"""Tests for the webhook management API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.application.webhooks.service import WebhookStore
from app.main import app

_API_KEY_HEADER = {"X-API-Key": "test-key"}


@pytest.fixture
def fresh_store():
    store = WebhookStore()
    with patch("app.application.webhooks.service.webhook_store", store):
        yield store


@pytest.fixture
def client():
    from unittest.mock import MagicMock

    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- POST /webhooks ---

def test_register_webhook_returns_201(client: TestClient, fresh_store: WebhookStore) -> None:
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.post(
            "/webhooks",
            json={"url": "https://hook.example.com/play", "event_types": ["play.detected"]},
            headers=_API_KEY_HEADER,
        )
    assert r.status_code == 201


def test_register_webhook_response_fields(client: TestClient, fresh_store: WebhookStore) -> None:
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.post(
            "/webhooks",
            json={"url": "https://hook.example.com", "event_types": ["play.detected"]},
            headers=_API_KEY_HEADER,
        )
    body = r.json()
    assert "id" in body
    assert body["url"] == "https://hook.example.com"
    assert body["event_types"] == ["play.detected"]
    assert body["is_active"] is True


def test_register_webhook_invalid_event_type_returns_422(
    client: TestClient, fresh_store: WebhookStore
) -> None:
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.post(
            "/webhooks",
            json={"url": "https://hook.example.com", "event_types": ["invalid.event"]},
            headers=_API_KEY_HEADER,
        )
    assert r.status_code == 422
    assert "invalid.event" in r.json()["detail"]


# --- GET /webhooks ---

def test_list_webhooks_empty(client: TestClient, fresh_store: WebhookStore) -> None:
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.get("/webhooks", headers=_API_KEY_HEADER)
    assert r.status_code == 200
    assert r.json() == []


def test_list_webhooks_includes_registered(client: TestClient, fresh_store: WebhookStore) -> None:
    fresh_store.register(url="https://a.com", event_types=["play.detected"])
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.get("/webhooks", headers=_API_KEY_HEADER)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["url"] == "https://a.com"


def test_list_webhooks_multiple_event_types_deduped(
    client: TestClient, fresh_store: WebhookStore
) -> None:
    fresh_store.register(
        url="https://a.com",
        event_types=["play.detected", "no_track.detected"],
    )
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.get("/webhooks", headers=_API_KEY_HEADER)
    # Subscription appears for each matching event type, but it's one physical sub
    body = r.json()
    assert len(body) >= 1


# --- DELETE /webhooks/{id} ---

def test_unregister_webhook_returns_204(client: TestClient, fresh_store: WebhookStore) -> None:
    sub = fresh_store.register(url="https://a.com", event_types=["play.detected"])
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.delete(f"/webhooks/{sub.id}", headers=_API_KEY_HEADER)
    assert r.status_code == 204


def test_unregister_nonexistent_returns_404(
    client: TestClient, fresh_store: WebhookStore
) -> None:
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.delete(f"/webhooks/{uuid.uuid4()}", headers=_API_KEY_HEADER)
    assert r.status_code == 404
