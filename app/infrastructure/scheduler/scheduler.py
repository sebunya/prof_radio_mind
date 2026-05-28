"""APScheduler wiring — registers all background collection and reconciliation jobs.

Job-store persistence
---------------------
By default APScheduler keeps scheduled fire-times in memory only, which means
that if the process restarts between midnight and the scheduled run time those
jobs are silently lost.

To fix this, ``build_scheduler()`` attempts to configure a ``SQLAlchemyJobStore``
backed by the same PostgreSQL database used for application data.  On restart
APScheduler reloads the persisted next-run times and immediately fires any job
whose scheduled time has passed within its ``misfire_grace_time`` window.

The job store requires the *sync* ``psycopg2`` driver (``psycopg2-binary`` in
``pyproject.toml``) which is separate from the async ``asyncpg`` driver used by
the main application.  If the job store cannot be configured (missing driver,
unreachable database) the scheduler falls back to the default in-memory store —
all other functionality remains unaffected.
"""

from __future__ import annotations

import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.settings import settings
from app.infrastructure.collectors.capital_iheart import CapitalIHeartCollector
from app.infrastructure.collectors.kiis_iheart import KIISIHeartCollector
from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector

logger = logging.getLogger(__name__)

# Deterministic IDs — must match app.application.seeder._NS derivation exactly.
_NS = uuid.NAMESPACE_DNS
_NOVA_STATION_ID = uuid.uuid5(_NS, "station.NOVA969")
_NOVA_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radiowave")
_KIIS_STATION_ID = uuid.uuid5(_NS, "station.KIISFM")
_KIIS_SOURCE_ID = uuid.uuid5(_NS, "source.KIISFM.iheart")
_CAPITAL_STATION_ID = uuid.uuid5(_NS, "station.CAPITALFM")
_CAPITAL_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.iheart")


async def _persist_result(result: object) -> None:
    """Persist a CollectorResult (runs, payloads, events) to the DB."""
    from app.application.normalization.normalizer import (
        compute_fingerprint,
        strip_label_from_artist,
    )
    from app.infrastructure.collectors.base import CollectorResult
    from app.infrastructure.database.repositories.collector_run_repo import (
        SQLCollectorRunRepository,
    )
    from app.infrastructure.database.repositories.no_track_event_repo import (
        SQLNoTrackEventRepository,
    )
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.raw_payload_repo import SQLRawPayloadRepository
    from app.infrastructure.database.session import _get_factory as _factory

    if not isinstance(result, CollectorResult):
        return

    try:
        async with _factory()() as session:
            run_repo = SQLCollectorRunRepository(session)
            await run_repo.save(result.collector_run)

            if result.raw_payload:
                payload_repo = SQLRawPayloadRepository(session)
                await payload_repo.save(result.raw_payload)

            play_repo = SQLPlayEventRepository(session)
            for play_event in result.play_events:
                # Compute fingerprint from normalised artist + title if absent
                if not play_event.fingerprint:
                    clean_artist = strip_label_from_artist(play_event.raw_artist)
                    play_event.fingerprint = compute_fingerprint(
                        clean_artist, play_event.raw_title
                    )
                # Deduplicate: skip if the same fingerprint was seen within 6 hours
                if play_event.fingerprint and await play_repo.exists_by_fingerprint(
                    station_id=play_event.station_id,
                    fingerprint=play_event.fingerprint,
                    within_seconds=6 * 3600,
                ):
                    logger.debug(
                        "play_event_duplicate_skipped fingerprint=%s station=%s",
                        play_event.fingerprint,
                        play_event.station_id,
                    )
                    continue
                await play_repo.save(play_event)

            no_track_repo = SQLNoTrackEventRepository(session)
            for no_track_event in result.no_track_events:
                await no_track_repo.save(no_track_event)

            await session.commit()
    except Exception as exc:
        logger.error("persist_result_failed error=%s run_id=%s", exc, result.collector_run.id)


async def job_collect_nova_diary() -> None:
    """Collect Nova 96.9 Radiowave diary for the previous day (runs daily 16:00 UTC)."""
    try:
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
        await _persist_result(result)
    except Exception as exc:
        logger.error("job_collect_nova_diary_failed error=%s", exc, exc_info=True)


async def job_collect_kiis_now_playing() -> None:
    """Poll KIIS-FM iHeart now-playing endpoint (runs every 5 minutes)."""
    try:
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
        await _persist_result(result)
    except Exception as exc:
        logger.error("job_collect_kiis_now_playing_failed error=%s", exc, exc_info=True)


async def job_collect_capital_now_playing() -> None:
    """Poll Capital FM iHeart now-playing endpoint (runs every 5 minutes)."""
    try:
        collector = CapitalIHeartCollector(
            source_id=_CAPITAL_SOURCE_ID,
            station_id=_CAPITAL_STATION_ID,
            storage_root=settings.raw_payload_storage_path,
        )
        result = await collector.run()
        logger.debug(
            "capital_now_playing status=%s plays=%d no_tracks=%d",
            result.collector_run.status.value,
            len(result.play_events),
            len(result.no_track_events),
        )
        await _persist_result(result)
    except Exception as exc:
        logger.error("job_collect_capital_now_playing_failed error=%s", exc, exc_info=True)


async def job_send_daily_email() -> None:
    """Send daily email report to subscribed recipients (runs 22:00 UTC = 08:00 AEST)."""
    try:
        from app.application.reports.email_report_builder import send_frequency_report

        result = await send_frequency_report("daily")
        logger.info("daily_email_report_done result=%s", result)
    except Exception as exc:
        logger.error("job_send_daily_email_failed error=%s", exc, exc_info=True)


async def job_send_weekly_email() -> None:
    """Send weekly email report every Monday 22:00 UTC (= Tue 08:00 AEST)."""
    try:
        from app.application.reports.email_report_builder import send_frequency_report

        result = await send_frequency_report("weekly")
        logger.info("weekly_email_report_done result=%s", result)
    except Exception as exc:
        logger.error("job_send_weekly_email_failed error=%s", exc, exc_info=True)


async def job_send_monthly_email() -> None:
    """Send monthly email report on 1st of month 22:00 UTC (= 2nd 08:00 AEST)."""
    try:
        from app.application.reports.email_report_builder import send_frequency_report

        result = await send_frequency_report("monthly")
        logger.info("monthly_email_report_done result=%s", result)
    except Exception as exc:
        logger.error("job_send_monthly_email_failed error=%s", exc, exc_info=True)


async def job_check_trend_alerts() -> None:
    """Detect trending / new-entry songs and fire webhook events (runs 23:00 UTC daily)."""
    try:
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts

        summary = await check_and_fire_trend_alerts()
        logger.info("trend_alerts_done summary=%s", summary)
    except Exception as exc:
        logger.error("job_check_trend_alerts_failed error=%s", exc, exc_info=True)


async def job_nightly_reconciliation() -> None:
    """Nightly deduplication and normalization reconciliation (runs daily 17:00 UTC)."""
    from datetime import UTC, datetime, timedelta

    from app.application.normalization.normalizer import (
        compute_fingerprint,
        strip_label_from_artist,
    )
    from app.domain.entities.review_item import ReviewItem, ReviewItemType
    from app.infrastructure.database.repositories.review_item_repo import SQLReviewItemRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository
    from app.infrastructure.database.session import _get_factory as _factory

    now = datetime.now(UTC)
    window_start = now - timedelta(hours=25)
    total_dupes = 0

    try:
        async with _factory()() as session:
            station_repo = SQLStationRepository(session)
            review_repo = SQLReviewItemRepository(session)
            stations = await station_repo.list_active()

            for station in stations:
                from app.infrastructure.database.repositories.play_event_repo import (
                    SQLPlayEventRepository,
                )

                play_repo = SQLPlayEventRepository(session)
                events = await play_repo.list_for_station(station.id, window_start, now)

                seen: set[str] = set()
                dupes = 0
                for event in events:
                    artist = strip_label_from_artist(event.raw_artist)
                    fp = event.fingerprint or compute_fingerprint(artist, event.raw_title)
                    if fp in seen:
                        dupes += 1
                    else:
                        seen.add(fp)

                if dupes > 0:
                    total_dupes += dupes
                    item = ReviewItem.create(
                        item_type=ReviewItemType.MANUAL_REVIEW,
                        title=f"Duplicate plays detected: {station.name}",
                        description=(
                            f"{dupes} potential duplicate play(s) in the last 25h "
                            f"for {station.call_sign}."
                        ),
                        station_id=station.id,
                    )
                    await review_repo.add(item)

            summary = ReviewItem.create(
                item_type=ReviewItemType.MANUAL_REVIEW,
                title="Nightly reconciliation completed",
                description=(
                    f"Reconciliation window: {window_start.date()} – {now.date()}. "
                    f"Stations checked: {len(stations)}. "
                    f"Potential duplicates flagged: {total_dupes}."
                ),
            )
            await review_repo.add(summary)
            await session.commit()

    except Exception as exc:
        logger.error("nightly_reconciliation_failed error=%s", exc)

    logger.info("nightly_reconciliation completed total_dupes=%d", total_dupes)


def _build_job_stores() -> dict:
    """Build APScheduler job stores.

    Returns a dict mapping ``"default"`` to a ``SQLAlchemyJobStore`` when the
    PostgreSQL database is reachable, or an empty dict (APScheduler falls back
    to its built-in ``MemoryJobStore``) when it isn't.

    The store uses psycopg2 (sync) rather than asyncpg because APScheduler's
    SQLAlchemy integration is synchronous.  Both drivers can coexist — asyncpg
    is used by the main async application, psycopg2 only by the scheduler.
    """
    db_url = settings.database_url
    if not db_url:
        return {}
    try:
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # type: ignore[import]

        # Rewrite the async asyncpg URL to the sync psycopg2 URL.
        # e.g. postgresql+asyncpg://user:pass@host/db → postgresql+psycopg2://…
        sync_url = db_url.replace("+asyncpg", "+psycopg2")
        store = SQLAlchemyJobStore(url=sync_url, tablename="apscheduler_jobs")
        logger.debug("apscheduler_jobstore=sqlalchemy url_prefix=%s", sync_url.split("@")[-1])
        return {"default": store}
    except Exception as exc:
        logger.warning(
            "apscheduler_jobstore_unavailable reason=%s using=memory", exc
        )
        return {}


def build_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance with all registered jobs.

    The scheduler uses a persistent SQLAlchemy job store (PostgreSQL) when
    available so that missed firings are recovered after a restart.  Falls back
    to in-memory storage if the job store cannot be initialised.
    """
    sched = AsyncIOScheduler(timezone="UTC", jobstores=_build_job_stores())

    # Nova Radiowave diary — 16:00 UTC daily (02:00 AEST)
    sched.add_job(
        job_collect_nova_diary,
        CronTrigger(hour=16, minute=0, timezone="UTC"),
        id="nova_daily_diary",
        name="Nova 96.9 Radiowave diary",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    # KIIS iHeart now-playing — every 5 minutes
    sched.add_job(
        job_collect_kiis_now_playing,
        IntervalTrigger(minutes=5),
        id="kiis_now_playing",
        name="KIIS-FM iHeart now-playing poll",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
        coalesce=True,
    )

    # Capital FM iHeart now-playing — every 5 minutes
    sched.add_job(
        job_collect_capital_now_playing,
        IntervalTrigger(minutes=5),
        id="capital_now_playing",
        name="Capital FM iHeart now-playing poll",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
        coalesce=True,
    )

    # Nightly reconciliation — 17:00 UTC daily (03:00 AEST)
    sched.add_job(
        job_nightly_reconciliation,
        CronTrigger(hour=17, minute=0, timezone="UTC"),
        id="nightly_reconciliation",
        name="Nightly deduplication & normalization reconciliation",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    # ── Email reports ─────────────────────────────────────────────────────────

    # Daily email — 22:00 UTC (08:00 AEST next day), covers yesterday's plays
    sched.add_job(
        job_send_daily_email,
        CronTrigger(hour=22, minute=0, timezone="UTC"),
        id="email_daily_report",
        name="Daily email report",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    # Weekly email — Monday 22:00 UTC (Tue 08:00 AEST), covers last Mon–Sun
    sched.add_job(
        job_send_weekly_email,
        CronTrigger(day_of_week="mon", hour=22, minute=0, timezone="UTC"),
        id="email_weekly_report",
        name="Weekly email report",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    # Monthly email — 1st of month 22:00 UTC (2nd 08:00 AEST), covers last month
    sched.add_job(
        job_send_monthly_email,
        CronTrigger(day=1, hour=22, minute=0, timezone="UTC"),
        id="email_monthly_report",
        name="Monthly email report",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    # ── Trend alerts ──────────────────────────────────────────────────────────

    # Trend alert sweep — 23:00 UTC daily (09:00 AEST), after the email report
    # run.  Fires song.trending, song.new_entry, and song.aria_match webhooks
    # for songs that crossed configured thresholds since yesterday.
    sched.add_job(
        job_check_trend_alerts,
        CronTrigger(hour=23, minute=0, timezone="UTC"),
        id="trend_alerts",
        name="Nightly trend alert sweep",
        replace_existing=True,
        misfire_grace_time=3600,
        max_instances=1,
        coalesce=True,
    )

    return sched
