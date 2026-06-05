"""One-shot dry run for Nova 96.9 — Radiowave diary collector.

Runs a single fetch-parse-persist cycle without enabling the scheduler.

Source URL: https://www.radiowave.com.au/diary?idds=11129
VAL-NOVA-001: UNVALIDATED — radiowave.com.au was never tested live (D5 diagnostic
              used wrong domain radiowavemonitor.com). This dry run IS the live test.
robots.txt:   PENDING — https://www.radiowave.com.au/robots.txt not yet checked.
ToS review:   PENDING.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_nova969
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime, timedelta

from app.core.settings import settings
from app.domain.entities.collector_run import CollectorStatus
from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector
from app.infrastructure.scheduler.scheduler import _persist_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dry_run_nova969")

_NS = uuid.NAMESPACE_DNS
_STATION_ID = uuid.uuid5(_NS, "station.NOVA969")
_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radiowave")


async def run() -> None:
    today = datetime.now(tz=UTC).date()
    # Radiowave diary is a daily chart; try yesterday and today
    for days_back in [1, 0]:
        diary_date = today - timedelta(days=days_back)
        label = "yesterday" if days_back == 1 else "today"
        logger.info("Nova 96.9 dry run — Radiowave diary (%s: %s)", label, diary_date)

        collector = NovaRadiowaveCollector(
            source_id=_SOURCE_ID,
            station_id=_STATION_ID,
            diary_date=diary_date,
            storage_root=settings.raw_payload_storage_path,
        )

        try:
            result = await collector.run()
            status_val = result.collector_run.status

            logger.info("[%s] status=%s", diary_date, status_val.value)
            if result.raw_payload:
                logger.info(
                    "[%s] raw payload: %d bytes  sha256=%s",
                    diary_date,
                    result.raw_payload.byte_size,
                    result.raw_payload.sha256,
                )

            if result.play_events:
                logger.info("[%s] Tracks (%d):", diary_date, len(result.play_events))
                for play in result.play_events[:10]:
                    logger.info(
                        "  %s — %s  [played_at=%s]",
                        play.raw_artist,
                        play.raw_title,
                        play.played_at,
                    )
                if len(result.play_events) > 10:
                    logger.info("  ... and %d more", len(result.play_events) - 10)
            elif result.no_track_events:
                for ev in result.no_track_events:
                    logger.info(
                        "[%s] NO_TRACK reason=%s  notes=%s",
                        diary_date, ev.reason, ev.notes,
                    )
            else:
                logger.info("[%s] No events extracted.", diary_date)

            if result.collector_run.error_message:
                logger.error("[%s] Error: %s", diary_date, result.collector_run.error_message)

            if status_val != CollectorStatus.FAILED:
                logger.info("[%s] Persisting to database...", diary_date)
                await _persist_result(result)
                logger.info("[%s] Persisted.", diary_date)
            else:
                logger.info("[%s] Skipping DB persistence (FAILED).", diary_date)

        except Exception as exc:
            logger.exception("[%s] Unexpected error: %s", diary_date, exc)

    logger.info("Nova 96.9 dry run complete.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
