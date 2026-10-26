from __future__ import annotations

from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_diagnostics_mailbox(client: AsyncClient):
    await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "diag@outlook.com",
    })
    listing = await client.get("/api/v1/mailboxes")
    items = listing.json()["items"]
    mailbox = [m for m in items if m["email"] == "diag@outlook.com"][0]

    resp = await client.get(f"/api/v1/mailboxes/{mailbox['id']}/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "diag@outlook.com"
    assert data["token_status"] == "missing"
    assert data["has_refresh_token"] is False
    assert data["is_mock"] is True
    assert data["provider_status"] == "unconfigured"


@pytest.mark.asyncio
async def test_diagnostics_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/mailboxes/99999/diagnostics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_refresh_no_token(client: AsyncClient):
    await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "norefresh@outlook.com",
    })
    listing = await client.get("/api/v1/mailboxes")
    items = listing.json()["items"]
    mailbox = [m for m in items if m["email"] == "norefresh@outlook.com"][0]

    resp = await client.post(f"/api/v1/mailboxes/{mailbox['id']}/refresh")
    assert resp.status_code == 400
    assert "refresh token" in resp.json()["detail"].lower() or "re-authorize" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_not_found(client: AsyncClient):
    resp = await client.post("/api/v1/mailboxes/99999/refresh")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_messages_mock(client: AsyncClient):
    await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "search@outlook.com:pass:client-id:auth-token",
        "format_hint": "email:password:clientId:authToken",
    })
    listing = await client.get("/api/v1/mailboxes")
    items = listing.json()["items"]
    mailbox = [m for m in items if m["email"] == "search@outlook.com"][0]

    resp = await client.post("/api/v1/mailboxes/search", json={
        "mailbox_id": mailbox["id"],
        "sender_filter": "noreply",
        "max_results": 10,
    })
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 1
    assert all(m["is_mock"] for m in messages)


@pytest.mark.asyncio
async def test_search_with_subject_filter(client: AsyncClient):
    await client.post("/api/v1/mailboxes/import/commit", json={
        "raw_text": "subjsearch@outlook.com:pass:client-id:auth-token",
        "format_hint": "email:password:clientId:authToken",
    })
    listing = await client.get("/api/v1/mailboxes")
    items = listing.json()["items"]
    mailbox = [m for m in items if m["email"] == "subjsearch@outlook.com"][0]

    resp = await client.post("/api/v1/mailboxes/search", json={
        "mailbox_id": mailbox["id"],
        "subject_filter": "verification",
    })
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 1
    assert "verification" in messages[0]["subject"].lower()
