"""Tests for APScheduler job registration — no live-network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.infrastructure.scheduler.scheduler import (
    build_scheduler,
    job_collect_kiis_now_playing,
    job_collect_nova_diary,
    job_nightly_reconciliation,
)

# --- Job registration ---

def test_scheduler_has_three_jobs() -> None:
    sched = build_scheduler()
    assert len(sched.get_jobs()) == 3


def test_scheduler_job_ids() -> None:
    sched = build_scheduler()
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {"nova_daily_diary", "kiis_now_playing", "nightly_reconciliation"}


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
    mock_result = MagicMock()
    mock_result.collector_run.status.value = "completed"
    mock_result.play_events = []
    mock_result.no_track_events = []

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=mock_result)

    with patch(
        "app.infrastructure.scheduler.scheduler.NovaRadiowaveCollector",
        return_value=mock_collector,
    ):
        await job_collect_nova_diary()

    mock_collector.run.assert_awaited_once()


@pytest.mark.anyio
async def test_kiis_job_invokes_collector() -> None:
    mock_result = MagicMock()
    mock_result.collector_run.status.value = "completed"
    mock_result.play_events = []
    mock_result.no_track_events = []

    mock_collector = AsyncMock()
    mock_collector.run = AsyncMock(return_value=mock_result)

    with patch(
        "app.infrastructure.scheduler.scheduler.KIISIHeartCollector",
        return_value=mock_collector,
    ):
        await job_collect_kiis_now_playing()

    mock_collector.run.assert_awaited_once()
