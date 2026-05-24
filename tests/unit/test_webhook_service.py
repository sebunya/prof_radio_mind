"""Tests for webhook subscription store and delivery — no live network calls."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.webhooks.service import WebhookStore, fire_event, webhook_store


# --- WebhookStore ---

def test_register_returns_subscription() -> None:
    store = WebhookStore()
    sub = store.register(url="https://example.com/hook", event_types=["play.detected"])
    assert sub.url == "https://example.com/hook"
    assert "play.detected" in sub.event_types
    assert sub.is_active is True
    assert isinstance(sub.id, uuid.UUID)


def test_register_stores_subscription() -> None:
    store = WebhookStore()
    store.register(url="https://a.com", event_types=["play.detected"])
    assert len(store) == 1


def test_unregister_removes_subscription() -> None:
    store = WebhookStore()
    sub = store.register(url="https://a.com", event_types=["play.detected"])
    removed = store.unregister(sub.id)
    assert removed is True
    assert len(store) == 0


def test_unregister_nonexistent_returns_false() -> None:
    store = WebhookStore()
    assert store.unregister(uuid.uuid4()) is False


def test_list_active_filters_by_event_type() -> None:
    store = WebhookStore()
    store.register(url="https://a.com", event_types=["play.detected"])
    store.register(url="https://b.com", event_types=["no_track.detected"])
    active = store.list_active("play.detected")
    assert len(active) == 1
    assert active[0].url == "https://a.com"


def test_list_active_excludes_inactive() -> None:
    store = WebhookStore()
    sub = store.register(url="https://a.com", event_types=["play.detected"])
    sub.is_active = False
    active = store.list_active("play.detected")
    assert len(active) == 0


def test_get_returns_subscription() -> None:
    store = WebhookStore()
    sub = store.register(url="https://a.com", event_types=["play.detected"])
    fetched = store.get(sub.id)
    assert fetched is sub


def test_get_nonexistent_returns_none() -> None:
    store = WebhookStore()
    assert store.get(uuid.uuid4()) is None


def test_register_with_secret_stores_secret() -> None:
    store = WebhookStore()
    sub = store.register(url="https://a.com", event_types=["play.detected"], secret="s3cr3t")
    assert sub.secret == "s3cr3t"


# --- fire_event (with mocked HTTP) ---

def test_fire_event_no_subscribers_does_nothing() -> None:
    store = WebhookStore()
    with patch("app.application.webhooks.service.webhook_store", store):
        asyncio.run(fire_event("play.detected", {"station_id": "123"}))


def test_fire_event_delivers_to_subscribers() -> None:
    store = WebhookStore()
    store.register(url="https://hook.example.com/play", event_types=["play.detected"])

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.application.webhooks.service.webhook_store", store):
        with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
            asyncio.run(fire_event("play.detected", {"station_id": "abc"}))

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "https://hook.example.com/play" in str(call_kwargs)


def test_fire_event_with_hmac_signature() -> None:
    store = WebhookStore()
    store.register(
        url="https://hook.example.com/play",
        event_types=["play.detected"],
        secret="my_secret",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.application.webhooks.service.webhook_store", store):
        with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
            asyncio.run(fire_event("play.detected", {"station_id": "abc"}))

    _, call_kwargs = mock_client.post.call_args
    headers = call_kwargs.get("headers", {})
    assert "X-RMIAS-Signature" in headers
    assert headers["X-RMIAS-Signature"].startswith("sha256=")


def test_fire_event_retries_on_non_2xx() -> None:
    store = WebhookStore()
    store.register(url="https://hook.example.com/play", event_types=["play.detected"])

    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    async def _run() -> None:
        with patch("app.application.webhooks.service.webhook_store", store):
            with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
                with patch("app.application.webhooks.service.asyncio.sleep", new_callable=AsyncMock):
                    await fire_event("play.detected", {"station_id": "abc"})

    asyncio.run(_run())
    # Should retry up to _MAX_RETRIES (3) times
    assert mock_client.post.call_count == 3
