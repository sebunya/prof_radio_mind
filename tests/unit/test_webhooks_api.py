"""Tests for the webhook management API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.application.webhooks.service import WebhookStore
from app.main import app

_API_KEY_HEADER = {"X-API-Key": "test-key"}


def _make_async_session(found_row=None, list_rows=None):
    """Build an AsyncMock session that satisfies the webhook repository calls."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=found_row)
    # execute().scalars().all() → list_rows
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = list_rows or []
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def fresh_store():
    """Provide an isolated in-memory WebhookStore, patched into the service module."""
    store = WebhookStore()
    with patch("app.application.webhooks.service.webhook_store", store):
        yield store


@pytest.fixture
def client():
    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield _make_async_session()

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
    """List endpoint reads from DB; empty mock → empty list."""
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.get("/webhooks", headers=_API_KEY_HEADER)
    assert r.status_code == 200
    assert r.json() == []


def test_list_webhooks_from_db(fresh_store: WebhookStore) -> None:
    """List reads from DB — verify rows are mapped correctly."""
    from datetime import datetime

    from app.infrastructure.database.models.operations import WebhookSubscriptionDB

    row = MagicMock(spec=WebhookSubscriptionDB)
    row.id = uuid.uuid4()
    row.url = "https://a.com"
    row.event_types = ["play.detected"]
    row.is_active = True
    row.created_at = datetime.now(UTC)

    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield _make_async_session(list_rows=[row])

    app.dependency_overrides[get_db] = fake_db
    try:
        c = TestClient(app)
        with patch("app.core.auth.require_api_key", return_value=None):
            r = c.get("/webhooks", headers=_API_KEY_HEADER)
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["url"] == "https://a.com"
    finally:
        app.dependency_overrides.clear()


def test_list_webhooks_multiple_event_types(fresh_store: WebhookStore) -> None:
    """Multi-event subscription appears exactly once in the list."""
    from datetime import datetime

    from app.infrastructure.database.models.operations import WebhookSubscriptionDB

    row = MagicMock(spec=WebhookSubscriptionDB)
    row.id = uuid.uuid4()
    row.url = "https://a.com"
    row.event_types = ["play.detected", "no_track.detected"]
    row.is_active = True
    row.created_at = datetime.now(UTC)

    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield _make_async_session(list_rows=[row])

    app.dependency_overrides[get_db] = fake_db
    try:
        c = TestClient(app)
        with patch("app.core.auth.require_api_key", return_value=None):
            r = c.get("/webhooks", headers=_API_KEY_HEADER)
        body = r.json()
        assert len(body) == 1
    finally:
        app.dependency_overrides.clear()


# --- DELETE /webhooks/{id} ---

def test_unregister_webhook_returns_204(fresh_store: WebhookStore) -> None:
    """Unregister hard-deletes from DB (mock returns found row)."""
    sub = fresh_store.register(url="https://a.com", event_types=["play.detected"])


    from app.infrastructure.database.models.operations import WebhookSubscriptionDB

    row = MagicMock(spec=WebhookSubscriptionDB)
    row.id = sub.id

    from app.infrastructure.database.session import get_db

    async def fake_db():
        yield _make_async_session(found_row=row)

    app.dependency_overrides[get_db] = fake_db
    try:
        c = TestClient(app)
        with patch("app.core.auth.require_api_key", return_value=None):
            r = c.delete(f"/webhooks/{sub.id}", headers=_API_KEY_HEADER)
        assert r.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_unregister_nonexistent_returns_404(
    client: TestClient, fresh_store: WebhookStore
) -> None:
    """When DB doesn't find the subscription, return 404."""
    with patch("app.core.auth.require_api_key", return_value=None):
        r = client.delete(f"/webhooks/{uuid.uuid4()}", headers=_API_KEY_HEADER)
    assert r.status_code == 404
