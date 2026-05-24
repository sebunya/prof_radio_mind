"""ReviewItem domain entity — tracks items flagged for human review."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ReviewItemStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class ReviewItemType(StrEnum):
    DRIFT = "drift"
    PARSE_ERROR = "parse_error"
    LOW_CONFIDENCE = "low_confidence"
    SCHEMA_CHANGED = "schema_changed"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ReviewItem:
    id: uuid.UUID
    status: ReviewItemStatus
    item_type: ReviewItemType
    title: str
    description: str | None
    collector_run_id: uuid.UUID | None
    station_id: uuid.UUID | None
    resolved_at: datetime | None
    resolved_by: str | None
    notes: str | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        item_type: ReviewItemType,
        title: str,
        description: str | None = None,
        collector_run_id: uuid.UUID | None = None,
        station_id: uuid.UUID | None = None,
    ) -> ReviewItem:
        return cls(
            id=uuid.uuid4(),
            status=ReviewItemStatus.PENDING,
            item_type=item_type,
            title=title,
            description=description,
            collector_run_id=collector_run_id,
            station_id=station_id,
            resolved_at=None,
            resolved_by=None,
            notes=None,
            created_at=datetime.now(tz=UTC),
        )

    def resolve(self, resolved_by: str, notes: str | None = None) -> None:
        self.status = ReviewItemStatus.REVIEWED
        self.resolved_at = datetime.now(tz=UTC)
        self.resolved_by = resolved_by
        self.notes = notes

    def dismiss(self, resolved_by: str, notes: str | None = None) -> None:
        self.status = ReviewItemStatus.DISMISSED
        self.resolved_at = datetime.now(tz=UTC)
        self.resolved_by = resolved_by
        self.notes = notes

    def escalate(self, resolved_by: str, notes: str | None = None) -> None:
        self.status = ReviewItemStatus.ESCALATED
        self.resolved_at = datetime.now(tz=UTC)
        self.resolved_by = resolved_by
        self.notes = notes

    @property
    def is_open(self) -> bool:
        return self.status == ReviewItemStatus.PENDING
