"""Async job worker — pulls queued jobs and dispatches them to handlers.

Includes workflow execution for BATTLENET_WORKFLOW and TWITCH_WORKFLOW job types.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import async_session_factory
from backend.app.models.enums import JobStatus, JobType
from backend.app.models.job import Job
from backend.app.services.job_service import JobService

logger = logging.getLogger(__name__)


class WorkerService:
    def __init__(self, max_concurrency: int | None = None) -> None:
        self._max = max_concurrency or settings.MAX_WORKER_COUNT
        self._semaphore = asyncio.Semaphore(self._max)
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        self._running = True
        logger.info("Worker started (concurrency=%d)", self._max)
        while self._running:
            await self._poll()
            await asyncio.sleep(2)

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Worker stopped")

    async def _poll(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Job)
                .where(Job.status == JobStatus.QUEUED)
                .order_by(Job.created_at.asc())
                .limit(self._max)
            )
            jobs = result.scalars().all()

        for job in jobs:
            await self._semaphore.acquire()
            task = asyncio.create_task(self._execute_job(job.id))
            self._tasks.add(task)
            task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        self._semaphore.release()

    async def _execute_job(self, job_id: int) -> None:
        async with async_session_factory() as session:
            svc = JobService(session)
            job = await svc.get(job_id)
            if not job or job.status != JobStatus.QUEUED:
                return

            await svc.mark_running(job_id)
            params = json.loads(job.params_json) if job.params_json else {}

            try:
                if job.job_type in (JobType.BATTLENET_WORKFLOW, JobType.TWITCH_WORKFLOW):
                    result = await self._run_workflow(session, job.job_type, params)
                else:
                    result = await self._run_basic(job.job_type, params)

                await svc.mark_completed(job_id, result)
            except Exception as e:
                logger.exception("Job %d failed", job_id)
                await svc.mark_failed(job_id, str(e))

    async def _run_workflow(
        self, session: AsyncSession, job_type: JobType, params: dict
    ) -> dict:
        from backend.app.models.enums import AccountPlatform
        from backend.app.services.workflow_service import WorkflowService
        from backend.app.workflows.battlenet import create_battlenet_workflow
        from backend.app.workflows.engine import WorkflowEngine, WorkflowExecution
        from backend.app.workflows.twitch import create_twitch_workflow

        wf_id = params.get("workflow_execution_id")
        if not wf_id:
            raise ValueError("Missing workflow_execution_id in job params")

        wf_svc = WorkflowService(session)
        wf_resp = await wf_svc.get(wf_id)
        if not wf_resp:
            raise ValueError(f"Workflow execution {wf_id} not found")

        if job_type == JobType.BATTLENET_WORKFLOW:
            defn = create_battlenet_workflow()
        else:
            defn = create_twitch_workflow()

        from backend.app.models.workflow import WorkflowExecution as WFModel

        ctx_result = await session.execute(
            select(WFModel.context_json).where(WFModel.id == wf_id)
        )
        ctx_json = ctx_result.scalar() or "{}"

        execution = WorkflowExecution(defn, wf_resp.account_id)
        execution.context = json.loads(ctx_json)

        engine = WorkflowEngine()
        execution = await engine.run(execution)

        await wf_svc.update_from_execution(wf_id, execution)

        return execution.to_dict()

    async def _run_basic(self, job_type: JobType, params: dict) -> dict:
        if job_type == JobType.PROXY_TEST:
            return {"status": "completed", "message": "Proxy test placeholder"}
        elif job_type == JobType.MAILBOX_VALIDATE:
            return {"status": "completed", "message": "Mailbox validation placeholder"}
        elif job_type == JobType.BACKUP_CREATE:
            return {"status": "completed", "message": "Backup create placeholder"}
        return {"status": "completed", "job_type": job_type.value}
