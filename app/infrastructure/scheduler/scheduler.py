"""APScheduler wiring — registers all background collection and reconciliation jobs."""

from __future__ import annotations

import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.settings import settings
from app.infrastructure.collectors.capital_ukradiolive import CapitalUKRadioLiveCollector
from app.infrastructure.collectors.kiis_iheart_web import KIISIHeartWebCollector
from app.infrastructure.collectors.kiis_radiowave import KIISRadiowaveCollector
from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector
from app.infrastructure.collectors.nova_radoxo import NovaRadoxoCollector
from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector
from app.infrastructure.collectors.radio_australia_org import RadioAustraliaOrgCollector

logger = logging.getLogger(__name__)

# Deterministic IDs — must match app.application.seeder._NS derivation exactly.
_NS = uuid.NAMESPACE_DNS
_NOVA_STATION_ID = uuid.uuid5(_NS, "station.NOVA969")
_NOVA_RADIOWAVE_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radiowave")
_NOVA_RADOXO_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radoxo")
_NOVA_RAO_SOURCE_ID = uuid.uuid5(_NS, "source.NOVA969.radio_australia_org")
_CAPITAL_STATION_ID = uuid.uuid5(_NS, "station.CAPITALFM")
_CAPITAL_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.online_radio_box")
_CAPITAL_UKRADIOLIVE_SOURCE_ID = uuid.uuid5(_NS, "source.CAPITALFM.ukradiolive")
_KIIS1027_STATION_ID = uuid.uuid5(_NS, "station.KIIS1027")
_KIIS1027_RADIOWAVE_SOURCE_ID = uuid.uuid5(_NS, "source.KIIS1027.radiowave")
_KIIS1027_IHEART_WEB_SOURCE_ID = uuid.uuid5(_NS, "source.KIIS1027.iheart_web")

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

                # Batch-collector dedup: source_event_id is stable across polls,
                # so skip if this exact play instance is already stored.
                if play_event.source_event_id and await play_repo.exists_by_source_event_id(
                    play_event.station_id,
                    play_event.source_event_id,
                ):
                    logger.debug(
                        "persist_result_skip_duplicate station_id=%s source_event_id=%s",
                        play_event.station_id,
                        play_event.source_event_id,
                    )
                    continue

                # Now-playing dedup: fingerprint within a 30-minute window catches
                # the same song appearing on successive 5-minute polls.
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


# ─── Nova 96.9 ───────────────────────────────────────────────────────────────


async def job_collect_nova_diary() -> None:
    """Collect Nova 96.9 Radiowave diary for the previous day (runs daily 16:00 UTC)."""
    collector = NovaRadiowaveCollector(
        source_id=_NOVA_RADIOWAVE_SOURCE_ID,
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


async def job_collect_nova_radoxo() -> None:
    """Collect Nova 96.9 radoxo.com full-day playlist (runs every 4 hours)."""
    collector = NovaRadoxoCollector(
        source_id=_NOVA_RADOXO_SOURCE_ID,
        station_id=_NOVA_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "nova_radoxo_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)


async def job_collect_nova_radio_australia() -> None:
    """Collect Nova 96.9 weekly chart from radio-australia.org (runs daily 08:00 UTC)."""
    collector = RadioAustraliaOrgCollector(
        source_id=_NOVA_RAO_SOURCE_ID,
        station_id=_NOVA_STATION_ID,
        url="https://www.radio-australia.org/nova-969",
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "nova_radio_australia_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)


# ─── Capital FM UK ────────────────────────────────────────────────────────────


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
            _CAPITAL_FAILURES = 0

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


async def job_collect_capital_ukradiolive() -> None:
    """Scrape Capital FM ukradiolive.com playlist (runs every 15 minutes)."""
    collector = CapitalUKRadioLiveCollector(
        source_id=_CAPITAL_UKRADIOLIVE_SOURCE_ID,
        station_id=_CAPITAL_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "capital_ukradiolive_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)


# ─── KIIS-FM 102.7 Los Angeles ────────────────────────────────────────────────


async def job_collect_kiis1027_radiowave() -> None:
    """Collect KIIS-FM 102.7 Radiowave Monitor diary for yesterday (runs daily 09:00 UTC)."""
    from datetime import UTC, datetime, timedelta

    diary_date = datetime.now(tz=UTC).date() - timedelta(days=1)
    collector = KIISRadiowaveCollector(
        source_id=_KIIS1027_RADIOWAVE_SOURCE_ID,
        station_id=_KIIS1027_STATION_ID,
        diary_date=diary_date,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "kiis1027_radiowave_collected date=%s status=%s plays=%d no_tracks=%d",
        diary_date,
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)


async def job_collect_kiis_iheart_web() -> None:
    """Scrape KIIS-FM 102.7 iHeart recently-played page (runs every 15 minutes)."""
    collector = KIISIHeartWebCollector(
        source_id=_KIIS1027_IHEART_WEB_SOURCE_ID,
        station_id=_KIIS1027_STATION_ID,
        storage_root=settings.raw_payload_storage_path,
    )
    result = await collector.run()
    logger.info(
        "kiis_iheart_web_collected status=%s plays=%d no_tracks=%d",
        result.collector_run.status.value,
        len(result.play_events),
        len(result.no_track_events),
    )
    await _persist_result(result)


# ─── Nightly automation ───────────────────────────────────────────────────────


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


async def job_generate_nightly_reports() -> None:
    """Build DailyReport records for all active stations (runs daily 18:00 UTC).

    Generates yesterday's ranking for every station that has play events,
    persisting or updating the daily_reports + report_versions rows.
    Stations with zero plays for the day are silently skipped.
    Runs after nightly reconciliation (17:00 UTC) so dedup is current.
    """
    from datetime import UTC, datetime, timedelta

    from app.application.ranking.engine import build_snapshot
    from app.application.reports.confidence import SourceCoverage, compute_confidence
    from app.infrastructure.database.repositories.daily_report_repo import (
        SQLDailyReportRepository,
    )
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository
    from app.infrastructure.database.session import _get_factory as _factory

    report_date = (datetime.now(tz=UTC).date() - timedelta(days=1))
    from_dt = datetime(report_date.year, report_date.month, report_date.day, tzinfo=UTC)
    to_dt = from_dt + timedelta(days=1)
    generated = 0
    skipped = 0

    try:
        async with _factory()() as session:
            stations = await SQLStationRepository(session).list_active()
    except Exception as exc:
        logger.error("nightly_reports_station_load_failed error=%s", exc)
        return

    for station in stations:
        try:
            async with _factory()() as session:
                events = await SQLPlayEventRepository(session).list_for_station(
                    station.id, from_dt, to_dt
                )

            if not events:
                skipped += 1
                continue

            plays = [(e.raw_artist, e.raw_title) for e in events]
            snapshot = build_snapshot(plays, str(station.id), str(report_date), top_n=40)

            cov = SourceCoverage(total_plays=len(events))
            for ev in events:
                attr = getattr(ev, "attribution", None) or ""
                if attr == "radiowave":
                    cov.radiowave_plays += 1
                elif attr == "iheart":
                    cov.iheart_plays += 1
                elif attr == "manual_csv":
                    cov.manual_csv_plays += 1
                else:
                    cov.radiowave_plays += 1

            confidence_score, confidence_level = compute_confidence(cov)
            snapshot_rows = [
                {
                    "position": e.position,
                    "artist": e.song_key.artist,
                    "title": e.song_key.title,
                    "play_count": e.play_count,
                }
                for e in snapshot.entries
            ]

            async with _factory()() as session:
                _, version = await SQLDailyReportRepository(session).upsert(
                    station_id=station.id,
                    report_date=report_date,
                    confidence_level=confidence_level.value,
                    confidence_score=float(confidence_score),
                    total_plays=snapshot.total_plays,
                    unique_songs=len(snapshot.entries),
                    source_coverage=cov.to_dict(),
                    snapshot_rows=snapshot_rows,
                )
                await session.commit()

            logger.info(
                "nightly_report_generated station=%s date=%s plays=%d entries=%d "
                "confidence=%s version=%d",
                station.call_sign, report_date, snapshot.total_plays,
                len(snapshot.entries), confidence_level.value, version,
            )
            generated += 1

        except Exception as exc:
            logger.error(
                "nightly_report_station_failed station=%s date=%s error=%s",
                getattr(station, "call_sign", station.id), report_date, exc,
            )

    logger.info(
        "nightly_reports_complete date=%s generated=%d skipped_no_plays=%d",
        report_date, generated, skipped,
    )


# ─── Scheduler builder ────────────────────────────────────────────────────────


def build_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance with all registered jobs."""
    global _scheduler
    sched = AsyncIOScheduler(timezone="UTC")
    _scheduler = sched

    # Nova 96.9 — Radiowave diary (primary): 16:00 UTC daily (02:00 AEST)
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

    # Nova 96.9 — radoxo.com playlist (secondary): every 4 hours
    if settings.enable_nova_radoxo_collector:
        sched.add_job(
            job_collect_nova_radoxo,
            IntervalTrigger(hours=4),
            id="nova_radoxo_playlist",
            name="Nova 96.9 radoxo.com playlist",
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info("Scheduler registered job: Nova 96.9 radoxo.com playlist")
    else:
        logger.info("Scheduler skipped job: Nova 96.9 radoxo playlist (disabled)")

    # Nova 96.9 — radio-australia.org chart (tertiary): 08:00 UTC daily
    if settings.enable_nova_radio_australia_collector:
        sched.add_job(
            job_collect_nova_radio_australia,
            CronTrigger(hour=8, minute=0, timezone="UTC"),
            id="nova_radio_australia_chart",
            name="Nova 96.9 radio-australia.org weekly chart",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduler registered job: Nova 96.9 radio-australia.org chart")
    else:
        logger.info("Scheduler skipped job: Nova 96.9 radio-australia chart (disabled)")

    # Capital FM — Online Radio Box (primary): every 15 minutes
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
        logger.info("Scheduler skipped job: Capital FM Online Radio Box poll (disabled)")

    # Capital FM — ukradiolive.com (secondary): every 15 minutes
    if settings.enable_capital_ukradiolive_collector:
        sched.add_job(
            job_collect_capital_ukradiolive,
            IntervalTrigger(minutes=15),
            id="capital_ukradiolive_playlist",
            name="Capital FM ukradiolive.com playlist",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Scheduler registered job: Capital FM ukradiolive.com playlist")
    else:
        logger.info("Scheduler skipped job: Capital FM ukradiolive playlist (disabled)")

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

    # Nightly report generation — 18:00 UTC daily (after reconciliation at 17:00)
    if settings.enable_nightly_report_generation:
        sched.add_job(
            job_generate_nightly_reports,
            CronTrigger(hour=18, minute=0, timezone="UTC"),
            id="nightly_report_generation",
            name="Nightly daily-report generation (all stations)",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduler registered job: Nightly report generation")
    else:
        logger.info("Scheduler skipped job: Nightly report generation (disabled)")

    # KIIS-FM 102.7 — iHeart web recently-played (primary): every 15 minutes
    if settings.enable_kiis_iheart_web_collector:
        sched.add_job(
            job_collect_kiis_iheart_web,
            IntervalTrigger(minutes=15),
            id="kiis_iheart_web_playlist",
            name="KIIS-FM 102.7 iHeart recently-played",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Scheduler registered job: KIIS-FM 102.7 iHeart recently-played")
    else:
        logger.info("Scheduler skipped job: KIIS-FM 102.7 iHeart web (disabled)")

    # KIIS-FM 102.7 — Radiowave diary (secondary): 09:00 UTC daily (01:00 AM Pacific)
    if settings.enable_kiis_radiowave_collector:
        sched.add_job(
            job_collect_kiis1027_radiowave,
            CronTrigger(hour=9, minute=0, timezone="UTC"),
            id="kiis1027_radiowave_diary",
            name="KIIS-FM 102.7 Radiowave diary",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduler registered job: KIIS-FM 102.7 Radiowave diary")
    else:
        logger.info("Scheduler skipped job: KIIS-FM 102.7 Radiowave diary (disabled)")

    return sched
