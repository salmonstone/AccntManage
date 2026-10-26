from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_metrics(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_battlenet_accounts" in data
    assert "total_twitch_accounts" in data
    assert "active_jobs" in data


@pytest.mark.asyncio
async def test_recent_activity(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/activity")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
