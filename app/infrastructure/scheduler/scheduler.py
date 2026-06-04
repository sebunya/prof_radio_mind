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
from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector

logger = logging.getLogger(__name__)

# Deterministic IDs — must match app.application.seeder._NS derivation exactly.
_NS = uuid.NAMESPACE_DNS
_NOVA_STATION_ID = uuid.uuid5(_NS, "station.NOVA969")
_NOVA_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radiowave")
_KIIS_STATION_ID = uuid.uuid5(_NS, "station.KIISFM")
_KIIS_SOURCE_ID = uuid.uuid5(_NS, "source.KIISFM.iheart")
_CAPITAL_STATION_ID = uuid.uuid5(_NS, "station.CAPITALFM")
_CAPITAL_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.online_radio_box")

_scheduler: AsyncIOScheduler | None = None
_CAPITAL_FAILURES = 0
_FAILURE_THRESHOLD = 5


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

                # Skip if this now-playing event is a duplicate of a recent save.
                # Use a 1 800-second (30-minute) window — 2× the Capital FM poll
                # interval — so a song still playing on consecutive polls is stored
                # once, while a legitimate replay hours later is captured.
                if play_event.fingerprint and await play_repo.exists_by_fingerprint(
                    play_event.station_id,
                    play_event.fingerprint,
                    within_seconds=1800,
                ):
                    logger.debug(
                        "persist_result_skip_duplicate station_id=%s fingerprint=%s",
                        play_event.station_id,
                        play_event.fingerprint,
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
    await _persist_result(result)


async def job_collect_capital_now_playing() -> None:
    """Poll Capital FM Online Radio Box page (runs every 15 minutes)."""
    global _CAPITAL_FAILURES

    collector = OnlineRadioBoxCollector(
        source_id=_CAPITAL_SOURCE_ID,
        station_id=_CAPITAL_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )

    try:
        result = await collector.run()
        status_val = result.collector_run.status

        # MONITOR Log for tracking runs
        logger.info(
            "[MONITOR] capital_now_playing status=%s plays=%d no_tracks=%d",
            status_val.value,
            len(result.play_events),
            len(result.no_track_events),
        )

        from app.domain.entities.collector_run import CollectorStatus
        if status_val == CollectorStatus.FAILED:
            _CAPITAL_FAILURES += 1
            logger.warning(
                "[MONITOR] capital_now_playing_failed consecutive_failures=%d",
                _CAPITAL_FAILURES,
            )
        else:
            _CAPITAL_FAILURES = 0  # reset consecutive failure count

        await _persist_result(result)

    except Exception as exc:
        _CAPITAL_FAILURES += 1
        logger.error(
            "[MONITOR] capital_now_playing_exception error=%s consecutive_failures=%d",
            exc,
            _CAPITAL_FAILURES,
        )

    if _CAPITAL_FAILURES >= _FAILURE_THRESHOLD:
        logger.critical(
            "[MONITOR] capital_now_playing_paused reason=threshold_exceeded threshold=%d",
            _FAILURE_THRESHOLD,
        )
        global _scheduler
        if _scheduler:
            try:
                _scheduler.pause_job("capital_now_playing")
                logger.critical(
                    "[MONITOR] capital_now_playing_paused_success "
                    "job_id=capital_now_playing"
                )
            except Exception as e:
                logger.error("Failed to pause scheduler job: %s", e)


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


async def job_spotify_metadata_enrichment() -> None:
    """Scheduled background job to enrich pending catalog songs with Spotify metadata."""
    from app.application.spotify.enricher import enrich_songs_batch
    from app.infrastructure.database.session import _get_factory as _factory

    try:
        async with _factory()() as session:
            count = await enrich_songs_batch(session, batch_size=20)
            logger.info("spotify_metadata_enrichment_run completed enriched=%d", count)
    except Exception as exc:
        logger.error("spotify_metadata_enrichment_run_failed error=%s", exc)


def build_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance with all registered jobs."""
    global _scheduler
    sched = AsyncIOScheduler(timezone="UTC")
    _scheduler = sched

    # Nova Radiowave diary — 16:00 UTC daily (02:00 AEST)
    if settings.enable_nova_collector:
        sched.add_job(
            job_collect_nova_diary,
            CronTrigger(hour=16, minute=0, timezone="UTC"),
            id="nova_daily_diary",
            name="Nova 96.9 Radiowave diary",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduler registered job: Nova 96.9 Radiowave diary")
    else:
        logger.info("Scheduler skipped job: Nova 96.9 Radiowave diary (disabled)")

    # KIIS iHeart now-playing — every 5 minutes
    if settings.enable_kiis_collector:
        sched.add_job(
            job_collect_kiis_now_playing,
            IntervalTrigger(minutes=5),
            id="kiis_now_playing",
            name="KIIS-FM iHeart now-playing poll",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Scheduler registered job: KIIS-FM iHeart now-playing poll")
    else:
        logger.info("Scheduler skipped job: KIIS-FM iHeart now-playing poll (disabled)")

    # Capital FM Online Radio Box now-playing — every 15 minutes (low frequency)
    if settings.enable_capital_collector:
        sched.add_job(
            job_collect_capital_now_playing,
            IntervalTrigger(minutes=15),
            id="capital_now_playing",
            name="Capital FM Online Radio Box now-playing poll",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Scheduler registered job: Capital FM Online Radio Box now-playing poll")
    else:
        logger.info(
            "Scheduler skipped job: Capital FM Online Radio Box "
            "now-playing poll (disabled)"
        )

    # Nightly reconciliation — 17:00 UTC daily (03:00 AEST)
    if settings.enable_nightly_reconciliation:
        sched.add_job(
            job_nightly_reconciliation,
            CronTrigger(hour=17, minute=0, timezone="UTC"),
            id="nightly_reconciliation",
            name="Nightly deduplication & normalization reconciliation",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduler registered job: Nightly reconciliation")
    else:
        logger.info("Scheduler skipped job: Nightly reconciliation (disabled)")

    # Spotify Metadata Enrichment Job — runs hourly
    if settings.spotify_metadata_enrichment_enabled:
        sched.add_job(
            job_spotify_metadata_enrichment,
            IntervalTrigger(hours=1),
            id="spotify_metadata_enrichment",
            name="Spotify catalog metadata enrichment job",
            replace_existing=True,
            misfire_grace_time=120,
        )
        logger.info("Scheduler registered job: Spotify catalog metadata enrichment")
    else:
        logger.info(
            "Scheduler skipped job: Spotify catalog metadata enrichment (disabled)"
        )

    return sched
