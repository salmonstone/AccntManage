"""Account workflow engine — orchestrates multi-step account workflows with
state persistence, manual handoff, and per-step error handling."""
from __future__ import annotations

import enum
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    MANUAL_REQUIRED = "manual_required"
    UNSUPPORTED = "unsupported"
    TIMED_OUT = "timed_out"


class WorkflowStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED_MANUAL = "paused_manual"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class StepResult:
    def __init__(
        self,
        status: StepStatus,
        message: str = "",
        data: dict[str, Any] | None = None,
        screenshot_path: str | None = None,
    ) -> None:
        self.status = status
        self.message = message
        self.data = data or {}
        self.screenshot_path = screenshot_path
        self.timestamp = datetime.now(UTC).isoformat()


class WorkflowStep:
    """Base class for a single step in an account workflow."""

    name: str = "unnamed_step"
    description: str = ""
    required: bool = True

    async def execute(self, context: dict[str, Any]) -> StepResult:
        raise NotImplementedError

    async def rollback(self, context: dict[str, Any]) -> None:
        pass


class WorkflowDefinition:
    """Defines an ordered sequence of steps for an account workflow."""

    def __init__(self, name: str, platform: str, steps: list[WorkflowStep]) -> None:
        self.name = name
        self.platform = platform
        self.steps = steps


class WorkflowExecution:
    """Tracks the state of one workflow execution."""

    def __init__(self, definition: WorkflowDefinition, account_id: int) -> None:
        self.definition = definition
        self.account_id = account_id
        self.status = WorkflowStatus.CREATED
        self.current_step_index = 0
        self.step_results: list[dict[str, Any]] = []
        self.context: dict[str, Any] = {"account_id": account_id}
        self.created_at = datetime.now(UTC).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.definition.name,
            "platform": self.definition.platform,
            "account_id": self.account_id,
            "status": self.status.value,
            "current_step": self.current_step_index,
            "total_steps": len(self.definition.steps),
            "step_results": self.step_results,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkflowEngine:
    """Executes workflow definitions step by step with error isolation."""

    async def run(self, execution: WorkflowExecution) -> WorkflowExecution:
        execution.status = WorkflowStatus.RUNNING
        execution.updated_at = datetime.now(UTC).isoformat()

        for i in range(execution.current_step_index, len(execution.definition.steps)):
            step = execution.definition.steps[i]
            execution.current_step_index = i

            logger.info(
                "Workflow %s account=%d: running step %d/%d (%s)",
                execution.definition.name,
                execution.account_id,
                i + 1,
                len(execution.definition.steps),
                step.name,
            )

            try:
                result = await step.execute(execution.context)
            except Exception as e:
                result = StepResult(StepStatus.FAILED, f"Unexpected error: {e}")
                logger.exception("Step %s failed", step.name)

            execution.step_results.append({
                "step": step.name,
                "description": step.description,
                "status": result.status.value,
                "message": result.message,
                "data": result.data,
                "screenshot": result.screenshot_path,
                "timestamp": result.timestamp,
            })
            execution.updated_at = datetime.now(UTC).isoformat()

            if result.status == StepStatus.MANUAL_REQUIRED:
                execution.status = WorkflowStatus.PAUSED_MANUAL
                logger.info("Workflow paused — manual action required at step %s", step.name)
                return execution

            if result.status == StepStatus.UNSUPPORTED:
                if step.required:
                    execution.status = WorkflowStatus.FAILED
                    logger.warning("Required step %s is unsupported", step.name)
                    return execution
                continue

            if result.status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                if step.required:
                    execution.status = WorkflowStatus.FAILED
                    return execution
                continue

        execution.status = WorkflowStatus.COMPLETED
        execution.updated_at = datetime.now(UTC).isoformat()
        return execution
