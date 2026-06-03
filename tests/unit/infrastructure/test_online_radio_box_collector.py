"""Fixture-driven unit tests for the Online Radio Box collector and scheduler threshold logic.

No live network calls.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.entities.collector_run import CollectorStatus
from app.domain.entities.no_track_event import NoTrackReason
from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector
from app.infrastructure.scheduler import scheduler
from app.infrastructure.scheduler.scheduler import job_collect_capital_now_playing

_FIXTURE_VALID = (
    Path(__file__).parent.parent.parent
    / "fixtures/html/online_radio_box_capital_valid.html"
)


class _FixtureOnlineRadioBoxCollector(OnlineRadioBoxCollector):
    """Collector stub that returns fixed data instead of performing network operations."""

    def __init__(self, raw_bytes: bytes, http_status: int, tmp_path_str: str) -> None:
        super().__init__(
            uuid.uuid4(),
            uuid.uuid4(),
            storage_root=tmp_path_str,
        )
        self._raw = raw_bytes
        self._status = http_status

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        return self._raw, self._status, "text/html"


@pytest.mark.anyio
async def test_collector_successful_run(tmp_path: pytest.fixture) -> None:
    html_content = _FIXTURE_VALID.read_bytes()
    collector = _FixtureOnlineRadioBoxCollector(html_content, 200, str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.COMPLETED
    assert len(result.play_events) == 1
    assert result.play_events[0].raw_artist == "Taylor Swift"
    assert result.play_events[0].raw_title == "Elizabeth Taylor"
    assert result.raw_payload is not None
    assert result.raw_payload.http_status == 200


@pytest.mark.anyio
async def test_collector_204_produces_no_track_event(tmp_path: pytest.fixture) -> None:
    collector = _FixtureOnlineRadioBoxCollector(b"", 204, str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.COMPLETED
    assert len(result.play_events) == 0
    assert len(result.no_track_events) == 1
    assert result.no_track_events[0].reason == NoTrackReason.SOURCE_HTTP_204


@pytest.mark.anyio
async def test_collector_failed_fetch_graceful(tmp_path: pytest.fixture) -> None:
    class _BrokenCollector(OnlineRadioBoxCollector):
        async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
            raise RuntimeError("Network down")

    collector = _BrokenCollector(uuid.uuid4(), uuid.uuid4(), storage_root=str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.FAILED
    assert len(result.play_events) == 0


@pytest.mark.anyio
async def test_scheduler_failure_threshold_pausing() -> None:
    # Reset failure counter before test
    scheduler._CAPITAL_FAILURES = 0

    # Mock database persistence to avoid hitting DB
    with patch("app.infrastructure.scheduler.scheduler._persist_result", new_callable=AsyncMock):

        # Create a mock collector that fails
        class _BrokenCollector(OnlineRadioBoxCollector):
            async def run(self) -> any:
                # Mock a failed result
                run = MagicMock()
                run.status = CollectorStatus.FAILED
                run.id = uuid.uuid4()
                result = MagicMock()
                result.collector_run = run
                result.play_events = []
                result.no_track_events = []
                return result

        # Mock scheduler instance
        mock_sched = MagicMock()
        scheduler._scheduler = mock_sched

        # Patch OnlineRadioBoxCollector instantiated inside the job
        with patch(
            "app.infrastructure.scheduler.scheduler.OnlineRadioBoxCollector",
            return_value=_BrokenCollector(uuid.uuid4(), uuid.uuid4())
        ):
            # Run job 4 times (under threshold)
            for _ in range(4):
                await job_collect_capital_now_playing()
                assert scheduler._CAPITAL_FAILURES < 5
                mock_sched.pause_job.assert_not_called()

            # Run 5th time (hits threshold)
            await job_collect_capital_now_playing()
            assert scheduler._CAPITAL_FAILURES == 5
            mock_sched.pause_job.assert_called_once_with("capital_now_playing")


@pytest.mark.anyio
async def test_scheduler_resets_failures_on_success() -> None:
    scheduler._CAPITAL_FAILURES = 3

    # Create a mock collector that succeeds
    class _SuccessCollector(OnlineRadioBoxCollector):
        async def run(self) -> any:
            run = MagicMock()
            run.status = CollectorStatus.COMPLETED
            result = MagicMock()
            result.collector_run = run
            result.play_events = [MagicMock()]
            result.no_track_events = []
            return result

    with patch("app.infrastructure.scheduler.scheduler._persist_result", new_callable=AsyncMock):
        with patch(
            "app.infrastructure.scheduler.scheduler.OnlineRadioBoxCollector",
            return_value=_SuccessCollector(uuid.uuid4(), uuid.uuid4())
        ):
            await job_collect_capital_now_playing()
            # Success resets consecutive failures to 0
            assert scheduler._CAPITAL_FAILURES == 0
