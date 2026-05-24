"""Nova 96.9 Radiowave diary collector.

Fetches the Radiowave diary page for IDDS=11129 and parses it into PlayEvents.
Uses BaseCollector lifecycle: fetch_raw → store payload + SHA-256 → parse.

VAL-NOVA-001 (IDDS=11129) must be confirmed before this collector is enabled
in production. See docs/VALIDATION_REGISTER.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.domain.entities.no_track_event import NoTrackEvent
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector
from app.infrastructure.parsers.radiowave import parse_radiowave_diary

_DEFAULT_BASE_URL = "https://www.radiowave.com.au/diary"
_DEFAULT_IDDS = "11129"
_REQUEST_TIMEOUT = 30.0


class NovaRadiowaveCollector(BaseCollector):
    """Collects Nova 96.9 airplay data from the Radiowave diary."""

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
        return f"{self.base_url}?idds={self.idds}&date={date_str}"

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
        )
        return result.play_events, []
