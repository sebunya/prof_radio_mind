"""One-shot dry run for KIIS-FM 102.7 Los Angeles — Radiowave Monitor diary.

VAL-KIIS-RAD-001 FAILED: radiowavemonitor.com returns HTTP 200 but 0 matching
rows. Root cause: live page likely uses different HTML structure than the
synthetic fixture (tr.diary-row selectors not present in real ASP.NET page).

This script saves the raw HTML to /tmp/kiis1027_raw.html so the actual page
structure can be inspected and the parser selectors corrected.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_kiis1027

Inspect raw HTML after running:
    docker exec rmias-app-1 cat /tmp/kiis1027_raw.html | head -100
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.settings import settings
from app.infrastructure.collectors.kiis_radiowave import KIISRadiowaveCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_kiis1027")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.KIIS1027")
_SOURCE_ID = uuid.uuid5(_NS, "source.KIIS1027.radiowave")

_HTML_DUMP_PATH = Path("/tmp/kiis1027_raw.html")


async def run() -> None:
    today = datetime.now(tz=UTC).date()

    for days_back in [1, 2]:
        diary_date = today - timedelta(days=days_back)
        logger.info(
            "KIIS-FM 102.7 dry run — Radiowave Monitor diary (%s)", diary_date
        )
        logger.info(
            "URL: https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080&date=%s",
            diary_date,
        )
        logger.info("NOTE: VAL-KIIS-RAD-001 FAILED — expecting 0 rows; raw HTML will be saved.")

        collector = KIISRadiowaveCollector(
            source_id=_SOURCE_ID,
            station_id=_STATION_ID,
            diary_date=diary_date,
            storage_root=settings.raw_payload_storage_path,
        )

        try:
            # Fetch raw bytes directly so we can save them before parse
            raw_bytes, http_status, content_type = await collector.fetch_raw()

            logger.info(
                "[%s] HTTP=%s  content-type=%s  bytes=%d",
                diary_date, http_status, content_type, len(raw_bytes),
            )

            # Save raw HTML for selector inspection
            try:
                _HTML_DUMP_PATH.write_bytes(raw_bytes)
                logger.info(
                    "[%s] Raw HTML saved to %s — inspect with: "
                    "docker exec rmias-app-1 head -120 %s",
                    diary_date, _HTML_DUMP_PATH, _HTML_DUMP_PATH,
                )
            except OSError as e:
                logger.warning("Could not save raw HTML: %s", e)

            # Parse (expected to return 0 play events)
            run_id = uuid.uuid4()
            plays, no_tracks = collector.parse(raw_bytes, http_status, run_id)

            logger.info(
                "[%s] play_events=%d  no_track_events=%d",
                diary_date, len(plays), len(no_tracks),
            )

            if plays:
                logger.info("[%s] Tracks (unexpected — selectors may now match):", diary_date)
                for play in plays[:5]:
                    logger.info("  %s — %s  [%s]", play.raw_artist, play.raw_title, play.played_at)
            else:
                # Count <tr> elements in raw HTML to diagnose selector issue
                tr_count = raw_bytes.count(b"<tr")
                diary_row_count = raw_bytes.count(b"diary-row")
                logger.warning(
                    "[%s] 0 plays. Total <tr> tags in HTML: %d. "
                    "'diary-row' occurrences: %d. "
                    "If diary-row=0, selectors need updating — inspect %s",
                    diary_date, tr_count, diary_row_count, _HTML_DUMP_PATH,
                )

        except Exception as exc:
            logger.exception("[%s] Error: %s", diary_date, exc)

        logger.info("---")

    logger.info(
        "KIIS-FM 102.7 dry run complete. "
        "If diary-row=0 in both runs, inspect %s and report back "
        "so the parser selectors can be corrected.",
        _HTML_DUMP_PATH,
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
