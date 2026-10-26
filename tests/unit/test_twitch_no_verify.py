"""Confirm Twitch workflow has no real email verification step.

CLIENT REQUIREMENT: Twitch accounts must NOT be email-verified by this tool.
"""
from __future__ import annotations

import pytest

from backend.app.workflows.engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
)
from backend.app.workflows.twitch import TwitchNoVerificationStep, create_twitch_workflow


@pytest.mark.asyncio
async def test_twitch_workflow_has_no_email_verify_step():
    wf = create_twitch_workflow()
    step_names = [s.name for s in wf.steps]
    assert "email_verification" not in " ".join(step_names).replace("_skipped", "").replace("twitch_email_verification", "")
    for step in wf.steps:
        if "email" in step.name and "verification" in step.name:
            assert "skipped" in step.name, (
                f"Found email verification step '{step.name}' that is not marked as skipped"
            )


@pytest.mark.asyncio
async def test_twitch_no_verification_step_returns_skipped():
    step = TwitchNoVerificationStep()
    result = await step.execute({"account_id": 1})
    assert result.status == StepStatus.SKIPPED
    assert "intentionally" in result.message.lower()
    assert result.data.get("policy") == "no_twitch_email_verification"


@pytest.mark.asyncio
async def test_twitch_no_verification_step_is_not_required():
    step = TwitchNoVerificationStep()
    assert step.required is False


@pytest.mark.asyncio
async def test_twitch_workflow_completes_without_browser():
    wf = create_twitch_workflow(browser_service=None)
    execution = WorkflowExecution(wf, account_id=1)
    engine = WorkflowEngine()
    result = await engine.run(execution)

    assert result.status == WorkflowStatus.PAUSED_MANUAL
    assert result.step_results[0]["step"] == "twitch_registration"
    assert result.step_results[0]["status"] == "manual_required"


@pytest.mark.asyncio
async def test_twitch_workflow_only_two_steps():
    wf = create_twitch_workflow()
    assert len(wf.steps) == 2
    assert wf.steps[0].name == "twitch_registration"
    assert wf.steps[1].name == "twitch_email_verification_skipped"


@pytest.mark.asyncio
async def test_twitch_workflow_name():
    wf = create_twitch_workflow()
    assert wf.name == "twitch_creation_only"
    assert wf.platform == "twitch"
