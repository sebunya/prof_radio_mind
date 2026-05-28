"""Repository for email recipients and send-log entries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.notifications import EmailRecipientDB, EmailSendLogDB
from app.infrastructure.database.pagination import paginate


class SQLEmailRecipientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, row: EmailRecipientDB) -> None:
        existing = await self._session.get(EmailRecipientDB, row.id)
        if existing is None:
            self._session.add(row)
        else:
            existing.name = row.name
            existing.email = row.email
            existing.frequencies = row.frequencies
            existing.is_active = row.is_active
        await self._session.flush()

    async def get(self, recipient_id: uuid.UUID) -> EmailRecipientDB | None:
        return await self._session.get(EmailRecipientDB, recipient_id)

    async def get_by_email(self, email: str) -> EmailRecipientDB | None:
        result = await self._session.execute(
            select(EmailRecipientDB).where(EmailRecipientDB.email == email)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[EmailRecipientDB]:
        result = await self._session.execute(
            select(EmailRecipientDB)
            .where(EmailRecipientDB.is_active.is_(True))
            .order_by(EmailRecipientDB.created_at)
        )
        return list(result.scalars().all())

    async def list_for_frequency(self, frequency: str) -> list[EmailRecipientDB]:
        """Return all active recipients subscribed to the given frequency."""
        # JSONB contains operator: frequencies @> '["daily"]'

        result = await self._session.execute(
            select(EmailRecipientDB).where(
                EmailRecipientDB.is_active.is_(True),
                EmailRecipientDB.frequencies.contains([frequency]),  # type: ignore[attr-defined]
            )
        )
        return list(result.scalars().all())

    async def list_page(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EmailRecipientDB], int]:
        """Return (rows, total_count) for paginated list endpoint."""
        stmt = select(EmailRecipientDB).order_by(EmailRecipientDB.created_at)
        return await paginate(self._session, stmt, limit=limit, offset=offset)

    async def delete(self, recipient_id: uuid.UUID) -> bool:
        row = await self._session.get(EmailRecipientDB, recipient_id)
        if row is None:
            return False
        row.is_active = False
        await self._session.flush()
        return True


class SQLEmailSendLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, row: EmailSendLogDB) -> None:
        self._session.add(row)
        await self._session.flush()

    async def list_recent(self, limit: int = 50) -> list[EmailSendLogDB]:
        result = await self._session.execute(
            select(EmailSendLogDB)
            .order_by(EmailSendLogDB.sent_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_page(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EmailSendLogDB], int]:
        """Return (rows, total_count) for paginated log endpoint."""
        stmt = select(EmailSendLogDB).order_by(EmailSendLogDB.sent_at.desc())
        return await paginate(self._session, stmt, limit=limit, offset=offset)
