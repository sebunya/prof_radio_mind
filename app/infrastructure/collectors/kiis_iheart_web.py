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
from app.infrastructure.collectors.base import SimpleHTTPCollector
from app.infrastructure.parsers.iheart_web import parse_iheart_web_recently_played


class KIISIHeartWebCollector(SimpleHTTPCollector):
    """Collects KIIS-FM 102.7 recently-played tracks from the iHeart station website."""

    _DEFAULT_URL = "https://kiisfm.iheart.com/music/recently-played/"

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
                reason=NoTrackReason.PARSE_FAILURE,
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
