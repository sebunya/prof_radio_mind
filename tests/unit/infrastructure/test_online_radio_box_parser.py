"""Fixture-driven tests for the Online Radio Box HTML parser.

No live network calls. All tests use saved HTML fixtures.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.infrastructure.parsers.online_radio_box import (
    parse_online_radio_box_history,
    parse_online_radio_box_now_playing,
    split_artist_title,
)

_FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures/html"
_FIXTURE_VALID = _FIXTURE_DIR / "online_radio_box_capital_valid.html"
_FIXTURE_MISSING = _FIXTURE_DIR / "online_radio_box_capital_missing.html"
_FIXTURE_MALFORMED = _FIXTURE_DIR / "online_radio_box_capital_malformed.html"


@pytest.fixture
def valid_html() -> bytes:
    return _FIXTURE_VALID.read_bytes()


@pytest.fixture
def missing_html() -> bytes:
    return _FIXTURE_MISSING.read_bytes()


@pytest.fixture
def malformed_html() -> bytes:
    return _FIXTURE_MALFORMED.read_bytes()


def test_parse_valid_now_playing(valid_html: bytes) -> None:
    result = parse_online_radio_box_now_playing(valid_html)
    assert result is not None
    assert result.artist == "Taylor Swift"
    assert result.title == "Elizabeth Taylor"
    assert result.source_event_id == "1513304645257968715"
    assert isinstance(result.played_at, datetime)
    assert result.played_at.tzinfo == UTC


def test_parse_missing_now_playing(missing_html: bytes) -> None:
    # missing fixture does not contain "Live" row, should return None
    result = parse_online_radio_box_now_playing(missing_html)
    assert result is None


def test_parse_malformed_html(malformed_html: bytes) -> None:
    # malformed fixture does not contain schedule table, should raise ValueError
    with pytest.raises(ValueError, match="Could not find table.tablelist-schedule"):
        parse_online_radio_box_now_playing(malformed_html)


def test_parse_empty_html_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Empty HTML content"):
        parse_online_radio_box_now_playing(b"")


def test_parse_now_playing_204_returns_none() -> None:
    result = parse_online_radio_box_now_playing(b"some content", http_status=204)
    assert result is None


def test_artist_title_splitting_no_b_tag() -> None:
    # Test split_artist_title helper
    artist, title = split_artist_title("The Weeknd - Blinding Lights")
    assert artist == "The Weeknd"
    assert title == "Blinding Lights"

    artist2, title2 = split_artist_title("Dua Lipa — Levitating")
    assert artist2 == "Dua Lipa"
    assert title2 == "Levitating"

    # No delimiter fallback
    artist3, title3 = split_artist_title("SingleNameArtist")
    assert artist3 == ""
    assert title3 == "SingleNameArtist"


def test_parse_history_extraction_and_timestamps(valid_html: bytes) -> None:
    base_date = date(2026, 5, 24)
    history = parse_online_radio_box_history(valid_html, base_date=base_date)

    # Valid fixture contains 3 items (1 live, 2 history)
    assert len(history) == 3

    # Check first track (Live)
    assert history[0].artist == "Taylor Swift"
    assert history[0].title == "Elizabeth Taylor"
    assert history[0].source_event_id == "1513304645257968715"
    assert (datetime.now(tz=UTC) - history[0].played_at).total_seconds() < 10

    # Check second track (History at 15:35)
    assert history[1].artist == "Macklemore & Ryan Lewis"
    assert history[1].title == "Thrift Shop (feat. Wanz)"
    assert history[1].source_event_id == "77815825"
    assert history[1].played_at == datetime(2026, 5, 24, 15, 35, tzinfo=UTC)

    # Check third track (History at 15:32)
    assert history[2].artist == "Djo"
    assert history[2].title == "End of Beginning"
    assert history[2].source_event_id == "41997679743852"
    assert history[2].played_at == datetime(2026, 5, 24, 15, 32, tzinfo=UTC)


def test_parse_history_missing_table(malformed_html: bytes) -> None:
    history = parse_online_radio_box_history(malformed_html)
    assert history == []
