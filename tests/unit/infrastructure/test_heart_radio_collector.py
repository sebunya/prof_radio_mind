"""Fixture-driven tests for the Heart FM last-played-songs collector and parser.

No live network calls. All tests use the updated HTML fixtures that reflect the
live page structure confirmed during VAL-HEARTFM-002 (2026-06-05).

Fixture structure (new selectors):
  div.last_played_songs > div.song_wrapper > div.song__text-content
    p.song__title / p.song__artist
  span.song__time

Three-strategy parser coverage:
  - New CSS selectors (primary for live page)
  - Old CSS selectors (backwards compat, tested via inline HTML)
  - __NEXT_DATA__ JSON (Next.js, tested via inline HTML)
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.collectors.heart_radio import HeartRadioCollector
from app.infrastructure.parsers.heart import parse_heart_last_played

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/heart_fm_last_played.html"
_EMPTY_FIXTURE = (
    Path(__file__).parent.parent.parent / "fixtures/html/heart_fm_last_played_empty.html"
)


# ── New-selector parser tests ─────────────────────────────────────────────────


def test_parser_extracts_five_tracks() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert len(results) == 5


def test_parser_first_track_is_harry_styles() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert results[0].artist == "Harry Styles"
    assert results[0].title == "As It Was"


def test_parser_source_event_id_from_data_attribute() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert results[0].source_event_id == "hfm-20260524-001"


def test_parser_timestamp_anchored_to_base_date() -> None:
    """06:18 in the fixture, base_date=2026-05-24 → 2026-05-24T06:18:00+00:00."""
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    first = results[0]
    assert first.played_at.year == 2026
    assert first.played_at.month == 5
    assert first.played_at.day == 24
    assert first.played_at.hour == 6
    assert first.played_at.minute == 18
    assert first.played_at.tzinfo is not None


def test_parser_all_tracks_have_artist_and_title() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    for r in results:
        assert r.artist
        assert r.title


def test_parser_returns_empty_list_for_204() -> None:
    assert parse_heart_last_played(b"", http_status=204) == []


def test_parser_raises_on_empty_html() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_heart_last_played(b"")


def test_parser_raises_on_missing_container() -> None:
    """No recognised container → ValueError for drift detection."""
    html = b"<html><body><div class='unknown-wrapper'></div></body></html>"
    with pytest.raises(ValueError, match="unrecognised"):
        parse_heart_last_played(html)


def test_parser_returns_empty_list_for_empty_fixture() -> None:
    """Empty track list inside the container returns [] without raising."""
    html = _EMPTY_FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert results == []


def test_parser_tracks_have_unique_source_event_ids() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    ids = [r.source_event_id for r in results if r.source_event_id]
    assert len(ids) == len(set(ids))


def test_parser_second_track_is_miley_cyrus() -> None:
    html = _FIXTURE.read_bytes()
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert results[1].artist == "Miley Cyrus"
    assert results[1].title == "Flowers"


# ── Old-selector backwards-compat test ───────────────────────────────────────


def test_old_selectors_still_parse() -> None:
    """Parser falls back to old div.station-song-history selectors."""
    html = b"""
    <html><body>
    <div class="station-song-history">
      <div class="song-item" data-track-id="old-001">
        <span class="song-item__title">Shape of You</span>
        <span class="song-item__artist">Ed Sheeran</span>
        <time class="song-item__time">08:00</time>
      </div>
    </div>
    </body></html>
    """
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert len(results) == 1
    assert results[0].artist == "Ed Sheeran"
    assert results[0].title == "Shape of You"
    assert results[0].source_event_id == "old-001"


# ── __NEXT_DATA__ JSON strategy test ─────────────────────────────────────────


def test_next_data_strategy_extracts_tracks() -> None:
    """__NEXT_DATA__ JSON is parsed before any CSS selectors are tried."""
    page_data = {
        "props": {
            "pageProps": {
                "lastPlayedSongs": [
                    {"title": "Watermelon Sugar", "artist": "Harry Styles", "playTime": "09:30"},
                    {"title": "Bad Guy", "artist": "Billie Eilish", "playTime": "09:26"},
                ]
            }
        }
    }
    html = (
        b"<html><body>"
        b'<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(page_data).encode()
        + b"</script>"
        b"</body></html>"
    )
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert len(results) == 2
    assert results[0].title == "Watermelon Sugar"
    assert results[0].artist == "Harry Styles"
    assert results[0].played_at.hour == 9
    assert results[0].played_at.minute == 30


def test_next_data_strategy_ignores_malformed_json() -> None:
    """Malformed __NEXT_DATA__ falls through to CSS strategies."""
    html = b"""
    <html><body>
    <script id="__NEXT_DATA__" type="application/json">{bad json}</script>
    <div class="last_played_songs">
      <div class="song_wrapper" data-track-id="x-001">
        <div class="song__text-content">
          <p class="song__title">Levitating</p>
          <p class="song__artist">Dua Lipa</p>
        </div>
      </div>
    </div>
    </body></html>
    """
    results = parse_heart_last_played(html, base_date=date(2026, 5, 24))
    assert len(results) == 1
    assert results[0].title == "Levitating"


# ── Collector integration tests ───────────────────────────────────────────────


def test_collector_url_is_heart_last_played() -> None:
    collector = HeartRadioCollector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    assert "heart.co.uk" in collector.base_url
    assert "last-played-songs" in collector.base_url


def test_collector_custom_base_url() -> None:
    custom = "https://example.com/last-played/"
    collector = HeartRadioCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        base_url=custom,
    )
    assert collector.base_url == custom


@pytest.mark.anyio
async def test_collector_successful_run_produces_five_plays() -> None:
    html = _FIXTURE.read_bytes()
    source_id = uuid.uuid4()
    station_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.content = html
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = HeartRadioCollector(source_id=source_id, station_id=station_id)

    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw_bytes, status, ct = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw_bytes, status, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []
    assert plays[0].raw_artist == "Harry Styles"
    assert plays[0].raw_title == "As It Was"
    assert plays[0].attribution == "heart"


def test_collector_204_produces_no_track_event() -> None:
    collector = HeartRadioCollector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    plays, no_tracks = collector.parse(b"", 204, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1


def test_collector_empty_fixture_produces_no_track_event() -> None:
    """Empty track list (valid HTML, no items) yields NoTrackEvent."""
    html = _EMPTY_FIXTURE.read_bytes()
    collector = HeartRadioCollector(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    plays, no_tracks = collector.parse(html, 200, uuid.uuid4())
    assert plays == []
    assert len(no_tracks) == 1
