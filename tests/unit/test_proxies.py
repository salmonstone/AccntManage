from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_proxy(client: AsyncClient):
    resp = await client.post("/api/v1/proxies", json={
        "protocol": "http",
        "host": "proxy.example.com",
        "port": 8080,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["host"] == "proxy.example.com"
    assert data["port"] == 8080
    assert data["test_status"] == "untested"


@pytest.mark.asyncio
async def test_create_duplicate_proxy(client: AsyncClient):
    await client.post("/api/v1/proxies", json={
        "protocol": "http",
        "host": "dup.example.com",
        "port": 8080,
    })
    resp = await client.post("/api/v1/proxies", json={
        "protocol": "http",
        "host": "dup.example.com",
        "port": 8080,
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_proxies(client: AsyncClient):
    await client.post("/api/v1/proxies", json={
        "protocol": "socks5",
        "host": "list.example.com",
        "port": 1080,
    })
    resp = await client.get("/api/v1/proxies")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_import_proxies(client: AsyncClient):
    resp = await client.post("/api/v1/proxies/import", json={
        "raw_text": "1.2.3.4:8080\n5.6.7.8:3128\nbadline",
        "default_protocol": "http",
    })
    assert resp.status_code == 200
    assert "Imported" in resp.json()["message"]


@pytest.mark.asyncio
async def test_delete_proxy_requires_confirm(client: AsyncClient):
    create_resp = await client.post("/api/v1/proxies", json={
        "protocol": "http",
        "host": "delme.example.com",
        "port": 9090,
    })
    proxy_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/proxies/{proxy_id}")
    assert resp.status_code == 400
    resp = await client.delete(f"/api/v1/proxies/{proxy_id}?confirm=true")
    assert resp.status_code == 200
