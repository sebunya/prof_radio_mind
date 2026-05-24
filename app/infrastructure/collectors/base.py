"""BaseCollector — full lifecycle contract for all collectors.

Every concrete collector must inherit from BaseCollector and implement
fetch_raw() and parse(). The run() method manages the lifecycle and
ensures raw payload storage and SHA-256 hashing happen on every run.

Invariants:
- A collector must never report success unless the raw payload is stored
  and hashed.
- A collector failure (exception or error status) must NOT propagate —
  it is caught and recorded as a failed CollectorRun.
- HTTP 204 responses produce a NoTrackEvent, never an exception.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.domain.entities.collector_run import CollectorRun, CollectorStatus
from app.domain.entities.no_track_event import NoTrackEvent
from app.domain.entities.play_event import PlayEvent
from app.domain.value_objects.raw_payload import RawPayload


@dataclass
class CollectorResult:
    collector_run: CollectorRun
    play_events: list[PlayEvent] = field(default_factory=list)
    no_track_events: list[NoTrackEvent] = field(default_factory=list)
    raw_payload: RawPayload | None = None


class BaseCollector(ABC):
    """Abstract base for all collectors.

    Subclasses must implement:
      - fetch_raw(): make the HTTP call (or read fixture) and return raw bytes + metadata
      - parse(): turn raw bytes into play/no-track events
    """

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        self.source_id = source_id
        self.station_id = station_id
        self.storage_root = storage_root

    @abstractmethod
    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        """Fetch raw bytes from the source.

        Returns:
            (raw_bytes, http_status_code, content_type)
        """
        ...

    @abstractmethod
    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        """Parse raw bytes into events.

        Must never call .json() or similar on a 204 response body.
        Must return ([], [no_track_event]) for HTTP 204.
        """
        ...

    async def run(self) -> CollectorResult:
        """Execute the full collector lifecycle.

        Catches all exceptions; sets collector status to FAILED on error.
        Does not re-raise — one collector failure must not stop others.
        """
        run = CollectorRun.create(self.source_id, self.station_id)
        run.transition(CollectorStatus.FETCHING)

        try:
            raw_bytes, http_status, content_type = await self.fetch_raw()
        except Exception as exc:
            run.fail(f"fetch_raw failed: {exc}")
            return CollectorResult(collector_run=run)

        run.transition(CollectorStatus.RAW_STORED)
        storage_path = self._build_storage_path(run.id)
        raw_payload = self._store_payload(
            run.id,
            raw_bytes,
            storage_path,
            content_type=content_type,
            http_status=http_status,
        )
        run.meta = {"sha256": raw_payload.sha256, "byte_size": raw_payload.byte_size}

        run.transition(CollectorStatus.PARSED)
        try:
            play_events, no_track_events = self.parse(raw_bytes, http_status, run.id)
        except Exception as exc:
            run.fail(f"parse failed: {exc}")
            return CollectorResult(collector_run=run, raw_payload=raw_payload)

        run.rows_fetched = len(play_events) + len(no_track_events)
        run.rows_parsed = len(play_events) + len(no_track_events)

        if not play_events and not no_track_events:
            run.transition(CollectorStatus.NO_CONTENT)
        else:
            run.transition(CollectorStatus.COMPLETED)

        return CollectorResult(
            collector_run=run,
            play_events=play_events,
            no_track_events=no_track_events,
            raw_payload=raw_payload,
        )

    def _build_storage_path(self, run_id: uuid.UUID) -> str:
        date_str = datetime.now(tz=UTC).strftime("%Y/%m/%d")
        return os.path.join(self.storage_root, date_str, f"{run_id}.bin")

    def _store_payload(
        self,
        run_id: uuid.UUID,
        raw_bytes: bytes,
        storage_path: str,
        *,
        content_type: str | None = None,
        http_status: int | None = None,
    ) -> RawPayload:
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
        with open(storage_path, "wb") as f:
            f.write(raw_bytes)

        return RawPayload.create(
            run_id,
            self.source_id,
            raw_bytes,
            storage_path,
            content_type=content_type,
            http_status=http_status,
        )
