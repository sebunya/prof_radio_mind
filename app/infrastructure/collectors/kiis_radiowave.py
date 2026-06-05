"""KIIS-FM 102.7 Radiowave Monitor diary collector.

Fetches the Radiowave Monitor diary for IDDS=5080 (KIIS-FM Los Angeles) and
parses it into PlayEvents.  Uses the shared parse_radiowave_diary parser with
America/Los_Angeles timezone so HH:MM diary times are converted correctly.

Source URL: https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date=YYYY-MM-DD

VAL-KIIS-RAD-001 must be confirmed before this collector is enabled in production.
See docs/VALIDATION_REGISTER.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.domain.entities.no_track_event import NoTrackEvent
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.radiowave import parse_radiowave_diary

_DEFAULT_BASE_URL = "https://www.radiowavemonitor.com/pub_charts/diaries.aspx"
_DEFAULT_IDDS = "5080"
_REQUEST_TIMEOUT = 30.0
_LOS_ANGELES = ZoneInfo("America/Los_Angeles")


class KIISRadiowaveCollector(BaseCollector):
    """Collects KIIS-FM 102.7 airplay data from the Radiowave Monitor diary."""

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        idds: str = _DEFAULT_IDDS,
        diary_date: date | None = None,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.base_url = base_url
        self.idds = idds
        self.diary_date = diary_date or datetime.now(tz=UTC).date()

    def _build_url(self) -> str:
        date_str = self.diary_date.strftime("%Y-%m-%d")
        return f"{self.base_url}?IDDS={self.idds}&date={date_str}"

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        from app.infrastructure.http.client import build_client

        url = self._build_url()
        async with await build_client(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(url)
        return response.content, response.status_code, response.headers.get("content-type")

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        result = parse_radiowave_diary(
            raw_bytes,
            source_id=self.source_id,
            station_id=self.station_id,
            collector_run_id=collector_run_id,
            diary_date=self.diary_date,
            station_timezone=_LOS_ANGELES,
        )
        return result.play_events, []
