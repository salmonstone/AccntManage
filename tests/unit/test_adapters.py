from __future__ import annotations

import pytest

from backend.app.adapters.mock_captcha import MockCaptchaAdapter
from backend.app.adapters.mock_mailbox import MockMailboxAdapter
from backend.app.adapters.mock_sms import MockSMSAdapter


@pytest.mark.asyncio
async def test_mock_sms_flow():
    adapter = MockSMSAdapter()
    assert adapter.is_mock() is True

    rental = await adapter.rent_number()
    assert rental["is_mock"] is True
    assert rental["rental_id"]

    sms = await adapter.get_sms(rental["rental_id"])
    assert sms["is_mock"] is True
    assert sms["code"]

    await adapter.release_number(rental["rental_id"])

    balance = await adapter.check_balance()
    assert balance["is_mock"] is True


@pytest.mark.asyncio
async def test_mock_captcha_never_solves_live():
    adapter = MockCaptchaAdapter()
    assert adapter.is_mock() is True

    result = await adapter.solve("site-key", "https://example.com")
    assert result["is_mock"] is True
    assert "policy" in result

    balance = await adapter.check_balance()
    assert balance["is_mock"] is True


@pytest.mark.asyncio
async def test_mock_mailbox_search():
    adapter = MockMailboxAdapter()
    assert adapter.is_mock() is True

    messages = await adapter.search_messages("fake-token")
    assert len(messages) >= 1
    assert messages[0]["is_mock"] is True

    validation = await adapter.validate_token("fake-token")
    assert validation["is_mock"] is True
    assert validation["valid"] is True
