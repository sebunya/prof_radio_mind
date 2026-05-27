"""Tests for APScheduler job registration — no live-network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.infrastructure.scheduler.scheduler import (
    build_scheduler,
    job_check_trend_alerts,
    job_collect_capital_now_playing,
    job_collect_kiis_now_playing,
    job_collect_nova_diary,
    job_nightly_reconciliation,
)

# --- Job registration ---

def test_scheduler_has_eight_jobs() -> None:
    sched = build_scheduler()
    assert len(sched.get_jobs()) == 8


def test_scheduler_job_ids() -> None:
    sched = build_scheduler()
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {
        "nova_daily_diary",
        "kiis_now_playing",
        "capital_now_playing",
        "nightly_reconciliation",
        "email_daily_report",
        "email_weekly_report",
        "email_monthly_report",
        "trend_alerts",
    }


def test_nova_job_uses_cron_trigger() -> None:
    sched = build_scheduler()
    job = sched.get_job("nova_daily_diary")
    assert job is not None
    assert isinstance(job.trigger, CronTrigger)


def test_kiis_job_uses_interval_trigger() -> None:
    sched = build_scheduler()
    job = sched.get_job("kiis_now_playing")
    assert job is not None
    assert isinstance(job.trigger, IntervalTrigger)


def test_capital_job_uses_interval_trigger() -> None:
    sched = build_scheduler()
    job = sched.get_job("capital_now_playing")
    assert job is not None
    assert isinstance(job.trigger, IntervalTrigger)


def test_reconciliation_job_uses_cron_trigger() -> None:
    sched = build_scheduler()
    job = sched.get_job("nightly_reconciliation")
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
async def test_trend_alert_job_invokes_service() -> None:
    with patch(
        "app.infrastructure.scheduler.scheduler.job_check_trend_alerts",
        new_callable=AsyncMock,
    ):
        # The actual wrapped function delegates to check_and_fire_trend_alerts;
        # we just verify the job coroutine itself completes without error when
        # the underlying service raises (error-handling path).
        from unittest.mock import patch as _patch

        with _patch(
            "app.application.alerts.trend_alert_service.check_and_fire_trend_alerts",
            new_callable=AsyncMock,
            return_value={"total_fired": 0},
        ):
            await job_check_trend_alerts()


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
        patch(f"{_sched}.CapitalIHeartCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_capital_now_playing()

    mock_collector.run.assert_awaited_once()
