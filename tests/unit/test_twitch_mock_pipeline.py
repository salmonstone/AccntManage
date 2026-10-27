"""Tests for the Twitch 8-step pipeline running in mock mode.

Verifies that every step completes when mock_mode=True, credentials
are generated, and DB persistence works through StoreCredentials
and UpdateStatus steps.
"""
from __future__ import annotations

import pytest

from backend.app.workflows.engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
)
from backend.app.workflows.twitch import create_twitch_workflow


def _mock_context(email: str = "test@example.com", account_id: int = 1) -> dict:
    return {
        "mock_mode": True,
        "email": email,
        "account_id": account_id,
    }


@pytest.mark.asyncio
async def test_all_eight_steps_complete_in_mock_mode():
    wf = create_twitch_workflow()
    execution = WorkflowExecution(wf, account_id=1)
    execution.context.update(_mock_context())

    engine = WorkflowEngine()
    execution = await engine.run(execution)

    assert execution.status == WorkflowStatus.COMPLETED
    assert len(execution.step_results) == 8
    for entry in execution.step_results:
        assert entry["status"] == StepStatus.COMPLETED.value, (
            f"Step '{entry['step']}' did not complete: {entry.get('message')}"
        )


@pytest.mark.asyncio
async def test_mock_generates_credentials():
    wf = create_twitch_workflow()
    execution = WorkflowExecution(wf, account_id=1)
    execution.context.update(_mock_context())

    engine = WorkflowEngine()
    execution = await engine.run(execution)

    assert execution.context.get("generated_username") is not None
    assert execution.context.get("generated_password") is not None
    assert len(execution.context["generated_password"]) == 16


@pytest.mark.asyncio
async def test_mock_sets_registration_submitted():
    wf = create_twitch_workflow()
    execution = WorkflowExecution(wf, account_id=1)
    execution.context.update(_mock_context())

    engine = WorkflowEngine()
    execution = await engine.run(execution)

    assert execution.context.get("registration_submitted") is True


@pytest.mark.asyncio
async def test_mock_uses_display_name_when_provided():
    wf = create_twitch_workflow()
    execution = WorkflowExecution(wf, account_id=1)
    execution.context.update(_mock_context())
    execution.context["display_name"] = "CustomUser99"

    engine = WorkflowEngine()
    execution = await engine.run(execution)

    assert execution.context["generated_username"] == "CustomUser99"


@pytest.mark.asyncio
async def test_mock_step_results_have_mock_flag():
    wf = create_twitch_workflow()
    execution = WorkflowExecution(wf, account_id=1)
    execution.context.update(_mock_context())

    engine = WorkflowEngine()
    execution = await engine.run(execution)

    mock_steps = {"proxy_config", "browser_launch", "navigate_signup",
                  "fill_form", "captcha_solve", "submit_form"}
    for entry in execution.step_results:
        if entry["step"] in mock_steps:
            assert entry["data"].get("mock") is True, (
                f"Step '{entry['step']}' missing mock flag"
            )


@pytest.mark.asyncio
async def test_store_credentials_without_db_still_completes():
    from backend.app.workflows.twitch import StoreCredentialsStep
    step = StoreCredentialsStep()
    ctx = {
        "mock_mode": True,
        "account_id": 1,
        "generated_username": "testuser1234",
        "generated_password": "AbCd1234!@#$efgh",
    }
    result = await step.execute(ctx)
    assert result.status == StepStatus.COMPLETED
    assert result.data["stored_to_db"] is False


@pytest.mark.asyncio
async def test_update_status_without_db_still_completes():
    from backend.app.workflows.twitch import UpdateStatusStep
    step = UpdateStatusStep()
    ctx = {"mock_mode": True, "registration_submitted": True}
    result = await step.execute(ctx)
    assert result.status == StepStatus.COMPLETED
    assert result.data["status_updated"] is False


@pytest.mark.asyncio
async def test_fill_form_fails_without_email():
    from backend.app.workflows.twitch import FillFormStep
    step = FillFormStep()
    result = await step.execute({"mock_mode": True})
    assert result.status == StepStatus.FAILED
    assert "email" in result.message.lower()
