"""Tests for APScheduler job registration — no live-network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.infrastructure.scheduler.scheduler import (
    build_scheduler,
    job_collect_capital_now_playing,
    job_collect_kiis_now_playing,
    job_collect_nova_diary,
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
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 0


def test_scheduler_all_enabled_has_four_jobs() -> None:
    from app.core.settings import settings
    with (
        patch.object(settings, "enable_nova_collector", True),
        patch.object(settings, "enable_kiis_collector", True),
        patch.object(settings, "enable_capital_collector", True),
        patch.object(settings, "enable_nightly_reconciliation", True),
    ):
        sched = build_scheduler()
        assert len(sched.get_jobs()) == 4
        ids = {j.id for j in sched.get_jobs()}
        assert ids == {
            "nova_daily_diary",
            "kiis_now_playing",
            "capital_now_playing",
            "nightly_reconciliation",
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
        patch(f"{_sched}.CapitalIHeartCollector", return_value=mock_collector),
        patch(f"{_sched}._persist_result", new_callable=AsyncMock),
    ):
        await job_collect_capital_now_playing()

    mock_collector.run.assert_awaited_once()
