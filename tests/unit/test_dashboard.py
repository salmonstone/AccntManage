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
async def test_dashboard_mock_live_counts(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "live_accounts" in data
    assert "mock_accounts" in data
    assert isinstance(data["live_accounts"], int)
    assert isinstance(data["mock_accounts"], int)


@pytest.mark.asyncio
async def test_dashboard_chart_data(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_status_breakdown" in data
    assert isinstance(data["job_status_breakdown"], dict)
    assert "activity_timeline" in data
    assert isinstance(data["activity_timeline"], list)
    assert len(data["activity_timeline"]) == 7
    for day in data["activity_timeline"]:
        assert "date" in day
        assert "count" in day


@pytest.mark.asyncio
async def test_recent_activity(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/activity")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
