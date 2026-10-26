from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_workflows_empty(client: AsyncClient):
    resp = await client.get("/api/v1/workflows?platform=battlenet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_workflow_requires_account(client: AsyncClient):
    resp = await client.post("/api/v1/workflows", json={
        "platform": "battlenet",
        "account_id": 1,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "battlenet"
    assert data["workflow_name"] == "battlenet_full_verification"
    assert data["status"] == "created"
    assert data["total_steps"] == 3
    assert data["job_id"] is not None


@pytest.mark.asyncio
async def test_create_twitch_workflow(client: AsyncClient):
    resp = await client.post("/api/v1/workflows", json={
        "platform": "twitch",
        "account_id": 2,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "twitch"
    assert data["workflow_name"] == "twitch_creation_only"
    assert data["total_steps"] == 2


@pytest.mark.asyncio
async def test_get_workflow(client: AsyncClient):
    create_resp = await client.post("/api/v1/workflows", json={
        "platform": "battlenet",
        "account_id": 3,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wf_id


@pytest.mark.asyncio
async def test_get_workflow_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/workflows/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_workflow(client: AsyncClient):
    create_resp = await client.post("/api/v1/workflows", json={
        "platform": "twitch",
        "account_id": 4,
    })
    wf_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/workflows/{wf_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_completed_fails(client: AsyncClient):
    create_resp = await client.post("/api/v1/workflows", json={
        "platform": "twitch",
        "account_id": 5,
    })
    wf_id = create_resp.json()["id"]
    await client.post(f"/api/v1/workflows/{wf_id}/cancel")

    resp = await client.post(f"/api/v1/workflows/{wf_id}/cancel")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_workflow_engine_step_execution():
    from backend.app.workflows.engine import (
        StepResult,
        StepStatus,
        WorkflowDefinition,
        WorkflowEngine,
        WorkflowExecution,
        WorkflowStatus,
        WorkflowStep,
    )

    class PassStep(WorkflowStep):
        name = "pass_step"
        description = "Always passes"
        async def execute(self, context):
            return StepResult(StepStatus.COMPLETED, "Done")

    class ManualStep(WorkflowStep):
        name = "manual_step"
        description = "Requires manual action"
        async def execute(self, context):
            return StepResult(StepStatus.MANUAL_REQUIRED, "Do it manually")

    defn = WorkflowDefinition("test_wf", "test", [PassStep(), ManualStep()])
    execution = WorkflowExecution(defn, account_id=1)
    engine = WorkflowEngine()
    result = await engine.run(execution)

    assert result.status == WorkflowStatus.PAUSED_MANUAL
    assert len(result.step_results) == 2
    assert result.step_results[0]["status"] == "completed"
    assert result.step_results[1]["status"] == "manual_required"


@pytest.mark.asyncio
async def test_workflow_engine_skip_optional():
    from backend.app.workflows.engine import (
        StepResult,
        StepStatus,
        WorkflowDefinition,
        WorkflowEngine,
        WorkflowExecution,
        WorkflowStatus,
        WorkflowStep,
    )

    class FailOptional(WorkflowStep):
        name = "optional_fail"
        description = "Optional step that fails"
        required = False
        async def execute(self, context):
            return StepResult(StepStatus.FAILED, "Failed but optional")

    class PassStep(WorkflowStep):
        name = "final"
        description = "Final step"
        async def execute(self, context):
            return StepResult(StepStatus.COMPLETED, "All done")

    defn = WorkflowDefinition("test_skip", "test", [FailOptional(), PassStep()])
    execution = WorkflowExecution(defn, account_id=1)
    engine = WorkflowEngine()
    result = await engine.run(execution)

    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.step_results) == 2
