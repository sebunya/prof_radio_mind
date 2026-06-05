"""Heart FM last-played-songs collector.

Fetches https://www.heart.co.uk/radio/last-played-songs/ every 15 minutes
and ingests all track entries visible on the page.  Deduplication uses a
2-hour window so tracks already captured in a prior poll are not double-counted.

VAL-HEARTFM-001: page reachability UNVALIDATED.
VAL-HEARTFM-002: CSS selectors UNVALIDATED — requires live page verification.
VAL-HEARTFM-007: polling cadence / ToS UNVALIDATED.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.heart import parse_heart_last_played

_DEFAULT_BASE_URL = "https://www.heart.co.uk/radio/last-played-songs/"
_REQUEST_TIMEOUT = 20.0


class HeartRadioCollector(BaseCollector):
    """Collects Heart FM recently-played tracks from the official last-played-songs page."""

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.base_url = base_url

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        from app.infrastructure.http.client import build_client

        async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(self.base_url)
        return response.content, response.status_code, response.headers.get("content-type")

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        if http_status == 204:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=204,
                notes="Heart FM HTTP 204 — no content",
            )
            return [], [ev]

        results = parse_heart_last_played(raw_bytes, http_status)
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes="Heart FM last-played-songs — no track entries found",
            )
            return [], [ev]

        plays = [
            PlayEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                played_at=r.played_at,
                raw_artist=r.artist,
                raw_title=r.title,
                source_event_id=r.source_event_id,
                attribution="heart",
            )
            for r in results
        ]
        return plays, []
