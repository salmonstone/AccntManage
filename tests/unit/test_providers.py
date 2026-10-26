from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sms_health_is_mock(client: AsyncClient):
    resp = await client.post("/api/v1/providers/sms/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_mock"] is True
    assert data["status"] == "mock_only"


@pytest.mark.asyncio
async def test_captcha_health_is_mock(client: AsyncClient):
    resp = await client.post("/api/v1/providers/captcha/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_mock"] is True
    assert "disabled by policy" in data["message"].lower()


@pytest.mark.asyncio
async def test_msgraph_health_unconfigured(client: AsyncClient):
    resp = await client.post("/api/v1/providers/msgraph/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unconfigured"
    assert data["is_mock"] is False
