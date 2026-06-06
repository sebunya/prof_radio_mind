"""radio-australia.org weekly chart collector.

Fetches https://www.radio-australia.org/{station-slug} and extracts the
server-side-rendered weekly top songs chart. Usable for any station on
that site — pass the full page URL at construction time.

NOTE: played_at is synthetic (time of collection). These are chart positions
representing plays over the preceding 7 days, not individual timed events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import SimpleHTTPCollector
from app.infrastructure.parsers.radio_australia_org import parse_radio_australia_chart


class RadioAustraliaOrgCollector(SimpleHTTPCollector):
    """Collects weekly chart data from radio-australia.org for any station."""

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
                reason=NoTrackReason.PARSE_FAILURE,
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
