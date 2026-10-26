from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def sync_client():
    return TestClient(app)


def test_websocket_connect_and_ping(sync_client: TestClient):
    with sync_client.websocket_connect("/ws") as ws:
        ws.send_text('{"type": "ping"}')
        data = ws.receive_json()
        assert data == {"type": "pong"}


def test_websocket_invalid_json(sync_client: TestClient):
    with sync_client.websocket_connect("/ws") as ws:
        ws.send_text("not json at all")
        data = ws.receive_json()
        assert data["type"] == "error"
        assert "Invalid JSON" in data["message"]


def test_websocket_non_ping_ignored(sync_client: TestClient):
    with sync_client.websocket_connect("/ws") as ws:
        ws.send_text('{"type": "unknown"}')
        ws.send_text('{"type": "ping"}')
        data = ws.receive_json()
        assert data == {"type": "pong"}
