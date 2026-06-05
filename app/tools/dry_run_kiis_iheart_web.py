"""One-shot dry run for KIIS-FM 102.7 iHeart web recently-played.

VAL-KIIS1027-WEB-001: iHeart v3 API is entirely dead (404 all paths).
This script tests the public iHeart station page instead:
  https://kiisfm.iheart.com/music/recently-played/

The page is likely a Next.js app. If it uses SSR, __NEXT_DATA__ will contain
the track list and the parser will extract songs. If it is CSR-only (skeleton
HTML + client-side fetch), the parser will return 0 tracks and the raw HTML
will show a minimal skeleton — we would then need to find the underlying API.

Raw HTML is saved to /tmp/kiis_iheart_web_raw.html for inspection.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_kiis_iheart_web

Inspect raw HTML after running:
    docker exec rmias-app-1 head -150 /tmp/kiis_iheart_web_raw.html

Look for __NEXT_DATA__:
    docker exec rmias-app-1 grep -o '__NEXT_DATA__' /tmp/kiis_iheart_web_raw.html
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

from app.core.settings import settings
from app.infrastructure.collectors.kiis_iheart_web import KIISIHeartWebCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_kiis_iheart_web")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.KIIS1027")
_SOURCE_ID = uuid.uuid5(_NS, "source.KIIS1027.iheart_web")

_HTML_DUMP_PATH = Path("/tmp/kiis_iheart_web_raw.html")


async def run() -> None:
    logger.info("KIIS-FM 102.7 iHeart web dry run")
    logger.info("URL: https://kiisfm.iheart.com/music/recently-played/")

    collector = KIISIHeartWebCollector(
        source_id=_SOURCE_ID,
        station_id=_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )

    try:
        raw_bytes, http_status, content_type = await collector.fetch_raw()
        logger.info(
            "HTTP=%s  content-type=%s  bytes=%d",
            http_status, content_type, len(raw_bytes),
        )

        try:
            _HTML_DUMP_PATH.write_bytes(raw_bytes)
            logger.info(
                "Raw HTML saved to %s — inspect with: "
                "docker exec rmias-app-1 head -150 %s",
                _HTML_DUMP_PATH, _HTML_DUMP_PATH,
            )
        except OSError as e:
            logger.warning("Could not save raw HTML: %s", e)

        next_data_present = b"__NEXT_DATA__" in raw_bytes
        logger.info("__NEXT_DATA__ present in HTML: %s", next_data_present)

        run_id = uuid.uuid4()
        plays, no_tracks = collector.parse(raw_bytes, http_status, run_id)

        logger.info("play_events=%d  no_track_events=%d", len(plays), len(no_tracks))

        if plays:
            logger.info("Tracks (parser succeeded):")
            for play in plays[:10]:
                logger.info("  %s — %s  [%s]", play.raw_artist, play.raw_title, play.played_at)
            if len(plays) > 10:
                logger.info("  ... and %d more", len(plays) - 10)
        else:
            script_count = raw_bytes.count(b"<script")
            logger.warning(
                "0 plays. <script> tags in HTML: %d. "
                "__NEXT_DATA__: %s. "
                "If __NEXT_DATA__ is False, this is CSR-only — "
                "inspect %s for the underlying API URL in XHR calls.",
                script_count, next_data_present, _HTML_DUMP_PATH,
            )
            if no_tracks:
                logger.info("no_track notes: %s", no_tracks[0].notes)

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)

    logger.info("KIIS-FM 102.7 iHeart web dry run complete.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
