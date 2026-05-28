"""SQLAlchemy repository for persisted webhook subscriptions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.operations import WebhookSubscriptionDB
from app.infrastructure.database.pagination import paginate


class SQLWebhookSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, row: WebhookSubscriptionDB) -> None:
        """Insert or merge a subscription row."""
        existing = await self._session.get(WebhookSubscriptionDB, row.id)
        if existing is None:
            self._session.add(row)
        else:
            existing.url = row.url
            existing.event_types = row.event_types
            existing.secret = row.secret
            existing.is_active = row.is_active
        await self._session.flush()

    async def delete(self, sub_id: uuid.UUID) -> bool:
        """Soft-delete (deactivate) a subscription. Returns True if found."""
        row = await self._session.get(WebhookSubscriptionDB, sub_id)
        if row is None:
            return False
        row.is_active = False
        await self._session.flush()
        return True

    async def hard_delete(self, sub_id: uuid.UUID) -> bool:
        """Hard-delete a subscription row. Returns True if found."""
        row = await self._session.get(WebhookSubscriptionDB, sub_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def list_active(self) -> list[WebhookSubscriptionDB]:
        """Return all active subscriptions."""
        result = await self._session.execute(
            select(WebhookSubscriptionDB).where(WebhookSubscriptionDB.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def list_page(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookSubscriptionDB], int]:
        """Return (rows, total_count) for paginated list endpoint."""
        stmt = (
            select(WebhookSubscriptionDB)
            .where(WebhookSubscriptionDB.is_active.is_(True))
            .order_by(WebhookSubscriptionDB.created_at.desc())
        )
        return await paginate(self._session, stmt, limit=limit, offset=offset)

    async def get(self, sub_id: uuid.UUID) -> WebhookSubscriptionDB | None:
        return await self._session.get(WebhookSubscriptionDB, sub_id)
