"""KIIS-FM 106.5 Sydney radio-australia.org weekly chart collector.

Fetches https://www.radio-australia.org/kiis-1065 and extracts the
server-side-rendered weekly top songs chart.

NOTE: played_at is synthetic (time of collection). These are chart positions
representing plays over the preceding 7 days, not individual timed events.

VAL-KIIS-RAO-001 validated SSR chart structure 2026-06-06.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.radio_australia_org import parse_radio_australia_chart

_DEFAULT_URL = "https://www.radio-australia.org/kiis-1065"
_REQUEST_TIMEOUT = 30.0


class KIISFMRadioAustraliaCollector(BaseCollector):
    """Collects KIIS-FM 106.5 weekly chart from radio-australia.org."""

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        url: str = _DEFAULT_URL,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.url = url

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        from app.infrastructure.http.client import build_client

        async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(self.url)
        return response.content, response.status_code, response.headers.get("content-type")

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        if http_status is not None and http_status >= 400:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes=f"radio-australia.org HTTP {http_status} — {self.url}",
            )
            return [], [ev]

        collected_at = datetime.now(tz=UTC)
        results = parse_radio_australia_chart(raw_bytes, http_status, collected_at)
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=collected_at,
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes="radio-australia.org: no chart items parsed",
            )
            return [], [ev]

        plays = [
            PlayEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                played_at=r.collected_at,
                raw_artist=r.artist,
                raw_title=r.title,
                attribution="radio_australia_org",
            )
            for r in results
        ]
        return plays, []
