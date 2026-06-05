"""One-shot dry run for Heart FM — last-played-songs collector.

Runs a single fetch-parse-persist cycle without enabling the scheduler.

Source URL: https://www.heart.co.uk/radio/last-played-songs/
Parser:     REPAIRED 2026-06-05 (HEART-HTML-PARSER-FIX-1).
            Tries __NEXT_DATA__ JSON → new CSS (last_played_songs/song_wrapper) → old CSS.
robots.txt: PENDING — https://www.heart.co.uk/robots.txt not yet checked.
ToS review: PENDING (VAL-HEARTFM-007).

VAL-HEARTFM-002: PARSER_REPAIRED — awaiting live re-validation. This dry run
                 IS the live validation run.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_heart_fm
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid

from app.core.settings import settings
from app.domain.entities.collector_run import CollectorStatus
from app.infrastructure.collectors.heart_radio import HeartRadioCollector
from app.infrastructure.scheduler.scheduler import _persist_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_heart_fm")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.HEARTFMUK")
_SOURCE_ID = uuid.uuid5(_NS, "source.HEARTFMUK.heart_last_played")


async def run() -> None:
    logger.info("Heart FM dry run — last-played-songs page")
    logger.info("URL: https://www.heart.co.uk/radio/last-played-songs/")
    logger.info("Parser strategy: __NEXT_DATA__ JSON → new CSS → old CSS fallback")
    logger.info("NOTE: robots.txt + ToS review PENDING — do not enable scheduler job yet")
    logger.info("Storage root: %s", settings.raw_payload_storage_path)

    collector = HeartRadioCollector(
        source_id=_SOURCE_ID,
        station_id=_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )

    try:
        result = await collector.run()
        status_val = result.collector_run.status

        logger.info("Collector status: %s", status_val.value)
        if result.raw_payload:
            logger.info(
                "Raw payload: %d bytes  sha256=%s  http=%s",
                result.raw_payload.byte_size,
                result.raw_payload.sha256,
                result.raw_payload.http_status,
            )

        if result.play_events:
            logger.info("Tracks (%d):", len(result.play_events))
            for play in result.play_events:
                logger.info(
                    "  %s — %s  [played_at=%s  id=%s]",
                    play.raw_artist,
                    play.raw_title,
                    play.played_at,
                    play.source_event_id,
                )
        elif result.no_track_events:
            for ev in result.no_track_events:
                logger.info("NO_TRACK reason=%s  notes=%s", ev.reason, ev.notes)
        else:
            logger.info("No events extracted.")

        if result.collector_run.error_message:
            logger.error("Error: %s", result.collector_run.error_message)

        if status_val != CollectorStatus.FAILED:
            logger.info("Persisting results to database...")
            await _persist_result(result)
            logger.info("Persisted.")
        else:
            logger.info("Skipping DB persistence (collector FAILED).")

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)

    logger.info("Heart FM dry run complete.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
