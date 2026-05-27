"""Webhook subscription management API."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_api_key

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_VALID_EVENTS = {"play.detected", "no_track.detected", "reconciliation.completed"}


class SubscriptionRequest(BaseModel):
    url: str
    event_types: list[str]
    secret: str | None = None


class SubscriptionResponse(BaseModel):
    id: str
    url: str
    event_types: list[str]
    is_active: bool
    created_at: datetime


def _to_response(sub: object) -> SubscriptionResponse:
    from app.application.webhooks.service import WebhookSubscription

    assert isinstance(sub, WebhookSubscription)
    return SubscriptionResponse(
        id=str(sub.id),
        url=sub.url,
        event_types=sub.event_types,
        is_active=sub.is_active,
        created_at=sub.created_at,
    )


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
async def register_webhook(body: SubscriptionRequest) -> SubscriptionResponse:
    """Register a new webhook subscription."""
    from app.application.webhooks.service import webhook_store

    invalid = [e for e in body.event_types if e not in _VALID_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event types: {invalid}. Valid: {sorted(_VALID_EVENTS)}",
        )

    sub = webhook_store.register(
        url=body.url,
        event_types=body.event_types,
        secret=body.secret,
    )
    return _to_response(sub)


@router.get(
    "",
    response_model=list[SubscriptionResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_webhooks() -> list[SubscriptionResponse]:
    """List all active webhook subscriptions."""
    from app.application.webhooks.service import webhook_store

    seen: dict[str, object] = {}
    for event_type in _VALID_EVENTS:
        for sub in webhook_store.list_active(event_type):
            seen.setdefault(str(sub.id), sub)
    return [_to_response(s) for s in seen.values()]


@router.delete(
    "/{subscription_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
async def unregister_webhook(subscription_id: uuid.UUID) -> None:
    """Remove a webhook subscription."""
    from app.application.webhooks.service import webhook_store

    removed = webhook_store.unregister(subscription_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription {subscription_id} not found",
        )
