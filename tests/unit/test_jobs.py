from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient):
    resp = await client.post("/api/v1/jobs", json={
        "job_type": "proxy_test",
        "params": {"proxy_ids": [1, 2]},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["job_type"] == "proxy_test"
    assert data["status"] == "queued"
    assert data["correlation_id"]


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    await client.post("/api/v1/jobs", json={"job_type": "proxy_test"})
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_cancel_job(client: AsyncClient):
    create_resp = await client.post("/api/v1/jobs", json={"job_type": "proxy_test"})
    job_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_completed_job_fails(client: AsyncClient):
    create_resp = await client.post("/api/v1/jobs", json={"job_type": "proxy_test"})
    job_id = create_resp.json()["id"]
    await client.post(f"/api/v1/jobs/{job_id}/cancel")
    resp = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_idempotency_key_dedup(client: AsyncClient):
    payload = {
        "job_type": "proxy_test",
        "params": {"proxy_ids": [1]},
        "idempotency_key": "test-idem-key-001",
    }
    resp1 = await client.post("/api/v1/jobs", json=payload)
    assert resp1.status_code == 201
    job1 = resp1.json()

    resp2 = await client.post("/api/v1/jobs", json=payload)
    assert resp2.status_code == 201
    job2 = resp2.json()

    assert job1["id"] == job2["id"]
    assert job1["idempotency_key"] == "test-idem-key-001"
