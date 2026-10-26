from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_account(client: AsyncClient):
    resp = await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "test@example.com",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["platform"] == "battlenet"
    assert data["status"] == "draft"
    assert data["is_simulated"] is False


@pytest.mark.asyncio
async def test_create_duplicate_account(client: AsyncClient):
    await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "dup@example.com",
    })
    resp = await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "dup@example.com",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient):
    await client.post("/api/v1/accounts", json={
        "platform": "twitch",
        "email": "list1@example.com",
    })
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_account(client: AsyncClient):
    create_resp = await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "get@example.com",
    })
    account_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/accounts/{account_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "get@example.com"


@pytest.mark.asyncio
async def test_get_nonexistent_account(client: AsyncClient):
    resp = await client.get("/api/v1/accounts/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_account(client: AsyncClient):
    create_resp = await client.post("/api/v1/accounts", json={
        "platform": "twitch",
        "email": "update@example.com",
    })
    account_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/v1/accounts/{account_id}", json={
        "display_name": "Updated Name",
        "status": "unverified",
    })
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"
    assert resp.json()["status"] == "unverified"


@pytest.mark.asyncio
async def test_delete_requires_confirm(client: AsyncClient):
    create_resp = await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "del@example.com",
    })
    account_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/accounts/{account_id}")
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/accounts/{account_id}?confirm=true")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_import_preview(client: AsyncClient):
    resp = await client.post("/api/v1/accounts/import/preview", json={
        "platform": "battlenet",
        "raw_text": "user1@test.com\nuser2@test.com\ninvalid-line\nuser1@test.com",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_parsed"] == 4
    assert data["valid_count"] == 2
    assert data["invalid_count"] == 1


@pytest.mark.asyncio
async def test_account_status_history(client: AsyncClient):
    create_resp = await client.post("/api/v1/accounts", json={
        "platform": "battlenet",
        "email": "history@example.com",
    })
    account_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/accounts/{account_id}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["new_status"] == "draft"
