"""KIIS-FM iHeart Now Playing collector.

CRITICAL BEHAVIOUR:
- HTTP 204 = commercial break or talk. Never call .json() on the body.
  204 must produce a NoTrackEvent(SOURCE_HTTP_204), not an exception.
- VAL-KIIS-001: station ID 2501 is UNVALIDATED — confirm before production.
- VAL-KIIS-003: HTTP 204 behaviour UNCONFIRMED — guard implemented regardless.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.iheart import parse_iheart_now_playing

_DEFAULT_BASE_URL = "https://api.iheart.com/api/v3/live-meta/stream"
_DEFAULT_STATION_ID = "2501"
_REQUEST_TIMEOUT = 15.0


class KIISIHeartCollector(BaseCollector):
    """Collects KIIS-FM now-playing data from the iHeart API."""

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        iheart_station_id: str = _DEFAULT_STATION_ID,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.base_url = base_url
        self.iheart_station_id = iheart_station_id

    def _build_url(self) -> str:
        return f"{self.base_url}/{self.iheart_station_id}/currentTrack"

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        url = self._build_url()
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(url)
        return response.content, response.status_code, response.headers.get("content-type")

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        # CRITICAL: 204 = no track — never parse body, produce NoTrackEvent
        if http_status == 204:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=204,
                notes="KIIS iHeart HTTP 204 — commercial break or talk",
            )
            return [], [ev]

        result = parse_iheart_now_playing(raw_bytes, http_status)
        if result is None:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
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
        )
        return [play], []
