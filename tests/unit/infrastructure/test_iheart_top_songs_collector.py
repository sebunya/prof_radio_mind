"""Tests for the generic IHeartTopSongsCollector and parse_iheart_top_songs parser.

No live network calls. Uses saved JSON fixtures.
One generic collector class, three station fixtures (KIIS-2501, Z100-614, WKSC-821).

VAL-IHEART-TOP-001: topSongs endpoint URL and schema are UNVALIDATED — confirm via
DevTools on any iHeart station page before enabling.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.collectors.iheart_top_songs import IHeartTopSongsCollector
from app.infrastructure.parsers.iheart import parse_iheart_top_songs

_FIXTURE_KIIS = Path(__file__).parent.parent.parent / "fixtures/json/iheart_kiis_top_songs.json"
_FIXTURE_Z100 = Path(__file__).parent.parent.parent / "fixtures/json/iheart_z100_top_songs.json"
_FIXTURE_WKSC = Path(__file__).parent.parent.parent / "fixtures/json/iheart_wksc_top_songs.json"


# ── Parser unit tests ─────────────────────────────────────────────────────────

def test_parser_returns_five_results_from_kiis_fixture() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="2501")
    assert len(results) == 5


def test_parser_first_result_rank_and_artist() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="2501")
    top = results[0]
    assert top.rank == 1
    assert top.artist == "Olivia Rodrigo"
    assert top.title == "good 4 u"
    assert top.play_count == 52


def test_parser_ranks_are_sequential() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="2501")
    assert [r.rank for r in results] == [1, 2, 3, 4, 5]


def test_parser_source_event_id_from_fixture_id() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="2501")
    assert results[0].source_event_id == "top-2501-rank1-20260604"


def test_parser_source_event_id_fallback_when_no_id() -> None:
    payload = b'{"topSongs": [{"artist": "A", "title": "T", "rank": 1}]}'
    results = parse_iheart_top_songs(payload, 200, iheart_station_id="9999")
    assert results[0].source_event_id is not None
    assert "9999" in results[0].source_event_id
    assert "rank1" in results[0].source_event_id


def test_parser_204_returns_empty_list() -> None:
    results = parse_iheart_top_songs(b"", 204, iheart_station_id="2501")
    assert results == []


def test_parser_snapshot_at_is_utc_aware() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="2501")
    assert results[0].snapshot_at.tzinfo is not None


def test_parser_accepts_artist_name_key() -> None:
    payload = b'{"topSongs": [{"artistName": "Adele", "title": "Hello", "rank": 1}]}'
    results = parse_iheart_top_songs(payload, 200, iheart_station_id="123")
    assert results[0].artist == "Adele"


def test_parser_skips_entries_missing_artist_or_title() -> None:
    payload = (
        b'{"topSongs": ['
        b'{"title": "No Artist"}, '
        b'{"artist": "No Title"}, '
        b'{"artist": "A", "title": "T", "rank": 1}'
        b"]}"
    )
    results = parse_iheart_top_songs(payload, 200, iheart_station_id="123")
    assert len(results) == 1


def test_parser_falls_back_to_songs_key() -> None:
    payload = b'{"songs": [{"artist": "A", "title": "T", "rank": 1}]}'
    results = parse_iheart_top_songs(payload, 200, iheart_station_id="123")
    assert len(results) == 1


def test_parser_raises_on_missing_top_songs_key() -> None:
    payload = b'{"notTopSongs": []}'
    with pytest.raises(ValueError, match="missing"):
        parse_iheart_top_songs(payload, 200, iheart_station_id="123")


def test_parser_raises_on_invalid_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_iheart_top_songs(b"not json", 200, iheart_station_id="123")


def test_parser_z100_fixture_first_is_cruel_summer() -> None:
    raw = _FIXTURE_Z100.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="614")
    assert results[0].artist == "Taylor Swift"
    assert results[0].title == "Cruel Summer"
    assert results[0].rank == 1


def test_parser_wksc_fixture_first_is_anti_hero() -> None:
    raw = _FIXTURE_WKSC.read_bytes()
    results = parse_iheart_top_songs(raw, 200, iheart_station_id="821")
    assert results[0].artist == "Taylor Swift"
    assert results[0].title == "Anti-Hero"
    assert results[0].rank == 1


# ── Collector unit tests ──────────────────────────────────────────────────────

def test_collector_url_contains_station_id_and_top_songs() -> None:
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="2501",
    )
    url = collector._build_url()
    assert "2501" in url
    assert url.endswith("/topSongs")
    assert "api.iheart.com" in url


def test_collector_url_with_different_station_id() -> None:
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        iheart_station_id="614",
    )
    assert "614/topSongs" in collector._build_url()


def test_collector_parse_kiis_fixture_produces_five_plays() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="2501"
    )
    plays, no_tracks = collector.parse(raw, 200, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []


def test_collector_parse_z100_fixture_first_play() -> None:
    raw = _FIXTURE_Z100.read_bytes()
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].raw_title == "Cruel Summer"
    assert plays[0].attribution == "iheart_top_songs"


def test_collector_parse_wksc_fixture_first_play() -> None:
    raw = _FIXTURE_WKSC.read_bytes()
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="821"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].raw_title == "Anti-Hero"
    assert plays[0].attribution == "iheart_top_songs"


def test_collector_204_produces_no_track_event() -> None:
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="2501"
    )
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_collector_empty_list_produces_no_track_event() -> None:
    payload = b'{"topSongs": []}'
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="2501"
    )
    plays, no_tracks = collector.parse(payload, 200, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_collector_played_at_is_utc_aware() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="2501"
    )
    plays, _ = collector.parse(raw, 200, uuid.uuid4())
    assert plays[0].played_at.tzinfo is not None


@pytest.mark.anyio
async def test_collector_fetch_and_parse_mocked_kiis() -> None:
    raw = _FIXTURE_KIIS.read_bytes()
    mock_response = MagicMock()
    mock_response.content = raw
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="2501"
    )
    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, _ = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []


@pytest.mark.anyio
async def test_collector_fetch_and_parse_mocked_z100() -> None:
    raw = _FIXTURE_Z100.read_bytes()
    mock_response = MagicMock()
    mock_response.content = raw
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = IHeartTopSongsCollector(
        source_id=uuid.uuid4(), station_id=uuid.uuid4(), iheart_station_id="614"
    )
    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, _ = await collector.fetch_raw()

    plays, _ = collector.parse(raw_bytes, status, uuid.uuid4())
    assert plays[0].raw_artist == "Taylor Swift"
