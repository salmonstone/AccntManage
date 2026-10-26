from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_import_preview_mailboxes(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/import/preview", json={
        "raw_text": "user1@outlook.com\nuser2@outlook.com\nbadline\nuser1@outlook.com",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_parsed"] == 4
    assert data["valid_count"] == 2
    assert data["invalid_count"] == 1


@pytest.mark.asyncio
async def test_import_commit_mailboxes(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "mb1@outlook.com\nmb2@outlook.com",
    })
    assert resp.status_code == 200
    assert "Imported 2" in resp.json()["message"]


@pytest.mark.asyncio
async def test_list_mailboxes(client: AsyncClient):
    await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "listmb@outlook.com",
    })
    resp = await client.get("/api/v1/mailboxes")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_import_credential_format(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/import/preview", json={
        "raw_text": "user@outlook.com:pass123:abc-def-123:tokenvalue\nuser2@outlook.com:pw:cid:tok",
        "format_hint": "email:password:clientId:authToken",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_count"] == 2
    assert data["invalid_count"] == 0


@pytest.mark.asyncio
async def test_import_credential_commit_stores_encrypted(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "cred@outlook.com:mypass:client-id-123:auth-token-abc",
        "format_hint": "email:password:clientId:authToken",
    })
    assert resp.status_code == 200
    assert "Imported 1" in resp.json()["message"]

    listing = await client.get("/api/v1/mailboxes")
    items = listing.json()["items"]
    found = [m for m in items if m["email"] == "cred@outlook.com"]
    assert len(found) == 1


@pytest.mark.asyncio
async def test_import_refresh_token_format(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/import/preview", json={
        "raw_text": "rt@outlook.com:pass:refreshtokenval:client-id-456",
        "format_hint": "email:password:refreshToken:clientId",
    })
    assert resp.status_code == 200
    assert resp.json()["valid_count"] == 1
