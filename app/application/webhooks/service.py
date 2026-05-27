"""Webhook notification service.

Fires HTTP POST events to registered subscriber URLs when new plays are detected.

Subscriptions are persisted to the database (via WebhookSubscriptionDB) and loaded
into an in-memory store at startup so that ``fire_event`` is a zero-DB-query hot path.

Write-through pattern:
  - register / unregister write to DB first, then update the in-memory store.
  - fire_event reads from the in-memory store (fast).
  - On startup call ``load_from_db(session)`` to repopulate memory from DB.

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
    """In-memory subscription store backed by DB persistence.

    Use ``load_from_db`` at startup and ``persist_register`` / ``persist_unregister``
    in routes to keep DB and memory in sync.
    """

    def __init__(self) -> None:
        self._subs: dict[uuid.UUID, WebhookSubscription] = {}

    # ── Memory-only helpers (used internally and by fire_event) ───────────────

    def _add(self, sub: WebhookSubscription) -> None:
        self._subs[sub.id] = sub

    def _remove(self, sub_id: uuid.UUID) -> bool:
        return self._subs.pop(sub_id, None) is not None

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_active(self, event_type: str) -> list[WebhookSubscription]:
        return [
            s for s in self._subs.values()
            if s.is_active and event_type in s.event_types
        ]

    def get(self, sub_id: uuid.UUID) -> WebhookSubscription | None:
        return self._subs.get(sub_id)

    def __len__(self) -> int:
        return len(self._subs)

    # ── Write-through DB helpers (called from routes with a live session) ─────

    def register(
        self, url: str, event_types: list[str], secret: str | None = None
    ) -> WebhookSubscription:
        """Add to in-memory store only. Persist separately with ``persist_register``."""
        sub = WebhookSubscription(id=uuid.uuid4(), url=url, event_types=event_types, secret=secret)
        self._add(sub)
        return sub

    def unregister(self, sub_id: uuid.UUID) -> bool:
        """Remove from in-memory store only. Persist separately with ``persist_unregister``."""
        return self._remove(sub_id)

    # ── DB persistence helpers ────────────────────────────────────────────────

    async def load_from_db(self, session: object) -> None:
        """Load all active subscriptions from DB into memory (idempotent)."""
        from app.infrastructure.database.repositories.webhook_subscription_repo import (
            SQLWebhookSubscriptionRepository,
        )

        repo = SQLWebhookSubscriptionRepository(session)  # type: ignore[arg-type]
        rows = await repo.list_active()
        for row in rows:
            sub = WebhookSubscription(
                id=row.id,
                url=row.url,
                event_types=list(row.event_types or []),
                secret=row.secret,
                is_active=row.is_active,
                created_at=row.created_at,
            )
            self._add(sub)
        logger.info("webhook_store_loaded count=%d", len(rows))

    async def persist_register(self, sub: WebhookSubscription, session: object) -> None:
        """Persist a newly registered subscription to DB."""
        from app.infrastructure.database.models.operations import WebhookSubscriptionDB
        from app.infrastructure.database.repositories.webhook_subscription_repo import (
            SQLWebhookSubscriptionRepository,
        )

        row = WebhookSubscriptionDB(
            id=sub.id,
            url=sub.url,
            event_types=sub.event_types,
            secret=sub.secret,
            is_active=sub.is_active,
            created_at=sub.created_at,
        )
        repo = SQLWebhookSubscriptionRepository(session)  # type: ignore[arg-type]
        await repo.save(row)

    async def persist_unregister(self, sub_id: uuid.UUID, session: object) -> bool:
        """Hard-delete a subscription from DB. Returns True if found."""
        from app.infrastructure.database.repositories.webhook_subscription_repo import (
            SQLWebhookSubscriptionRepository,
        )

        repo = SQLWebhookSubscriptionRepository(session)  # type: ignore[arg-type]
        return await repo.hard_delete(sub_id)


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
) -> None:
    """Deliver a webhook payload with retry logic (bounded for-loop, single client)."""
    import hashlib
    import hmac
    import json

    from app.infrastructure.http.client import build_client

    body = json.dumps({"event": event_type, **payload})

    async with await build_client(timeout=5.0) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            headers = {"Content-Type": "application/json"}
            if sub.secret:
                sig = hmac.new(sub.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                headers["X-RMIAS-Signature"] = f"sha256={sig}"
            try:
                resp = await client.post(sub.url, content=body, headers=headers)
                if resp.status_code < 300:
                    logger.debug(
                        "webhook_delivered sub=%s event=%s status=%d",
                        sub.id, event_type, resp.status_code,
                    )
                    return
                logger.warning(
                    "webhook_non_2xx sub=%s event=%s status=%d attempt=%d",
                    sub.id, event_type, resp.status_code, attempt,
                )
            except Exception as exc:
                logger.warning(
                    "webhook_failed sub=%s event=%s error=%s attempt=%d",
                    sub.id, event_type, exc, attempt,
                )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
