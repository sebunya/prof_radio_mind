"""Webhook subscription management API."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.webhooks.service import WebhookSubscription, webhook_store
from app.core.auth import require_api_key
from app.infrastructure.database.repositories.webhook_subscription_repo import (
    SQLWebhookSubscriptionRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_VALID_EVENTS = {"play.detected", "no_track.detected", "reconciliation.completed"}


class SubscriptionRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    event_types: list[str] = Field(..., max_length=10)
    secret: str | None = Field(None, max_length=512)


class SubscriptionResponse(BaseModel):
    id: str
    url: str
    event_types: list[str]
    is_active: bool
    created_at: datetime


def _to_response(sub: WebhookSubscription) -> SubscriptionResponse:
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
async def register_webhook(
    body: SubscriptionRequest,
    session: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Register a new webhook subscription (persisted to DB)."""
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
    try:
        await webhook_store.persist_register(sub, session)
        await session.commit()
    except Exception as exc:
        # Roll back in-memory add if DB write fails
        webhook_store.unregister(sub.id)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return _to_response(sub)


@router.get(
    "",
    response_model=list[SubscriptionResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_webhooks(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[SubscriptionResponse]:
    """List active webhook subscriptions.  Total in ``X-Total-Count`` header."""
    repo = SQLWebhookSubscriptionRepository(session)
    rows, total = await repo.list_page(limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(total)
    return [
        SubscriptionResponse(
            id=str(row.id),
            url=row.url,
            event_types=list(row.event_types or []),
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.delete(
    "/{subscription_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
async def unregister_webhook(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a webhook subscription (hard-deletes from DB)."""
    try:
        deleted = await webhook_store.persist_unregister(subscription_id, session)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription {subscription_id} not found",
        )
    # Also remove from in-memory store
    webhook_store.unregister(subscription_id)
