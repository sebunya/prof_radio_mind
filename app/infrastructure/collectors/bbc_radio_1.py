"""BBC Radio 1 now-playing collector via the BBC Sounds RMS API.

Polls GET https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest
every 5 minutes. The endpoint returns recently broadcast segments; the parser
picks the most recent music segment as the "now playing" track.

VAL-BBC1-001: live reachability UNVALIDATED.
VAL-BBC1-006: rate-limiting / ToS UNVALIDATED — guarded by enable_bbc_radio1_collector flag.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.bbc_sounds import parse_bbc_sounds_now_playing

_DEFAULT_BASE_URL = (
    "https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest"
)
_REQUEST_TIMEOUT = 15.0


class BBCRadio1Collector(BaseCollector):
    """Collects BBC Radio 1 now-playing data from the BBC Sounds RMS API."""

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
                notes="BBC Radio 1 HTTP 204 — no current segment",
            )
            return [], [ev]

        result = parse_bbc_sounds_now_playing(raw_bytes, http_status)
        if result is None:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes="BBC Radio 1 — no music segment in response",
            )
            return [], [ev]

        play = PlayEvent.create(
            station_id=self.station_id,
            source_id=self.source_id,
            collector_run_id=collector_run_id,
            played_at=result.played_at,
            raw_artist=result.artist,
            raw_title=result.title,
            source_event_id=result.source_event_id,
            attribution="bbc_sounds",
        )
        return [play], []
