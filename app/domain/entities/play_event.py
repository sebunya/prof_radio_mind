from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlayEvent:
    id: uuid.UUID
    station_id: uuid.UUID
    source_id: uuid.UUID
    collector_run_id: uuid.UUID
    played_at: datetime
    raw_artist: str
    raw_title: str
    # source_event_id is the opaque ID from the upstream source (e.g. Radiowave diary entry ID)
    source_event_id: str | None = None
    raw_label: str | None = None
    # SHA-256 fingerprint used for deduplication when source_event_id is absent
    fingerprint: str | None = None
    # radiowave | iheart | manual_csv — set by the collector or importer
    attribution: str | None = None

    @classmethod
    def create(
        cls,
        station_id: uuid.UUID,
        source_id: uuid.UUID,
        collector_run_id: uuid.UUID,
        played_at: datetime,
        raw_artist: str,
        raw_title: str,
        *,
        source_event_id: str | None = None,
        raw_label: str | None = None,
        fingerprint: str | None = None,
        attribution: str | None = None,
    ) -> PlayEvent:
        return cls(
            id=uuid.uuid4(),
            station_id=station_id,
            source_id=source_id,
            collector_run_id=collector_run_id,
            played_at=played_at,
            raw_artist=raw_artist,
            raw_title=raw_title,
            source_event_id=source_event_id,
            raw_label=raw_label,
            fingerprint=fingerprint,
            attribution=attribution,
        )
