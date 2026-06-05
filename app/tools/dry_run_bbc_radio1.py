"""One-shot dry run for BBC Radio 1 — BBC Sounds RMS API collector.

Runs a single fetch-parse-persist cycle without enabling the scheduler.

VAL-BBC1-001: endpoint reachability PASSED (rms.api.bbc.co.uk live).
VAL-BBC1-006: BBC Developer Terms review PENDING — production enablement
              blocked until a human records PASS in VALIDATION_REGISTER.md.

This dry run is safe to execute; it hits the BBC RMS API once and records
the result. It does NOT enable the scheduler job.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_bbc_radio1
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid

from app.core.settings import settings
from app.domain.entities.collector_run import CollectorStatus
from app.infrastructure.collectors.bbc_radio_1 import BBCRadio1Collector
from app.infrastructure.scheduler.scheduler import _persist_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_bbc_radio1")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.BBCRADIO1")
_SOURCE_ID = uuid.uuid5(_NS, "source.BBCRADIO1.bbc_sounds")


async def run() -> None:
    logger.info("BBC Radio 1 dry run — BBC Sounds RMS API")
    logger.info("URL: https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest")
    logger.info("NOTE: VAL-BBC1-006 (ToS review) PENDING — do not enable scheduler job yet")
    logger.info("Storage root: %s", settings.raw_payload_storage_path)

    collector = BBCRadio1Collector(
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
                "Raw payload: %d bytes  sha256=%s",
                result.raw_payload.byte_size,
                result.raw_payload.sha256,
            )

        if result.play_events:
            logger.info("Tracks (%d):", len(result.play_events))
            for play in result.play_events:
                logger.info(
                    "  %s — %s  [played_at=%s]",
                    play.raw_artist,
                    play.raw_title,
                    play.played_at,
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

    logger.info("BBC Radio 1 dry run complete.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
