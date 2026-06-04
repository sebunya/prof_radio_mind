"""Fixture-driven tests for the BBC Radio 1 Sounds collector and parser.

No live network calls. All parser tests use the saved JSON fixture.
Verifies:
  - Parser extracts the now_playing music segment correctly
  - Speech segments are skipped
  - First music segment is used when now_playing flag is absent
  - Timestamps are converted to UTC
  - HTTP 204 produces a NoTrackEvent (no play events)
  - All-speech response returns None (no play events)
  - Collector URL is the BBC RMS endpoint
  - attribution is 'bbc_sounds'
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.collectors.bbc_radio_1 import BBCRadio1Collector
from app.infrastructure.parsers.bbc_sounds import parse_bbc_sounds_now_playing

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/json/bbc_radio1_segments.json"


# ── Parser-level tests (fixture-driven) ──────────────────────────────────────

def test_parser_returns_now_playing_music_segment() -> None:
    raw = _FIXTURE.read_bytes()
    result = parse_bbc_sounds_now_playing(raw, http_status=200)
    assert result is not None
    assert result.artist == "Sabrina Carpenter"
    assert result.title == "Espresso"


def test_parser_source_event_id_from_segment_id() -> None:
    raw = _FIXTURE.read_bytes()
    result = parse_bbc_sounds_now_playing(raw, http_status=200)
    assert result is not None
    assert result.source_event_id == "bbc-r1-p0seg001"


def test_parser_timestamp_converts_to_utc() -> None:
    """offset.start 1748044860 must round-trip as a UTC timestamp."""
    raw = _FIXTURE.read_bytes()
    result = parse_bbc_sounds_now_playing(raw, http_status=200)
    assert result is not None
    assert result.played_at.tzinfo is not None
    assert int(result.played_at.timestamp()) == 1748044860


def test_parser_returns_none_for_204() -> None:
    assert parse_bbc_sounds_now_playing(b"", http_status=204) is None


def test_parser_raises_on_missing_data_key() -> None:
    bad = json.dumps({"segments": []}).encode()
    with pytest.raises(ValueError, match="missing 'data' field"):
        parse_bbc_sounds_now_playing(bad, http_status=200)


def test_parser_raises_on_invalid_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_bbc_sounds_now_playing(b"not json", http_status=200)


def test_parser_skips_speech_segments() -> None:
    """Response with only speech segments should return None."""
    payload = json.dumps({
        "data": [
            {
                "id": "speech-001",
                "type": "speech",
                "offset": {"start": 1748000000, "now_playing": True},
                "titles": {"primary": "Breakfast Show Chat"},
                "primary_contributors": [{"id": "x", "name": "Greg James"}],
            }
        ]
    }).encode()
    assert parse_bbc_sounds_now_playing(payload, http_status=200) is None


def test_parser_falls_back_to_first_music_when_no_now_playing_flag() -> None:
    """When now_playing is absent, the first music segment is returned."""
    payload = json.dumps({
        "data": [
            {
                "id": "seg-a",
                "type": "music",
                "offset": {"start": 1748000200, "now_playing": False},
                "titles": {"primary": "Track A"},
                "primary_contributors": [{"id": "x", "name": "Artist A"}],
            },
            {
                "id": "seg-b",
                "type": "music",
                "offset": {"start": 1748000000, "now_playing": False},
                "titles": {"primary": "Track B"},
                "primary_contributors": [{"id": "y", "name": "Artist B"}],
            },
        ]
    }).encode()
    result = parse_bbc_sounds_now_playing(payload, http_status=200)
    assert result is not None
    assert result.title == "Track A"
    assert result.source_event_id == "seg-a"


def test_parser_prefers_now_playing_true_over_first_segment() -> None:
    """If a later segment has now_playing=True it wins over the first item."""
    payload = json.dumps({
        "data": [
            {
                "id": "seg-first",
                "type": "music",
                "offset": {"start": 1748000300, "now_playing": False},
                "titles": {"primary": "First Song"},
                "primary_contributors": [{"id": "x", "name": "First Artist"}],
            },
            {
                "id": "seg-live",
                "type": "music",
                "offset": {"start": 1748000100, "now_playing": True},
                "titles": {"primary": "Live Song"},
                "primary_contributors": [{"id": "y", "name": "Live Artist"}],
            },
        ]
    }).encode()
    result = parse_bbc_sounds_now_playing(payload, http_status=200)
    assert result is not None
    assert result.title == "Live Song"
    assert result.artist == "Live Artist"


def test_parser_returns_none_when_music_segment_missing_artist() -> None:
    payload = json.dumps({
        "data": [
            {
                "id": "seg-001",
                "type": "music",
                "offset": {"start": 1748000000, "now_playing": True},
                "titles": {"primary": "A Song"},
                "primary_contributors": [],
            }
        ]
    }).encode()
    assert parse_bbc_sounds_now_playing(payload, http_status=200) is None


# ── Collector tests ───────────────────────────────────────────────────────────

def test_collector_url_is_bbc_rms_endpoint() -> None:
    collector = BBCRadio1Collector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    assert "rms.api.bbc.co.uk" in collector.base_url
    assert "bbc_radio_one/segments/latest" in collector.base_url


def test_collector_custom_base_url() -> None:
    custom = "https://example.com/v2/services/bbc_radio_one/segments/latest"
    collector = BBCRadio1Collector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        base_url=custom,
    )
    assert collector.base_url == custom


@pytest.mark.anyio
async def test_collector_successful_run_produces_play_event() -> None:
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

    collector = BBCRadio1Collector(source_id=source_id, station_id=station_id)

    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, ct = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 1
    assert no_tracks == []
    assert plays[0].raw_artist == "Sabrina Carpenter"
    assert plays[0].raw_title == "Espresso"
    assert plays[0].attribution == "bbc_sounds"


def test_collector_204_produces_no_track_event() -> None:
    collector = BBCRadio1Collector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_collector_all_speech_produces_no_track_event() -> None:
    """All-speech response yields NoTrackEvent, not a crash."""
    payload = json.dumps({
        "data": [
            {
                "id": "speech-001",
                "type": "speech",
                "offset": {"start": 1748000000, "now_playing": True},
                "titles": {"primary": "Chat"},
                "primary_contributors": [],
            }
        ]
    }).encode()
    collector = BBCRadio1Collector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    plays, no_tracks = collector.parse(payload, 200, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1
