from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient):
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "max_worker_count" in data
    assert "theme" in data


@pytest.mark.asyncio
async def test_update_settings(client: AsyncClient):
    resp = await client.patch("/api/v1/settings", json={
        "theme": "dark",
        "max_retries": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "dark"
    assert data["max_retries"] == 5
