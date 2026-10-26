"""Tests for live adapter construction and configuration validation.

These tests verify adapter initialization and error handling without
making real API calls.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_capsolver_not_configured():
    from backend.app.adapters.capsolver import CapSolverAdapter

    adapter = CapSolverAdapter(api_key="")
    assert adapter.is_mock() is False
    result = await adapter.check_balance()
    assert result["balance"] == 0
    assert "Not configured" in result["error"]


@pytest.mark.asyncio
async def test_capsolver_solve_requires_key():
    from backend.app.adapters.capsolver import CapSolverAdapter

    adapter = CapSolverAdapter(api_key="")
    with pytest.raises(ValueError, match="not configured"):
        await adapter.solve("site-key", "https://example.com")


@pytest.mark.asyncio
async def test_live_sms_not_configured():
    from backend.app.adapters.live_sms import LiveSMSAdapter

    adapter = LiveSMSAdapter(api_key="", base_url="")
    assert adapter.is_mock() is False
    result = await adapter.check_balance()
    assert result["balance"] == 0
    assert "Not configured" in result["error"]


@pytest.mark.asyncio
async def test_live_sms_rent_requires_config():
    from backend.app.adapters.live_sms import LiveSMSAdapter

    adapter = LiveSMSAdapter(api_key="", base_url="", provider_name="test")
    with pytest.raises(ValueError, match="not configured"):
        await adapter.rent_number("US")


@pytest.mark.asyncio
async def test_browser_service_diagnostics():
    from backend.app.services.browser_service import BrowserConfig, BrowserService

    config = BrowserConfig(headless=True, timeout_ms=15000)
    svc = BrowserService(config)
    diag = svc.get_diagnostics()
    assert diag["running"] is False
    assert diag["headless"] is True
    assert diag["timeout_ms"] == 15000
    assert diag["has_proxy"] is False


def test_workflow_step_statuses():
    from backend.app.workflows.engine import StepStatus, WorkflowStatus

    assert StepStatus.MANUAL_REQUIRED.value == "manual_required"
    assert WorkflowStatus.PAUSED_MANUAL.value == "paused_manual"
    assert StepStatus.UNSUPPORTED.value == "unsupported"


def test_battlenet_workflow_factory():
    from backend.app.workflows.battlenet import create_battlenet_workflow

    wf = create_battlenet_workflow()
    assert wf.name == "battlenet_full_verification"
    assert wf.platform == "battlenet"
    assert len(wf.steps) == 3
    assert wf.steps[0].name == "battlenet_registration"
    assert wf.steps[1].name == "battlenet_email_verification"
    assert wf.steps[2].name == "battlenet_phone_verification"


def test_twitch_workflow_factory():
    from backend.app.workflows.twitch import create_twitch_workflow

    wf = create_twitch_workflow()
    assert wf.name == "twitch_creation_only"
    assert wf.platform == "twitch"
    assert len(wf.steps) == 2
    assert wf.steps[1].required is False


@pytest.mark.asyncio
async def test_twitch_no_verification_step():
    from backend.app.workflows.twitch import TwitchNoVerificationStep
    from backend.app.workflows.engine import StepStatus

    step = TwitchNoVerificationStep()
    result = await step.execute({})
    assert result.status == StepStatus.SKIPPED
    assert "intentionally" in result.message.lower()


@pytest.mark.asyncio
async def test_battlenet_registration_no_browser():
    from backend.app.workflows.battlenet import BattlenetRegistrationStep
    from backend.app.workflows.engine import StepStatus

    step = BattlenetRegistrationStep(browser_service=None)
    result = await step.execute({})
    assert result.status == StepStatus.MANUAL_REQUIRED
    assert "manually" in result.message.lower()


@pytest.mark.asyncio
async def test_battlenet_email_no_token():
    from backend.app.workflows.battlenet import BattlenetEmailVerificationStep
    from backend.app.workflows.engine import StepStatus

    step = BattlenetEmailVerificationStep(mailbox_adapter=None)
    result = await step.execute({})
    assert result.status == StepStatus.MANUAL_REQUIRED


@pytest.mark.asyncio
async def test_battlenet_phone_no_sms():
    from backend.app.workflows.battlenet import BattlenetPhoneVerificationStep
    from backend.app.workflows.engine import StepStatus

    step = BattlenetPhoneVerificationStep(sms_adapter=None)
    result = await step.execute({})
    assert result.status == StepStatus.UNSUPPORTED
