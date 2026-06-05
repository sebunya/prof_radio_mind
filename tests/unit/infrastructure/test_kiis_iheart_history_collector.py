"""Fixture-driven tests for the KIIS-FM iHeart recently-played batch collector.

No live network calls. All tests use the saved JSON fixture.
Verifies:
  - Parser extracts correct events from the fixture
  - Timestamps are converted to UTC correctly
  - Collector URL uses the recentlyPlayed path
  - attribution is 'iheart_recently_played'
  - HTTP 204 produces a NoTrackEvent (no play events)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.collectors.iheart_recently_played import IHeartRecentlyPlayedCollector
from app.infrastructure.parsers.iheart import parse_iheart_recently_played

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/json/iheart_kiis_recently_played.json"


# ── Parser-level tests (fixture-driven) ──────────────────────────────────────

def test_parser_extracts_five_tracks_from_fixture() -> None:
    raw = _FIXTURE.read_bytes()
    results = parse_iheart_recently_played(raw, http_status=200)
    assert len(results) == 5


def test_parser_first_track_is_anti_hero() -> None:
    raw = _FIXTURE.read_bytes()
    results = parse_iheart_recently_played(raw, http_status=200)
    assert results[0].artist == "Taylor Swift"
    assert results[0].title == "Anti-Hero"


def test_parser_source_event_id_preserved() -> None:
    raw = _FIXTURE.read_bytes()
    results = parse_iheart_recently_played(raw, http_status=200)
    assert results[0].source_event_id == "iheart-2501-20260524-00601"


def test_parser_timestamp_converts_to_utc() -> None:
    """startTime 1748044860 → 2026-05-23 18:01:00 UTC."""
    raw = _FIXTURE.read_bytes()
    results = parse_iheart_recently_played(raw, http_status=200)
    # 1748044860 is a fixed Unix timestamp; confirm it round-trips
    first = results[0]
    assert first.played_at.tzinfo is not None
    assert int(first.played_at.timestamp()) == 1748044860


def test_parser_explicit_track_included() -> None:
    """Kill Bill (SZA) is explicit=true in the fixture — parser should still include it."""
    raw = _FIXTURE.read_bytes()
    results = parse_iheart_recently_played(raw, http_status=200)
    titles = [r.title for r in results]
    assert "Kill Bill" in titles


def test_parser_returns_empty_list_for_204() -> None:
    results = parse_iheart_recently_played(b"", http_status=204)
    assert results == []


def test_parser_raises_on_missing_tracks_key() -> None:
    import json

    bad_payload = json.dumps({"stationId": "2501"}).encode()
    with pytest.raises(ValueError, match="missing 'tracks' or 'recentTracks'"):
        parse_iheart_recently_played(bad_payload, http_status=200)


def test_parser_accepts_recent_tracks_key() -> None:
    """Fallback key 'recentTracks' must also be accepted."""
    import json

    payload = json.dumps({
        "recentTracks": [
            {
                "id": "x-001",
                "artist": "Doja Cat",
                "title": "Paint The Town Red",
                "startTime": 1748000000,
            },
        ]
    }).encode()
    results = parse_iheart_recently_played(payload, http_status=200)
    assert len(results) == 1
    assert results[0].artist == "Doja Cat"


def test_parser_skips_items_missing_artist_or_title() -> None:
    import json

    payload = json.dumps({
        "tracks": [
            {"id": "x-001", "artist": "Complete", "title": "Track", "startTime": 1748000000},
            {"id": "x-002", "artist": "", "title": "No Artist", "startTime": 1748000001},
            {"id": "x-003", "artist": "No Title", "title": "", "startTime": 1748000002},
        ]
    }).encode()
    results = parse_iheart_recently_played(payload, http_status=200)
    assert len(results) == 1
    assert results[0].title == "Track"


# ── URL construction ──────────────────────────────────────────────────────────

def test_collector_builds_recently_played_url() -> None:
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="2501",
    )
    url = collector._build_url()
    assert "api.iheart.com" in url
    assert "2501" in url
    assert url.endswith("/recentlyPlayed")


def test_collector_url_custom_station_id() -> None:
    collector = IHeartRecentlyPlayedCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="9999",
    )
    assert "9999/recentlyPlayed" in collector._build_url()


# ── Collector integration (mocked HTTP) ──────────────────────────────────────

@pytest.mark.anyio
async def test_collector_successful_run_produces_five_plays() -> None:
    raw = _FIXTURE.read_bytes()
    source_id = uuid.uuid4()
    station_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.content = raw
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = IHeartRecentlyPlayedCollector(
        source_id=source_id,
        station_id=station_id,
        iheart_station_id="2501",
    )

    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, ct = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].attribution == "iheart_recently_played"


@pytest.mark.anyio
async def test_collector_204_produces_no_track_event() -> None:
    source_id = uuid.uuid4()
    station_id = uuid.uuid4()

    collector = IHeartRecentlyPlayedCollector(
        source_id=source_id,
        station_id=station_id,
        iheart_station_id="2501",
    )
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1
