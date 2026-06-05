"""KIIS-FM 102.7 iHeart web recently-played collector.

Fetches https://kiisfm.iheart.com/music/recently-played/ and parses it
into PlayEvents.  iHeart v3 API is entirely dead (HTTP 404 on all paths),
so this scrapes the public station website instead.

VAL-KIIS1027-WEB-001 must be confirmed before this collector is enabled.
Run dry_run_kiis_iheart_web to validate HTML structure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.iheart_web import parse_iheart_web_recently_played

_DEFAULT_URL = "https://kiisfm.iheart.com/music/recently-played/"
_REQUEST_TIMEOUT = 30.0


class KIISIHeartWebCollector(BaseCollector):
    """Collects KIIS-FM 102.7 recently-played tracks from the iHeart station website."""

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
                notes=f"iHeart web HTTP {http_status} — {self.url}",
            )
            return [], [ev]

        results = parse_iheart_web_recently_played(raw_bytes, http_status)
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes="iHeart web: no tracks parsed — page may be CSR-only",
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
                attribution="iheart_web",
            )
            for r in results
        ]
        return plays, []
