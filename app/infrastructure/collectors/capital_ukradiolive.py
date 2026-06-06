"""Capital FM UK Radio Live playlist collector.

Fetches https://ukradiolive.com/capital-fm/playlist and parses it into PlayEvents.

VAL-CAPUK-URL-001 must be confirmed before this collector is enabled.
Run dry_run_capital_ukradiolive to validate HTML/JSON structure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import SimpleHTTPCollector
from app.infrastructure.parsers.ukradiolive import parse_ukradiolive_playlist


class CapitalUKRadioLiveCollector(SimpleHTTPCollector):
    """Collects Capital FM recently-played tracks from ukradiolive.com."""

    _DEFAULT_URL = "https://ukradiolive.com/capital-fm/playlist"

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
                notes=f"ukradiolive HTTP {http_status} — {self.url}",
            )
            return [], [ev]

        results = parse_ukradiolive_playlist(raw_bytes, http_status)
        if not results:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.PARSE_FAILURE,
                raw_http_status=http_status,
                notes="ukradiolive: no tracks parsed — inspect raw HTML",
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
                attribution="ukradiolive",
            )
            for r in results
        ]
        return plays, []
