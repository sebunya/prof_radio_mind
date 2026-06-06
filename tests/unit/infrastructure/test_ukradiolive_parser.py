"""Fixture-driven tests for the ukradiolive.com playlist HTML parser.

No live network calls. All tests use the saved HTML fixture.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.infrastructure.parsers.ukradiolive import (
    UKRadioLiveParseResult,
    parse_ukradiolive_playlist,
)

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/ukradiolive_playlist.html"


@pytest.fixture
def fixture_html() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.fixture
def parse_results(fixture_html: bytes) -> list[UKRadioLiveParseResult]:
    return parse_ukradiolive_playlist(fixture_html, ref_date=date(2026, 6, 6))


def test_parser_extracts_five_tracks(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert len(parse_results) == 5


def test_parser_correct_first_artist(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert parse_results[0].artist == "Fatman Scoop"


def test_parser_correct_first_title(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert parse_results[0].title == "Be Faithful"


def test_parser_correct_second_artist(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert parse_results[1].artist == "Justin Bieber feat. Nicki Minaj"


def test_parser_correct_second_title(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert parse_results[1].title == "Beauty And A Beat"


def test_played_at_has_timezone(parse_results: list[UKRadioLiveParseResult]) -> None:
    for result in parse_results:
        assert result.played_at.tzinfo is not None


def test_source_event_id_extracted(parse_results: list[UKRadioLiveParseResult]) -> None:
    assert parse_results[0].source_event_id == "163212182"
    assert parse_results[1].source_event_id == "163211971"


def test_live_prefix_parsed(parse_results: list[UKRadioLiveParseResult]) -> None:
    # First item has "LIVE - 06.06 06:07" — must still produce a valid datetime
    ev = parse_results[0]
    assert ev.played_at.tzinfo is not None
    # 06:07 BST (UTC+1) → 05:07 UTC
    assert ev.played_at.hour == 5
    assert ev.played_at.minute == 7


def test_non_live_item_parsed(parse_results: list[UKRadioLiveParseResult]) -> None:
    ev = parse_results[1]
    # 06:03 BST (UTC+1) → 05:03 UTC
    assert ev.played_at.hour == 5
    assert ev.played_at.minute == 3


def test_http_error_returns_empty() -> None:
    result = parse_ukradiolive_playlist(b"<html/>", http_status=404)
    assert result == []


def test_http_503_returns_empty() -> None:
    result = parse_ukradiolive_playlist(b"<html/>", http_status=503)
    assert result == []


def test_empty_html_returns_empty() -> None:
    result = parse_ukradiolive_playlist(b"<html><body></body></html>")
    assert result == []


def test_plist_item_without_txtsong_skipped() -> None:
    html = b"""
    <html><body>
    <div class="plist-item" data-id="1">
      <span class="txt2 mcolumn">06.06 10:00</span>
    </div>
    </body></html>
    """
    # txtsong span is missing — whole item skipped, and guard prevents false positives
    result = parse_ukradiolive_playlist(html, ref_date=date(2026, 6, 6))
    assert result == []


def test_year_rollback_when_month_ahead() -> None:
    # If ref_date is Jan 2027 and item is December, year should roll back to 2026
    html = b"""
    <html><body>
    <div class="plist-item" data-id="999">
      <span class="txt2 mcolumn">12.12 23:55</span>
      <span class="txtsong mcolumn">
        <span itemprop="byArtist">Test Artist</span>
        -
        <span itemprop="name">Test Song</span>
      </span>
    </div>
    </body></html>
    """
    result = parse_ukradiolive_playlist(html, ref_date=date(2027, 1, 5))
    assert len(result) == 1
    assert result[0].played_at.year == 2026
