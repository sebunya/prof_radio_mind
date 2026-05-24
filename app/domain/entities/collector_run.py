from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CollectorStatus(StrEnum):
    SCHEDULED = "scheduled"
    VALIDATING = "validating"
    FETCHING = "fetching"
    RAW_STORED = "raw_stored"
    PARSED = "parsed"
    NORMALIZED = "normalized"
    PERSISTED = "persisted"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    NO_CONTENT = "no_content"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    SCHEMA_CHANGED = "schema_changed"
    AUTH_REQUIRED = "auth_required"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    DEGRADED = "degraded"
    FALLBACK_USED = "fallback_used"


@dataclass
class CollectorRun:
    id: uuid.UUID
    source_id: uuid.UUID
    station_id: uuid.UUID
    status: CollectorStatus = CollectorStatus.SCHEDULED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rows_fetched: int | None = None
    rows_parsed: int | None = None
    rows_persisted: int | None = None
    error_message: str | None = None
    meta: dict | None = None

    @classmethod
    def create(cls, source_id: uuid.UUID, station_id: uuid.UUID) -> CollectorRun:
        return cls(id=uuid.uuid4(), source_id=source_id, station_id=station_id)

    def transition(self, status: CollectorStatus) -> None:
        self.status = status

    def fail(self, message: str) -> None:
        self.status = CollectorStatus.FAILED
        self.error_message = message
