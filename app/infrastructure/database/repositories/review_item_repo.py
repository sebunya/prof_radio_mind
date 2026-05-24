"""SQLAlchemy implementation of ReviewItemRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.review_item import ReviewItem as ReviewItemEntity
from app.domain.entities.review_item import ReviewItemStatus, ReviewItemType
from app.infrastructure.database.models.events import ReviewItem as ReviewItemModel


def _to_domain(row: ReviewItemModel) -> ReviewItemEntity:
    return ReviewItemEntity(
        id=row.id,
        status=ReviewItemStatus(row.status),
        item_type=ReviewItemType(row.item_type),
        title=row.title,
        description=row.description,
        collector_run_id=row.collector_run_id,
        station_id=row.station_id,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by,
        notes=row.notes,
        created_at=row.created_at,
    )


class SQLReviewItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: ReviewItemEntity) -> None:
        self._session.add(
            ReviewItemModel(
                id=item.id,
                status=item.status.value,
                item_type=item.item_type.value,
                title=item.title,
                description=item.description,
                collector_run_id=item.collector_run_id,
                station_id=item.station_id,
                resolved_at=item.resolved_at,
                resolved_by=item.resolved_by,
                notes=item.notes,
            )
        )
        await self._session.flush()

    async def get(self, item_id: uuid.UUID) -> ReviewItemEntity | None:
        row = await self._session.get(ReviewItemModel, item_id)
        return _to_domain(row) if row else None

    async def list(
        self, status: ReviewItemStatus | None = None
    ) -> list[ReviewItemEntity]:
        stmt = select(ReviewItemModel).order_by(ReviewItemModel.created_at.desc())
        if status is not None:
            stmt = stmt.where(ReviewItemModel.status == status.value)
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def update(self, item: ReviewItemEntity) -> None:
        row = await self._session.get(ReviewItemModel, item.id)
        if row:
            row.status = item.status.value
            row.resolved_at = item.resolved_at
            row.resolved_by = item.resolved_by
            row.notes = item.notes
            await self._session.flush()

    async def count_pending(self) -> int:
        stmt = select(ReviewItemModel).where(ReviewItemModel.status == "pending")
        result = await self._session.execute(stmt)
        return len(result.scalars().all())
