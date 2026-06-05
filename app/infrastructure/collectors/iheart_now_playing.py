"""Generic iHeart now-playing collector — reusable for any iHeart station.

Polls GET https://api.iheart.com/api/v3/live-meta/stream/{id}/currentTrack
every 5 minutes. Caller supplies iheart_station_id — no per-station subclass
needed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.iheart import parse_iheart_now_playing

_DEFAULT_BASE_URL = "https://api.iheart.com/api/v3/live-meta/stream"
_REQUEST_TIMEOUT = 15.0


class IHeartNowPlayingCollector(BaseCollector):
    """Collects iHeart now-playing data for any station (configurable station ID).

    Usage::

        collector = IHeartNowPlayingCollector(
            source_id=_KIIS_SOURCE_ID,
            station_id=_KIIS_STATION_ID,
            iheart_station_id="2501",
        )
        result = await collector.run()
    """

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        iheart_station_id: str,
        base_url: str = _DEFAULT_BASE_URL,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.iheart_station_id = iheart_station_id
        self.base_url = base_url

    def _build_url(self) -> str:
        return f"{self.base_url}/{self.iheart_station_id}/currentTrack"

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        from app.infrastructure.http.client import build_client

        async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(self._build_url())
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
                notes=f"iHeart HTTP 204 — station {self.iheart_station_id}",
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
            attribution="iheart",
        )
        return [play], []
