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
from app.infrastructure.collectors.base import SimpleHTTPCollector
from app.infrastructure.parsers.radoxo import parse_radoxo_playlist


class NovaRadoxoCollector(SimpleHTTPCollector):
    """Collects Nova 96.9 recently-played playlist from radoxo.com."""

    _DEFAULT_URL = "https://radoxo.com/australia/nova-969/playlist"

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
                reason=NoTrackReason.SOURCE_HTTP_ERROR,
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
                reason=NoTrackReason.PARSE_FAILURE,
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
