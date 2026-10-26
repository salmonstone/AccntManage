"""End-to-end Battle.net workflow pipeline test using mocked adapters.

Verifies the three-step pipeline (registration → email verify → phone verify)
chains correctly, and that failure in a required step stops the pipeline.
"""
from __future__ import annotations

import pytest

from backend.app.workflows.battlenet import (
    BattlenetEmailVerificationStep,
    BattlenetPhoneVerificationStep,
    BattlenetRegistrationStep,
    create_battlenet_workflow,
)
from backend.app.workflows.engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
)


@pytest.mark.asyncio
async def test_full_pipeline_no_browser_pauses_at_registration():
    wf = create_battlenet_workflow(browser_service=None, mailbox_adapter=None, sms_adapter=None)
    execution = WorkflowExecution(wf, account_id=1)
    engine = WorkflowEngine()
    result = await engine.run(execution)

    assert result.status == WorkflowStatus.PAUSED_MANUAL
    assert len(result.step_results) == 1
    assert result.step_results[0]["step"] == "battlenet_registration"
    assert result.step_results[0]["status"] == "manual_required"


@pytest.mark.asyncio
async def test_email_step_no_token_returns_manual():
    step = BattlenetEmailVerificationStep(mailbox_adapter=None)
    result = await step.execute({"account_id": 1})
    assert result.status == StepStatus.MANUAL_REQUIRED
    assert "mailbox access token" in result.message.lower()


@pytest.mark.asyncio
async def test_email_step_no_adapter_returns_unsupported():
    step = BattlenetEmailVerificationStep(mailbox_adapter=None)
    result = await step.execute({"account_id": 1, "mailbox_access_token": "fake-token"})
    assert result.status == StepStatus.UNSUPPORTED


class FakeMailboxAdapter:
    async def search_messages(self, token, sender_filter=None, subject_filter=None, max_results=5):
        return [
            {
                "subject": "Verify your Battle.net email",
                "sender": "noreply@blizzard.com",
                "body_preview": "Click here to verify: https://battle.net/verify?code=abc123",
                "is_mock": True,
            }
        ]


@pytest.mark.asyncio
async def test_email_step_finds_verification_link():
    adapter = FakeMailboxAdapter()
    step = BattlenetEmailVerificationStep(mailbox_adapter=adapter)
    ctx = {"account_id": 1, "mailbox_access_token": "test-token"}
    result = await step.execute(ctx)

    assert result.status == StepStatus.MANUAL_REQUIRED
    assert "verification_link" in result.data
    assert "battle.net/verify" in result.data["verification_link"]


class FakeMailboxAdapterWithCode:
    async def search_messages(self, token, sender_filter=None, subject_filter=None, max_results=5):
        return [
            {
                "subject": "Your Battle.net code",
                "sender": "noreply@blizzard.com",
                "body_preview": "Your verification code is 482917",
                "is_mock": True,
            }
        ]


@pytest.mark.asyncio
async def test_email_step_extracts_code():
    adapter = FakeMailboxAdapterWithCode()
    step = BattlenetEmailVerificationStep(mailbox_adapter=adapter)
    ctx = {"account_id": 1, "mailbox_access_token": "test-token"}
    result = await step.execute(ctx)

    assert result.status == StepStatus.MANUAL_REQUIRED
    assert result.data.get("verification_code") == "482917"


@pytest.mark.asyncio
async def test_phone_step_no_adapter_returns_unsupported():
    step = BattlenetPhoneVerificationStep(sms_adapter=None)
    result = await step.execute({"account_id": 1})
    assert result.status == StepStatus.UNSUPPORTED


class FakeSMSAdapter:
    def is_mock(self):
        return True

    async def rent_number(self, country="US"):
        return {"rental_id": "rental-001", "phone_number": "+15551234567"}

    async def get_sms(self, rental_id):
        return {"code": "123456", "message": "Your code is 123456"}

    async def release_number(self, rental_id):
        pass


@pytest.mark.asyncio
async def test_phone_step_mock_adapter_completes():
    adapter = FakeSMSAdapter()
    step = BattlenetPhoneVerificationStep(sms_adapter=adapter)
    result = await step.execute({"account_id": 1})

    assert result.status == StepStatus.COMPLETED
    assert result.data["is_mock"] is True
    assert result.data["code"] == "123456"


@pytest.mark.asyncio
async def test_registration_step_no_browser():
    step = BattlenetRegistrationStep(browser_service=None)
    result = await step.execute({"account_id": 1})
    assert result.status == StepStatus.MANUAL_REQUIRED
    assert "battle.net" in result.message.lower()


@pytest.mark.asyncio
async def test_all_three_steps_defined():
    wf = create_battlenet_workflow()
    assert len(wf.steps) == 3
    names = [s.name for s in wf.steps]
    assert names == [
        "battlenet_registration",
        "battlenet_email_verification",
        "battlenet_phone_verification",
    ]
