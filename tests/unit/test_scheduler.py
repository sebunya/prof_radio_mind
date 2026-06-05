"""Tests for APScheduler job registration — no live-network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.infrastructure.scheduler.scheduler import (
    build_scheduler,
    job_collect_bbc_radio1,
    job_collect_capital_now_playing,
    job_collect_heart_fm,
    job_collect_iheart_recently_played,
    job_collect_kiis1027_radiowave,
    job_collect_kiis_now_playing,
    job_collect_kiis_top_songs,
    job_collect_nova_diary,
    job_collect_wksc_now_playing,
    job_collect_z100_now_playing,
    job_generate_nightly_reports,
    job_nightly_reconciliation,
)

# --- Job registration ---

def test_scheduler_default_no_jobs() -> None:
    from app.core.settings import settings
    with (
        patch.object(settings, "enable_nova_collector", False),
        patch.object(settings, "enable_kiis_collector", False),
        patch.object(settings, "enable_capital_collector", False),
        patch.object(settings, "enable_nightly_reconciliation", False),
        patch.object(settings, "enable_bbc_radio1_collector", False),
        patch.object(settings, "enable_heart_collector", False),
        patch.object(settings, "enable_z100_collector", False),
        patch.object(settings, "enable_wksc_collector", False),
        patch.object(settings, "enable_iheart_top_songs", False),
        patch.object(settings, "enable_kiis_radiowave_collector", False),
        patch.object(settings, "enable_iheart_recently_played", False),
        patch.object(settings, "enable_nightly_report_generation", False),
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 0


def test_scheduler_all_enabled_has_twelve_jobs() -> None:
    from app.core.settings import settings
    with (
        patch.object(settings, "enable_nova_collector", True),
        patch.object(settings, "enable_kiis_collector", True),
        patch.object(settings, "enable_capital_collector", True),
        patch.object(settings, "enable_nightly_reconciliation", True),
        patch.object(settings, "enable_bbc_radio1_collector", True),
        patch.object(settings, "enable_heart_collector", True),
        patch.object(settings, "enable_z100_collector", True),
        patch.object(settings, "enable_wksc_collector", True),
        patch.object(settings, "enable_iheart_top_songs", True),
        patch.object(settings, "enable_kiis_radiowave_collector", True),
        patch.object(settings, "enable_iheart_recently_played", True),
        patch.object(settings, "enable_nightly_report_generation", True),
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 12
        ids = {j.id for j in sched.get_jobs()}
        assert ids == {
            "nova_daily_diary",
            "kiis_now_playing",
            "capital_now_playing",
            "nightly_reconciliation",
            "nightly_report_generation",
            "bbc_radio1_now_playing",
            "heart_fm_last_played",
            "z100_now_playing",
            "wksc_now_playing",
            "kiis_top_songs_daily",
            "kiis1027_radiowave_diary",
            "iheart_recently_played_hourly",
        }


def test_nova_job_uses_cron_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_nova_collector", True):
        sched = build_scheduler()
        job = sched.get_job("nova_daily_diary")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)


def test_kiis_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_kiis_collector", True):
        sched = build_scheduler()
        job = sched.get_job("kiis_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_capital_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_capital_collector", True):
        sched = build_scheduler()
        job = sched.get_job("capital_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_reconciliation_job_uses_cron_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_nightly_reconciliation", True):
        sched = build_scheduler()
        job = sched.get_job("nightly_reconciliation")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)


def test_bbc_radio1_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_bbc_radio1_collector", True):
        sched = build_scheduler()
        job = sched.get_job("bbc_radio1_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_heart_fm_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_heart_collector", True):
        sched = build_scheduler()
        job = sched.get_job("heart_fm_last_played")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_z100_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_z100_collector", True):
        sched = build_scheduler()
        job = sched.get_job("z100_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_wksc_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_wksc_collector", True):
        sched = build_scheduler()
        job = sched.get_job("wksc_now_playing")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


def test_kiis_top_songs_job_uses_cron_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_iheart_top_songs", True):
        sched = build_scheduler()
        job = sched.get_job("kiis_top_songs_daily")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)


def test_build_scheduler_returns_asyncio_scheduler() -> None:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    sched = build_scheduler()
    assert isinstance(sched, AsyncIOScheduler)


# --- Job function unit tests (no live network) ---

@pytest.mark.anyio
async def test_nightly_reconciliation_is_no_op() -> None:
    # Must complete without raising
    await job_nightly_reconciliation()


@pytest.mark.anyio
async def test_nova_diary_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.NovaRadiowaveCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_nova_diary()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_kiis_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.KIISIHeartCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_kiis_now_playing()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_capital_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.OnlineRadioBoxCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_capital_now_playing()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_bbc_radio1_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.BBCRadio1Collector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_bbc_radio1()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_heart_fm_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.HeartRadioCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_heart_fm()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_z100_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.IHeartNowPlayingCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_z100_now_playing()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_wksc_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.IHeartNowPlayingCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_wksc_now_playing()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_kiis_top_songs_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.IHeartTopSongsCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_kiis_top_songs()

    mock_collector.run.assert_awaited_once()


def test_kiis1027_radiowave_job_uses_cron_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_kiis_radiowave_collector", True):
        sched = build_scheduler()
        job = sched.get_job("kiis1027_radiowave_diary")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)


@pytest.mark.anyio
async def test_kiis1027_radiowave_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.KIISRadiowaveCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_kiis1027_radiowave()

    mock_collector.run.assert_awaited_once()


def test_iheart_recently_played_job_uses_interval_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_iheart_recently_played", True):
        sched = build_scheduler()
        job = sched.get_job("iheart_recently_played_hourly")
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)


@pytest.mark.anyio
async def test_iheart_recently_played_job_invokes_collector() -> None:
    import uuid

    from app.domain.entities.collector_run import CollectorRun
    from app.infrastructure.collectors.base import CollectorResult

    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    real_result = CollectorResult(collector_run=run, play_events=[], no_track_events=[])

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=real_result)

    _sched = "app.infrastructure.scheduler.scheduler"
    with (
        patch(f"{_sched}.IHeartRecentlyPlayedCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_iheart_recently_played()

    # Three stations are polled per invocation
    assert mock_collector.run.await_count == 3


def test_nightly_report_generation_job_uses_cron_trigger() -> None:
    from app.core.settings import settings
    with patch.object(settings, "enable_nightly_report_generation", True):
        sched = build_scheduler()
        job = sched.get_job("nightly_report_generation")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)


@pytest.mark.anyio
async def test_nightly_report_job_is_no_op_without_db() -> None:
    # Must complete without raising even when DB is unavailable
    await job_generate_nightly_reports()
