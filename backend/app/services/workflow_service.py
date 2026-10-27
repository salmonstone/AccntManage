"""Workflow service — creates, persists, and retrieves workflow executions."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import generate_correlation_id
from backend.app.models.account import Account
from backend.app.models.enums import AccountPlatform, JobType
from backend.app.models.workflow import WorkflowExecution as WorkflowExecutionModel
from backend.app.schemas.workflow import WorkflowResponse, WorkflowStepResultResponse
from backend.app.services.job_service import JobService
from backend.app.workflows.battlenet import create_battlenet_workflow
from backend.app.workflows.engine import (
    WorkflowExecution,
    WorkflowStatus,
)
from backend.app.workflows.twitch import create_twitch_workflow

logger = logging.getLogger(__name__)


def _model_to_response(m: WorkflowExecutionModel) -> WorkflowResponse:
    step_results = []
    if m.step_results_json:
        for sr in json.loads(m.step_results_json):
            step_results.append(WorkflowStepResultResponse(**sr))

    return WorkflowResponse(
        id=m.id,
        workflow_name=m.workflow_name,
        platform=m.platform,
        account_id=m.account_id,
        job_id=m.job_id,
        status=m.status.value if hasattr(m.status, "value") else m.status,
        current_step_index=m.current_step_index,
        total_steps=m.total_steps,
        step_results=step_results,
        error_message=m.error_message,
        correlation_id=m.correlation_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class WorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_and_enqueue(
        self,
        platform: AccountPlatform,
        account_id: int,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResponse:
        if platform == AccountPlatform.BATTLENET:
            defn = create_battlenet_workflow()
        elif platform == AccountPlatform.TWITCH:
            defn = create_twitch_workflow()
        else:
            raise ValueError(f"No workflow defined for platform {platform.value}")

        correlation_id = generate_correlation_id()

        ctx = dict(context or {})
        ctx.setdefault("account_id", account_id)
        ctx.setdefault("mock_mode", settings.MOCK_MODE)

        account_result = await self._session.execute(
            select(Account).where(Account.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if account:
            ctx.setdefault("email", account.email)
            if account.display_name:
                ctx.setdefault("display_name", account.display_name)

        model = WorkflowExecutionModel(
            workflow_name=defn.name,
            platform=defn.platform,
            account_id=account_id,
            status=WorkflowStatus.CREATED,
            current_step_index=0,
            total_steps=len(defn.steps),
            step_results_json="[]",
            context_json=json.dumps(ctx),
            correlation_id=correlation_id,
        )
        self._session.add(model)
        await self._session.flush()

        job_type = (
            JobType.BATTLENET_WORKFLOW
            if platform == AccountPlatform.BATTLENET
            else JobType.TWITCH_WORKFLOW
        )
        job_svc = JobService(self._session)
        job = await job_svc.create(job_type, {"workflow_execution_id": model.id})
        model.job_id = job.id
        await self._session.commit()

        return _model_to_response(model)

    async def get(self, workflow_id: int) -> WorkflowResponse | None:
        result = await self._session.execute(
            select(WorkflowExecutionModel).where(WorkflowExecutionModel.id == workflow_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            return None
        return _model_to_response(m)

    async def list_workflows(
        self,
        platform: str | None = None,
        status: str | None = None,
        account_id: int | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        query = select(WorkflowExecutionModel)
        count_q = select(func.count(WorkflowExecutionModel.id))

        if platform:
            query = query.where(WorkflowExecutionModel.platform == platform)
            count_q = count_q.where(WorkflowExecutionModel.platform == platform)
        if status:
            query = query.where(WorkflowExecutionModel.status == status)
            count_q = count_q.where(WorkflowExecutionModel.status == status)
        if account_id:
            query = query.where(WorkflowExecutionModel.account_id == account_id)
            count_q = count_q.where(WorkflowExecutionModel.account_id == account_id)

        total = (await self._session.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self._session.execute(
            query.order_by(WorkflowExecutionModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = [_model_to_response(m) for m in result.scalars().all()]

        return {
            "items": [i.model_dump() for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def cancel(self, workflow_id: int) -> WorkflowResponse:
        result = await self._session.execute(
            select(WorkflowExecutionModel).where(WorkflowExecutionModel.id == workflow_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            raise ValueError("Workflow not found")

        terminal = {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
        if m.status in terminal:
            raise ValueError(f"Cannot cancel workflow in {m.status.value} state")

        m.status = WorkflowStatus.CANCELLED
        if m.job_id:
            try:
                job_svc = JobService(self._session)
                await job_svc.cancel(m.job_id)
            except ValueError:
                pass
        await self._session.commit()
        return _model_to_response(m)

    async def run(self, workflow_id: int) -> WorkflowResponse:
        result = await self._session.execute(
            select(WorkflowExecutionModel).where(WorkflowExecutionModel.id == workflow_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            raise ValueError("Workflow not found")

        runnable = {WorkflowStatus.CREATED, WorkflowStatus.PAUSED_MANUAL, WorkflowStatus.FAILED}
        if m.status not in runnable:
            raise ValueError(f"Cannot run workflow in {m.status.value} state")

        m.status = WorkflowStatus.CREATED
        m.step_results_json = "[]"
        m.current_step_index = 0

        job_type = (
            JobType.BATTLENET_WORKFLOW
            if m.platform == "battlenet"
            else JobType.TWITCH_WORKFLOW
        )
        job_svc = JobService(self._session)
        job = await job_svc.create(job_type, {"workflow_execution_id": m.id})
        m.job_id = job.id
        await self._session.commit()

        return _model_to_response(m)

    async def update_from_execution(
        self, workflow_id: int, execution: WorkflowExecution
    ) -> None:
        result = await self._session.execute(
            select(WorkflowExecutionModel).where(WorkflowExecutionModel.id == workflow_id)
        )
        m = result.scalar_one_or_none()
        if not m:
            return

        m.status = execution.status
        m.current_step_index = execution.current_step_index
        m.step_results_json = json.dumps(execution.step_results)
        m.context_json = json.dumps(execution.serializable_context())
        await self._session.commit()
