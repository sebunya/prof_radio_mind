"""StreamTheWorld ICY metadata collector — backup source for Nova/KIIS.

Reads ICY metadata from a streaming HTTP radio endpoint. The metadata
is embedded in the stream as `StreamTitle=Artist - Title;` strings.

VAL-STW-001: Stream URL and ICY metadata format must be confirmed before enabling.
This collector is deferred in MVP — it serves as a fallback when Radiowave
and iHeart are unavailable.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

_ICY_META_RE = re.compile(r"StreamTitle='([^']*)'")
_REQUEST_TIMEOUT = 20.0
# Bytes to read from the stream before giving up on finding ICY metadata
_MAX_READ_BYTES = 64 * 1024


class StreamTheWorldICYCollector(BaseCollector):
    """Reads now-playing data from StreamTheWorld ICY stream metadata.

    ICY metadata is embedded in HTTP audio streams as inline blocks.
    The stream is read until the `Icy-MetaInt` boundary is found,
    then the `StreamTitle` field is extracted.
    """

    def __init__(
        self,
        source_id: uuid.UUID,
        station_id: uuid.UUID,
        *,
        stream_url: str,
        storage_root: str = "/data/raw_payloads",
    ) -> None:
        super().__init__(source_id, station_id, storage_root=storage_root)
        self.stream_url = stream_url

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        """Fetch raw ICY stream bytes and headers."""
        import httpx

        headers = {"Icy-MetaData": "1"}
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                async with client.stream("GET", self.stream_url, headers=headers) as resp:
                    status = resp.status_code
                    content_type = resp.headers.get("content-type")
                    raw = b""
                    async for chunk in resp.aiter_bytes():
                        raw += chunk
                        if len(raw) >= _MAX_READ_BYTES:
                            break
            return raw, status, content_type
        except Exception as exc:
            raise RuntimeError(f"ICY stream fetch failed: {exc}") from exc

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        """Extract StreamTitle from ICY metadata bytes."""
        if http_status and http_status != 200:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.UNKNOWN,
                raw_http_status=http_status,
                notes=f"StreamTheWorld HTTP {http_status}",
            )
            return [], [ev]

        try:
            text = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = ""

        match = _ICY_META_RE.search(text)
        if not match:
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.PARSE_FAILURE,
                notes="StreamTitle not found in ICY metadata",
            )
            return [], [ev]

        stream_title = match.group(1).strip()
        if not stream_title or stream_title.lower() in ("", "commercial", "ads"):
            ev = NoTrackEvent.create(
                station_id=self.station_id,
                source_id=self.source_id,
                collector_run_id=collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.COMMERCIAL_BREAK_OR_TALK,
                notes=f"StreamTitle='{stream_title}'",
            )
            return [], [ev]

        if " - " in stream_title:
            artist, _, title = stream_title.partition(" - ")
        else:
            artist = stream_title
            title = stream_title

        play = PlayEvent.create(
            station_id=self.station_id,
            source_id=self.source_id,
            collector_run_id=collector_run_id,
            played_at=datetime.now(tz=UTC),
            raw_artist=artist.strip(),
            raw_title=title.strip(),
            attribution="streamtheworld",
        )
        return [play], []
