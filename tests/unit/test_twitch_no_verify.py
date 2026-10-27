"""Confirm Twitch workflow pipeline structure and no email verification.

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
from backend.app.workflows.twitch import (
    UpdateStatusStep,
    create_twitch_workflow,
)


@pytest.mark.asyncio
async def test_twitch_workflow_has_no_email_verify_step():
    wf = create_twitch_workflow()
    step_names = [s.name for s in wf.steps]
    for name in step_names:
        assert "email_verification" not in name, (
            f"Found email verification step '{name}' — Twitch must not verify emails"
        )


@pytest.mark.asyncio
async def test_twitch_update_status_completes_without_db():
    step = UpdateStatusStep()
    context = {"account_id": 1, "registration_submitted": True}
    result = await step.execute(context)
    assert result.status == StepStatus.COMPLETED
    assert result.data.get("status_updated") is False


@pytest.mark.asyncio
async def test_twitch_workflow_has_eight_steps():
    wf = create_twitch_workflow()
    assert len(wf.steps) == 8
    expected_names = [
        "proxy_config", "browser_launch", "navigate_signup", "fill_form",
        "captcha_solve", "submit_form", "store_credentials", "update_status",
    ]
    actual_names = [s.name for s in wf.steps]
    assert actual_names == expected_names


@pytest.mark.asyncio
async def test_twitch_workflow_name():
    wf = create_twitch_workflow()
    assert wf.name == "twitch_account_creation"
    assert wf.platform == "twitch"


@pytest.mark.asyncio
async def test_twitch_proxy_step_no_db():
    from backend.app.workflows.twitch import ProxyConfigStep
    step = ProxyConfigStep()
    result = await step.execute({})
    assert result.status == StepStatus.COMPLETED
    assert result.data["proxy_configured"] is False


@pytest.mark.asyncio
async def test_twitch_browser_launch_fails_gracefully():
    from backend.app.workflows.twitch import BrowserLaunchStep
    step = BrowserLaunchStep()
    result = await step.execute({})
    assert result.status == StepStatus.FAILED
    assert "launch" in result.message.lower() or "browser" in result.message.lower()
