"""Webhook notification service.

Fires HTTP POST events to registered subscriber URLs when new plays are detected.
Subscriptions are stored in memory in MVP — replace with DB-backed store for production.

Payload format:
  {
    "event": "play.detected",
    "station_id": "...",
    "artist": "...",
    "title": "...",
    "played_at": "2026-05-24T16:00:00Z"
  }
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2.0


@dataclass
class WebhookSubscription:
    id: uuid.UUID
    url: str
    event_types: list[str]
    secret: str | None = None
    is_active: bool = True
    created_at: datetime = field(
        default_factory=lambda: __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
    )


class WebhookStore:
    """In-memory subscription store — replace with SQLAlchemy repo for production."""

    def __init__(self) -> None:
        self._subs: dict[uuid.UUID, WebhookSubscription] = {}

    def register(
        self, url: str, event_types: list[str], secret: str | None = None
    ) -> WebhookSubscription:
        sub = WebhookSubscription(id=uuid.uuid4(), url=url, event_types=event_types, secret=secret)
        self._subs[sub.id] = sub
        return sub

    def unregister(self, sub_id: uuid.UUID) -> bool:
        return self._subs.pop(sub_id, None) is not None

    def list_active(self, event_type: str) -> list[WebhookSubscription]:
        return [
            s for s in self._subs.values()
            if s.is_active and event_type in s.event_types
        ]

    def get(self, sub_id: uuid.UUID) -> WebhookSubscription | None:
        return self._subs.get(sub_id)

    def __len__(self) -> int:
        return len(self._subs)


webhook_store = WebhookStore()


async def fire_event(event_type: str, payload: dict) -> None:
    """Fire an event to all subscribers registered for that event type."""
    subscribers = webhook_store.list_active(event_type)
    if not subscribers:
        return

    tasks = [_deliver(sub, event_type, payload) for sub in subscribers]
    await asyncio.gather(*tasks, return_exceptions=True)


async def _deliver(
    sub: WebhookSubscription,
    event_type: str,
    payload: dict,
    *,
    attempt: int = 1,
) -> None:
    """Deliver a webhook payload with retry logic."""
    import json

    from app.infrastructure.http.client import build_client

    body = json.dumps({"event": event_type, **payload})
    headers = {"Content-Type": "application/json"}
    if sub.secret:
        import hashlib
        import hmac

        sig = hmac.new(sub.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-RMIAS-Signature"] = f"sha256={sig}"

    try:
        async with await build_client(timeout=5.0) as client:
            resp = await client.post(sub.url, content=body, headers=headers)
        if resp.status_code < 300:
            logger.debug("webhook_delivered sub=%s event=%s", sub.id, event_type)
        else:
            logger.warning(
                "webhook_non_2xx sub=%s event=%s status=%d attempt=%d",
                sub.id, event_type, resp.status_code, attempt,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
                await _deliver(sub, event_type, payload, attempt=attempt + 1)
    except Exception as exc:
        logger.warning(
            "webhook_failed sub=%s event=%s error=%s attempt=%d",
            sub.id, event_type, exc, attempt,
        )
        if attempt < _MAX_RETRIES:
            await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
            await _deliver(sub, event_type, payload, attempt=attempt + 1)
