"""SQLAlchemy implementation of SourceValidationRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.validation.base import ValidationResult
from app.infrastructure.database.models.sources import SourceValidation


class SQLSourceValidationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, result: ValidationResult) -> None:
        self._session.add(
            SourceValidation(
                id=uuid.uuid4(),
                source_id=result.source_id,
                status=result.status.value,
                validation_code=result.validation_code,
                notes=result.notes,
                response_status_code=result.response_status_code,
                response_snapshot=result.response_snapshot,
                validated_at=result.validated_at,
                validated_by=result.validated_by,
            )
        )
        await self._session.flush()

    async def list_for_source(self, source_id: uuid.UUID) -> list[SourceValidation]:
        stmt = (
            select(SourceValidation)
            .where(SourceValidation.source_id == source_id)
            .order_by(SourceValidation.validated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def latest_for_source(self, source_id: uuid.UUID) -> SourceValidation | None:
        stmt = (
            select(SourceValidation)
            .where(SourceValidation.source_id == source_id)
            .order_by(SourceValidation.validated_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count_for_source(self, source_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(SourceValidation)
            .where(SourceValidation.source_id == source_id)
        )
        return result.scalar_one()
