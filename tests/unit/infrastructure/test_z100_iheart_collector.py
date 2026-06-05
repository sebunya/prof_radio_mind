"""Tests for Z100 (WHTZ) iHeart now-playing and history collectors.

No live network calls. Uses saved JSON fixtures. Tests confirm Z100-specific
station ID (614), URL construction, and end-to-end parse paths via the shared
IHeartNowPlayingCollector and IHeartRecentlyPlayedCollector generic classes.

VAL-Z100-001: stream ID 614 is UNVALIDATED; confirm via DevTools on
https://z100.iheart.com/Music/ before enabling the collector.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector
from app.infrastructure.collectors.iheart_recently_played import IHeartRecentlyPlayedCollector

_FIXTURE_200 = Path(__file__).parent.parent.parent / "fixtures/json/iheart_z100_200.json"
_FIXTURE_RECENT = (
    Path(__file__).parent.parent.parent / "fixtures/json/iheart_z100_recently_played.json"
)


# ── Now-playing collector ─────────────────────────────────────────────────────

def test_now_playing_url_contains_614_and_current_track() -> None:
    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    url = collector._build_url()
    assert "614" in url
    assert url.endswith("/currentTrack")
    assert "api.iheart.com" in url


def test_now_playing_custom_station_id() -> None:
    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="9999",
    )
    assert "9999/currentTrack" in collector._build_url()


def test_now_playing_parse_fixture() -> None:
    raw = _FIXTURE_200.read_bytes()
    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, no_tracks = collector.parse(raw, 200, uuid.uuid4())
    assert len(plays) == 1
    assert no_tracks == []
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].raw_title == "Cruel Summer"
    assert plays[0].attribution == "iheart"
    assert plays[0].source_event_id == "iheart-614-20260524-00601"


def test_now_playing_204_produces_no_track_event() -> None:
    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_now_playing_timestamp_is_utc_aware() -> None:
    raw = _FIXTURE_200.read_bytes()
    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    assert plays[0].played_at.tzinfo is not None
    assert int(plays[0].played_at.timestamp()) == 1748044860


@pytest.mark.anyio
async def test_now_playing_fetch_and_parse_mocked() -> None:
    raw = _FIXTURE_200.read_bytes()
    mock_response = MagicMock()
    mock_response.content = raw
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = IHeartNowPlayingCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, _ = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 1
    assert plays[0].raw_artist == "Taylor Swift"


# ── History collector ─────────────────────────────────────────────────────────

def test_history_url_contains_614_and_recently_played() -> None:
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    url = collector._build_url()
    assert "614" in url
    assert url.endswith("/recentlyPlayed")
    assert "api.iheart.com" in url


def test_history_custom_station_id() -> None:
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="9999",
    )
    assert "9999/recentlyPlayed" in collector._build_url()


def test_history_parse_five_tracks() -> None:
    raw = _FIXTURE_RECENT.read_bytes()
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, no_tracks = collector.parse(raw, 200, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []


def test_history_first_track_is_cruel_summer() -> None:
    raw = _FIXTURE_RECENT.read_bytes()
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].raw_title == "Cruel Summer"
    assert plays[0].attribution == "iheart_recently_played"


def test_history_204_produces_no_track_event() -> None:
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_history_all_source_event_ids_use_614() -> None:
    raw = _FIXTURE_RECENT.read_bytes()
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    for play in plays:
        assert play.source_event_id is not None
        assert "614" in play.source_event_id


@pytest.mark.anyio
async def test_history_fetch_and_parse_mocked() -> None:
    raw = _FIXTURE_RECENT.read_bytes()
    mock_response = MagicMock()
    mock_response.content = raw
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, _ = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []
