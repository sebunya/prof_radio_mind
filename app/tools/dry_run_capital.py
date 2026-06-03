"""One-shot dry run for Capital FM UK Online Radio Box collector.

Runs a single fetch-parse-persist cycle without enabling the scheduler
or triggering recurring loops.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_capital

This module is the canonical way to invoke the dry run. The file at
scripts/dry_run_capital.py is a thin backwards-compatible wrapper that
delegates here.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid

from app.core.settings import settings
from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector
from app.infrastructure.scheduler.scheduler import _persist_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("capital_dry_run")

_NS = uuid.NAMESPACE_DNS
_CAPITAL_STATION_ID = uuid.uuid5(_NS, "station.CAPITALFM")
_CAPITAL_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.online_radio_box")


async def run_dry_run() -> None:
    masked_db_url = settings.database_url
    if "@" in masked_db_url:
        parts = masked_db_url.split("@")
        cred_parts = parts[0].split("//")
        masked_db_url = f"{cred_parts[0]}//****:****@{parts[1]}"

    logger.info("Starting Capital FM UK One-Shot Dry Run...")
    logger.info("Target Source: %s", "https://onlineradiobox.com/uk/capitalfmuk/")
    logger.info("Database URL (masked): %s", masked_db_url)
    logger.info("Storage root: %s", settings.raw_payload_storage_path)

    collector = OnlineRadioBoxCollector(
        source_id=_CAPITAL_SOURCE_ID,
        station_id=_CAPITAL_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )

    try:
        result = await collector.run()
        status_val = result.collector_run.status

        logger.info("--- Execution Results ---")
        logger.info("Collector status: %s", status_val.value)

        http_status_val = result.raw_payload.http_status if result.raw_payload else "None"
        logger.info("HTTP status: %s", http_status_val)

        if result.play_events:
            for play in result.play_events:
                logger.info(
                    "Extracted Track: %s - %s (played_at=%s, source_event_id=%s)",
                    play.raw_artist,
                    play.raw_title,
                    play.played_at,
                    play.source_event_id,
                )
        elif result.no_track_events:
            for no_track in result.no_track_events:
                logger.info(
                    "No Track Event: reason=%s, notes=%s", no_track.reason, no_track.notes
                )
        else:
            logger.info("No events extracted (missing now-playing).")

        if result.raw_payload:
            logger.info("Raw payload saved: %s", result.raw_payload.storage_path)
            logger.info(
                "Raw payload size: %d bytes, SHA256: %s",
                result.raw_payload.byte_size,
                result.raw_payload.sha256,
            )
        else:
            logger.info("Raw payload saved to disk: No")

        if result.collector_run.error_message:
            logger.error("Collector run error message: %s", result.collector_run.error_message)

        from app.domain.entities.collector_run import CollectorStatus

        if status_val != CollectorStatus.FAILED:
            logger.info("Persisting results to database...")
            await _persist_result(result)
            logger.info("Database records successfully created.")
        else:
            logger.info("Skipping database persistence due to execution failure.")

    except Exception as exc:
        logger.exception("Unexpected execution error: %s", exc)
        sys.exit(1)

    logger.info("One-Shot Dry Run Completed.")


def main() -> None:
    asyncio.run(run_dry_run())


if __name__ == "__main__":
    main()
