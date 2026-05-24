"""APScheduler wiring — registers all background collection and reconciliation jobs."""

from __future__ import annotations

import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.settings import settings
from app.infrastructure.collectors.kiis_iheart import KIISIHeartCollector
from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector

logger = logging.getLogger(__name__)

# Deterministic station/source IDs — match what the DB seeder assigns at first run.
# Derived from seed call-signs so they are stable across restarts.
_NOVA_STATION_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "station.NOVA969")
_NOVA_SOURCE_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "source.NOVA969.radiowave")
_KIIS_STATION_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "station.KIISFM")
_KIIS_SOURCE_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "source.KIISFM.iheart")


async def job_collect_nova_diary() -> None:
    """Collect Nova 96.9 Radiowave diary for the previous day (runs daily 16:00 UTC)."""
    collector = NovaRadiowaveCollector(
        source_id=_NOVA_SOURCE_ID,
        station_id=_NOVA_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "nova_diary_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )


async def job_collect_kiis_now_playing() -> None:
    """Poll KIIS-FM iHeart now-playing endpoint (runs every 5 minutes)."""
    collector = KIISIHeartCollector(
        source_id=_KIIS_SOURCE_ID,
        station_id=_KIIS_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.debug(
        "kiis_now_playing status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )


async def job_nightly_reconciliation() -> None:
    """Nightly deduplication and normalization reconciliation (runs daily 17:00 UTC).

    Full implementation wired in Pass 17 when ReviewItem workflow is complete.
    """
    logger.info("nightly_reconciliation started — stub, no-op in MVP")


def build_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance with all registered jobs."""
    sched = AsyncIOScheduler(timezone="UTC")

    # Nova Radiowave diary — 16:00 UTC daily (02:00 AEST)
    sched.add_job(
        job_collect_nova_diary,
        CronTrigger(hour=16, minute=0, timezone="UTC"),
        id="nova_daily_diary",
        name="Nova 96.9 Radiowave diary",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # KIIS iHeart now-playing — every 5 minutes
    sched.add_job(
        job_collect_kiis_now_playing,
        IntervalTrigger(minutes=5),
        id="kiis_now_playing",
        name="KIIS-FM iHeart now-playing poll",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Nightly reconciliation — 17:00 UTC daily (03:00 AEST)
    sched.add_job(
        job_nightly_reconciliation,
        CronTrigger(hour=17, minute=0, timezone="UTC"),
        id="nightly_reconciliation",
        name="Nightly deduplication & normalization reconciliation",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    return sched
