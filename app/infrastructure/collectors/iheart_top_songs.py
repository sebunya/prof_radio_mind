"""Generic iHeart top-songs collector — reusable across all iHeart stations.

Polls GET https://api.iheart.com/api/v3/live-meta/stream/{id}/topSongs
every 6 hours and ingests the station's ranked most-played songs for the
rolling weekly period.

Unlike now-playing and recently-played, each entry here represents a chart
position rather than a timestamped broadcast event.  The attribution field
is "iheart_top_songs" and played_at is set to the snapshot fetch time.

VAL-IHEART-TOP-001: endpoint URL and response schema are UNVALIDATED.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.iheart import parse_iheart_top_songs

_DEFAULT_BASE_URL = "https://api.iheart.com/api/v3/live-meta/stream"
_REQUEST_TIMEOUT = 15.0


class IHeartTopSongsCollector(BaseCollector):
    """Collects an iHeart station's top-songs chart (any station, configurable ID).

    Usage::

        collector = IHeartTopSongsCollector(
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
        return f"{self.base_url}/{self.iheart_station_id}/topSongs"

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
                notes=f"iHeart topSongs HTTP 204 — station {self.iheart_station_id}",
            )
            return [], [ev]

        results = parse_iheart_top_songs(
            raw_bytes, http_status, iheart_station_id=self.iheart_station_id
        )
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=http_status,
                notes=f"iHeart topSongs empty for station {self.iheart_station_id}",
            )
            return [], [ev]

        plays = [
            PlayEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                played_at=r.snapshot_at,
                raw_artist=r.artist,
                raw_title=r.title,
                source_event_id=r.source_event_id,
                attribution="iheart_top_songs",
            )
            for r in results
        ]
        return plays, []
