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
async def test_captcha_health(client: AsyncClient):
    resp = await client.post("/api/v1/providers/captcha/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_mock" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_msgraph_health_unconfigured(client: AsyncClient):
    resp = await client.post("/api/v1/providers/msgraph/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unconfigured"
    assert data["is_mock"] is False


@pytest.mark.asyncio
async def test_provider_status_all(client: AsyncClient):
    resp = await client.get("/api/v1/providers/status/all")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    names = {p["provider"] for p in data}
    assert names == {"sms", "captcha", "msgraph", "browser"}
    for p in data:
        assert "status" in p
        assert "is_mock" in p
        assert "capabilities" in p
        assert isinstance(p["capabilities"], list)


@pytest.mark.asyncio
async def test_provider_status_all_values(client: AsyncClient):
    resp = await client.get("/api/v1/providers/status/all")
    data = {p["provider"]: p for p in resp.json()}
    valid_statuses = {"unconfigured", "configured", "configured_not_tested", "live_tested", "mock_only", "connected", "unavailable", "disabled", "unsupported", "error"}
    for provider in ("captcha", "msgraph", "browser"):
        assert data[provider]["status"] in valid_statuses
    assert data["browser"]["is_mock"] is False


@pytest.mark.asyncio
async def test_captcha_profiles(client: AsyncClient):
    resp = await client.get("/api/v1/providers/captcha/profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    names = {p["provider"] for p in data}
    assert names == {"capsolver", "anticaptcha", "twocaptcha", "ezcaptcha"}
    for p in data:
        assert "status" in p
        assert "is_active" in p
        assert "has_key" in p
        assert "is_mock" in p
        assert isinstance(p["status"], str)
        assert isinstance(p["is_mock"], bool)


@pytest.mark.asyncio
async def test_health_includes_provider_statuses(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider_statuses" in data
    assert "providers_mock" in data
    statuses = data["provider_statuses"]
    assert "sms" in statuses
    assert "captcha" in statuses
    assert "msgraph" in statuses
    assert "browser" in statuses
    valid_values = {
        "unconfigured", "configured", "configured_not_tested", "live_tested",
        "mock_only", "connected", "unavailable", "disabled", "unsupported", "error",
    }
    for val in statuses.values():
        assert val in valid_values
