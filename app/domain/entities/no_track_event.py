from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class NoTrackReason(StrEnum):
    COMMERCIAL_BREAK_OR_TALK = "commercial_break_or_talk"
    SOURCE_HTTP_204 = "source_http_204"
    PARSE_FAILURE = "parse_failure"
    UNKNOWN = "unknown"


@dataclass
class NoTrackEvent:
    id: uuid.UUID
    station_id: uuid.UUID
    source_id: uuid.UUID
    collector_run_id: uuid.UUID
    observed_at: datetime
    reason: NoTrackReason
    raw_http_status: int | None = None
    notes: str | None = None

    @classmethod
    def create(
        cls,
        station_id: uuid.UUID,
        source_id: uuid.UUID,
        collector_run_id: uuid.UUID,
        observed_at: datetime,
        reason: NoTrackReason,
        *,
        raw_http_status: int | None = None,
        notes: str | None = None,
    ) -> NoTrackEvent:
        return cls(
            id=uuid.uuid4(),
            station_id=station_id,
            source_id=source_id,
            collector_run_id=collector_run_id,
            observed_at=observed_at,
            reason=reason,
            raw_http_status=raw_http_status,
            notes=notes,
        )
