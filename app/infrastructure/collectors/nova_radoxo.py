"""Nova 96.9 radoxo.com playlist collector.

Fetches https://radoxo.com/australia/nova-969/playlist and parses the
full day's playlist with exact Unix-timestamp broadcast times.

VAL-NOVA-RADOXO-001: parser selectors confirmed on real HTML 2026-06-06.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.radoxo import parse_radoxo_playlist

_DEFAULT_URL = "https://radoxo.com/australia/nova-969/playlist"
_REQUEST_TIMEOUT = 30.0


class NovaRadoxoCollector(BaseCollector):
    """Collects Nova 96.9 recently-played playlist from radoxo.com."""

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
                notes=f"radoxo HTTP {http_status} — {self.url}",
            )
            return [], [ev]

        results = parse_radoxo_playlist(raw_bytes, http_status)
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes="radoxo: no tracks parsed — inspect raw HTML",
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
                attribution="radoxo",
            )
            for r in results
        ]
        return plays, []
