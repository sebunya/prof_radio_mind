"""One-shot dry run for Capital FM UK — ukradiolive.com playlist.

VAL-CAPUK-URL-001: Tests https://ukradiolive.com/capital-fm/playlist as an
alternative source to the unvalidated Online Radio Box approach.

If the site uses Next.js SSR, the parser will find __NEXT_DATA__ and extract
the track list. If CSR-only, raw HTML will reveal the structure.

Raw HTML is saved to /tmp/capital_ukradiolive_raw.html for inspection.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_capital_ukradiolive

Inspect raw HTML after running:
    docker exec rmias-app-1 head -150 /tmp/capital_ukradiolive_raw.html

Look for __NEXT_DATA__:
    docker exec rmias-app-1 grep -o '__NEXT_DATA__' /tmp/capital_ukradiolive_raw.html
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

from app.core.settings import settings
from app.infrastructure.collectors.capital_ukradiolive import CapitalUKRadioLiveCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_capital_ukradiolive")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.CAPITALFM")
_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.ukradiolive")

_HTML_DUMP_PATH = Path("/tmp/capital_ukradiolive_raw.html")


async def run() -> None:
    logger.info("Capital FM UK — ukradiolive.com dry run")
    logger.info("URL: https://ukradiolive.com/capital-fm/playlist")

    collector = CapitalUKRadioLiveCollector(
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
                "0 plays. <script> tags: %d. __NEXT_DATA__: %s. "
                "Inspect %s to identify track list selectors.",
                script_count, next_data_present, _HTML_DUMP_PATH,
            )
            if no_tracks:
                logger.info("no_track notes: %s", no_tracks[0].notes)

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)

    logger.info("Capital FM ukradiolive.com dry run complete.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
