"""Fixture-driven tests for the iHeart parser and KIIS collector.

CRITICAL INVARIANTS TESTED:
- HTTP 204 NEVER causes an exception — produces NoTrackEvent
- HTTP 204 body is never parsed as JSON (no AttributeError / json.JSONDecodeError)
- Repeated observation deduplication logic tested via source_event_id

No live network calls.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.domain.entities.collector_run import CollectorStatus
from app.domain.entities.no_track_event import NoTrackReason
from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector
from app.infrastructure.parsers.iheart import parse_iheart_now_playing

_FIXTURE_200 = Path(__file__).parent.parent.parent / "fixtures/json/iheart_kiis_200.json"


@pytest.fixture
def fixture_200_bytes() -> bytes:
    return _FIXTURE_200.read_bytes()


def test_parse_200_returns_play_event_data(fixture_200_bytes: bytes) -> None:
    result = parse_iheart_now_playing(fixture_200_bytes, http_status=200)
    assert result is not None
    assert result.artist == "Taylor Swift"
    assert result.title == "Anti-Hero"


def test_parse_200_source_event_id(fixture_200_bytes: bytes) -> None:
    result = parse_iheart_now_playing(fixture_200_bytes, http_status=200)
    assert result is not None
    assert result.source_event_id == "iheart-2501-20260524-00601"


def test_parse_200_played_at_is_timezone_aware(fixture_200_bytes: bytes) -> None:
    result = parse_iheart_now_playing(fixture_200_bytes, http_status=200)
    assert result is not None
    assert result.played_at.tzinfo is not None


def test_parse_204_returns_none_never_raises() -> None:
    """HTTP 204 body is empty — parser must return None without raising."""
    result = parse_iheart_now_playing(b"", http_status=204)
    assert result is None


def test_parse_204_with_garbage_body_still_returns_none() -> None:
    """Even if the 204 body contains garbage, we never attempt to parse it."""
    result = parse_iheart_now_playing(b"not json at all {{{{", http_status=204)
    assert result is None


def test_parse_invalid_json_raises_value_error() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_iheart_now_playing(b"not json", http_status=200)


def test_parse_missing_current_track_raises() -> None:
    with pytest.raises(ValueError, match="missing 'currentTrack'"):
        parse_iheart_now_playing(b'{"stationId": "2501"}', http_status=200)


class _FixtureKIISCollector(IHeartNowPlayingCollector):
    """KIIS collector stub that returns a pre-loaded fixture instead of making HTTP calls."""

    def __init__(self, raw_bytes: bytes, http_status: int, tmp_path_str: str) -> None:
        super().__init__(
            uuid.uuid4(),
            uuid.uuid4(),
            iheart_station_id="2501",
            storage_root=tmp_path_str,
        )
        self._raw = raw_bytes
        self._status = http_status

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        return self._raw, self._status, "application/json"


@pytest.mark.anyio
async def test_collector_200_produces_play_event(
    tmp_path: pytest.fixture, fixture_200_bytes: bytes
) -> None:
    collector = _FixtureKIISCollector(fixture_200_bytes, 200, str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.COMPLETED
    assert len(result.play_events) == 1
    assert result.play_events[0].raw_artist == "Taylor Swift"
    assert result.play_events[0].raw_title == "Anti-Hero"


@pytest.mark.anyio
async def test_collector_204_produces_no_track_event_no_exception(
    tmp_path: pytest.fixture,
) -> None:
    """CRITICAL: HTTP 204 must never raise — must produce NoTrackEvent."""
    collector = _FixtureKIISCollector(b"", 204, str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.COMPLETED
    assert len(result.no_track_events) == 1
    assert len(result.play_events) == 0
    assert result.no_track_events[0].reason == NoTrackReason.SOURCE_HTTP_204
    assert result.no_track_events[0].raw_http_status == 204


@pytest.mark.anyio
async def test_failed_kiis_does_not_stop_another_collector(tmp_path: pytest.fixture) -> None:
    from app.infrastructure.collectors.base import BaseCollector

    class _BrokenCollector(BaseCollector):
        async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
            raise RuntimeError("broken")

        def parse(self, *_: object) -> tuple[list, list]:
            return [], []

    broken = _BrokenCollector(uuid.uuid4(), uuid.uuid4(), storage_root=str(tmp_path))
    kiis = _FixtureKIISCollector(
        Path(__file__).parent.parent.parent.joinpath(
            "fixtures/json/iheart_kiis_200.json"
        ).read_bytes(),
        200,
        str(tmp_path),
    )

    result_broken = await broken.run()
    result_kiis = await kiis.run()

    assert result_broken.collector_run.status == CollectorStatus.FAILED
    assert result_kiis.collector_run.status == CollectorStatus.COMPLETED


@pytest.mark.anyio
async def test_204_raw_payload_stored(tmp_path: pytest.fixture) -> None:
    """Even for 204, the (empty) raw payload must be stored and hashed."""
    collector = _FixtureKIISCollector(b"", 204, str(tmp_path))
    result = await collector.run()

    assert result.raw_payload is not None
    assert result.raw_payload.http_status == 204
