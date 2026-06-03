"""Tests for duplicate-prevention in scheduler._persist_result."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.entities.collector_run import CollectorRun
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import CollectorResult
from app.infrastructure.scheduler.scheduler import _persist_result

# All imports inside _persist_result are deferred; patch at source module path.
_RUN_REPO = "app.infrastructure.database.repositories.collector_run_repo.SQLCollectorRunRepository"
_PLAY_REPO = "app.infrastructure.database.repositories.play_event_repo.SQLPlayEventRepository"
_PAYLOAD_REPO = "app.infrastructure.database.repositories.raw_payload_repo.SQLRawPayloadRepository"
_NOTRACK_REPO = (
    "app.infrastructure.database.repositories"
    ".no_track_event_repo.SQLNoTrackEventRepository"
)
_SESSION = "app.infrastructure.database.session._get_factory"


def _make_play_event(fingerprint: str | None = "fp_test") -> PlayEvent:
    return PlayEvent(
        id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        played_at=datetime.now(UTC),
        raw_artist="Test Artist",
        raw_title="Test Title",
        fingerprint=fingerprint,
    )


def _make_result(play_events: list[PlayEvent]) -> CollectorResult:
    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    return CollectorResult(collector_run=run, play_events=play_events)


def _mock_ctx() -> MagicMock:
    session = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.anyio
async def test_new_event_is_saved() -> None:
    """A play event with no matching fingerprint is persisted."""
    event = _make_play_event()
    result = _make_result([event])

    mock_play_repo = AsyncMock()
    mock_play_repo.exists_by_fingerprint = AsyncMock(return_value=False)
    mock_play_repo.save = AsyncMock()

    with (
        patch(_SESSION, return_value=lambda: _mock_ctx()),
        patch(_RUN_REPO, return_value=AsyncMock()),
        patch(_PLAY_REPO, return_value=mock_play_repo),
        patch(_PAYLOAD_REPO, return_value=AsyncMock()),
        patch(_NOTRACK_REPO, return_value=AsyncMock()),
    ):
        await _persist_result(result)

    mock_play_repo.save.assert_awaited_once_with(event)


@pytest.mark.anyio
async def test_duplicate_fingerprint_is_skipped() -> None:
    """A play event whose fingerprint already exists within the window is not saved."""
    event = _make_play_event(fingerprint="known_fp")
    result = _make_result([event])

    mock_play_repo = AsyncMock()
    mock_play_repo.exists_by_fingerprint = AsyncMock(return_value=True)
    mock_play_repo.save = AsyncMock()

    with (
        patch(_SESSION, return_value=lambda: _mock_ctx()),
        patch(_RUN_REPO, return_value=AsyncMock()),
        patch(_PLAY_REPO, return_value=mock_play_repo),
        patch(_PAYLOAD_REPO, return_value=AsyncMock()),
        patch(_NOTRACK_REPO, return_value=AsyncMock()),
    ):
        await _persist_result(result)

    mock_play_repo.save.assert_not_awaited()


@pytest.mark.anyio
async def test_event_without_initial_fingerprint_gets_computed_then_checked() -> None:
    """When fingerprint is absent it is computed from artist+title before the dedup check."""
    event = _make_play_event(fingerprint=None)
    result = _make_result([event])

    mock_play_repo = AsyncMock()
    mock_play_repo.exists_by_fingerprint = AsyncMock(return_value=False)
    mock_play_repo.save = AsyncMock()

    with (
        patch(_SESSION, return_value=lambda: _mock_ctx()),
        patch(_RUN_REPO, return_value=AsyncMock()),
        patch(_PLAY_REPO, return_value=mock_play_repo),
        patch(_PAYLOAD_REPO, return_value=AsyncMock()),
        patch(_NOTRACK_REPO, return_value=AsyncMock()),
    ):
        await _persist_result(result)

    # fingerprint was computed → dedup check must have run
    mock_play_repo.exists_by_fingerprint.assert_awaited_once()
    # and since no duplicate found, event was saved
    mock_play_repo.save.assert_awaited_once_with(event)


@pytest.mark.anyio
async def test_dedup_check_uses_1800_second_window() -> None:
    """Dedup uses a 30-minute window — 2× Capital FM's 15-minute poll interval."""
    event = _make_play_event(fingerprint="fp_window_check")
    result = _make_result([event])

    mock_play_repo = AsyncMock()
    mock_play_repo.exists_by_fingerprint = AsyncMock(return_value=False)
    mock_play_repo.save = AsyncMock()

    with (
        patch(_SESSION, return_value=lambda: _mock_ctx()),
        patch(_RUN_REPO, return_value=AsyncMock()),
        patch(_PLAY_REPO, return_value=mock_play_repo),
        patch(_PAYLOAD_REPO, return_value=AsyncMock()),
        patch(_NOTRACK_REPO, return_value=AsyncMock()),
    ):
        await _persist_result(result)

    call_kwargs = mock_play_repo.exists_by_fingerprint.await_args
    assert call_kwargs is not None
    assert call_kwargs.kwargs.get("within_seconds") == 1800
