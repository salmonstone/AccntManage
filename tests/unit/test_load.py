"""Load tests for synthetic job creation at 1k, 5k, and 10k scale.

These tests verify the job queue and account import can handle large batches
without errors or excessive memory/time. They use the in-memory SQLite test
database, so results approximate real performance.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_1k_jobs(client: AsyncClient):
    with patch("backend.app.services.job_service.settings") as mock_settings:
        mock_settings.MAX_QUEUE_SIZE = 15000
        mock_settings.MAX_RETRIES = 3
        start = time.monotonic()
        for i in range(1000):
            resp = await client.post("/api/v1/jobs", json={
                "job_type": "proxy_test",
                "params": {"batch_index": i},
            })
            assert resp.status_code == 201, f"Job {i} failed: {resp.text}"

        elapsed = time.monotonic() - start

        resp = await client.get("/api/v1/jobs?page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1000

        assert elapsed < 60, f"1k jobs took {elapsed:.1f}s (expected <60s)"


@pytest.mark.asyncio
async def test_create_5k_jobs(client: AsyncClient):
    with patch("backend.app.services.job_service.settings") as mock_settings:
        mock_settings.MAX_QUEUE_SIZE = 15000
        mock_settings.MAX_RETRIES = 3
        start = time.monotonic()
        for i in range(5000):
            resp = await client.post("/api/v1/jobs", json={
                "job_type": "proxy_test",
                "params": {"batch_index": i},
            })
            assert resp.status_code == 201, f"Job {i} failed: {resp.text}"

        elapsed = time.monotonic() - start

        resp = await client.get("/api/v1/jobs?page_size=1")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 5000

        assert elapsed < 300, f"5k jobs took {elapsed:.1f}s (expected <300s)"


@pytest.mark.asyncio
async def test_create_10k_jobs(client: AsyncClient):
    with patch("backend.app.services.job_service.settings") as mock_settings:
        mock_settings.MAX_QUEUE_SIZE = 15000
        mock_settings.MAX_RETRIES = 3
        start = time.monotonic()
        for i in range(10000):
            resp = await client.post("/api/v1/jobs", json={
                "job_type": "proxy_test",
                "params": {"batch_index": i},
            })
            assert resp.status_code == 201, f"Job {i} failed: {resp.text}"

        elapsed = time.monotonic() - start

        resp = await client.get("/api/v1/jobs?page_size=1")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 10000

        assert elapsed < 600, f"10k jobs took {elapsed:.1f}s (expected <600s)"


@pytest.mark.asyncio
async def test_bulk_account_import_1k(client: AsyncClient):
    emails = "\n".join(f"user{i}@loadtest.example.com" for i in range(1000))
    resp = await client.post("/api/v1/accounts/import/preview", json={
        "platform": "battlenet",
        "raw_text": emails,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_count"] == 1000
    assert data["duplicate_count"] == 0

    resp = await client.post("/api/v1/accounts/import/commit", json={
        "platform": "battlenet",
        "raw_text": emails,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pagination_large_dataset(client: AsyncClient):
    for i in range(100):
        await client.post("/api/v1/jobs", json={
            "job_type": "proxy_test",
            "params": {"page_test": i},
        })

    resp = await client.get("/api/v1/jobs?page=1&page_size=25")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 25
    assert data["total"] >= 100

    resp = await client.get("/api/v1/jobs?page=4&page_size=25")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 25
