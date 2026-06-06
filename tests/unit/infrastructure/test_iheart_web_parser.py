"""Fixture-driven tests for the iHeart web recently-played HTML parser.

No live network calls. All tests use the saved HTML fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.parsers.iheart_web import (
    IHeartWebParseResult,
    parse_iheart_web_recently_played,
)

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/iheart_recently_played.html"


@pytest.fixture
def fixture_html() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.fixture
def parse_results(fixture_html: bytes) -> list[IHeartWebParseResult]:
    return parse_iheart_web_recently_played(fixture_html)


def test_parser_extracts_five_tracks(parse_results: list[IHeartWebParseResult]) -> None:
    assert len(parse_results) == 5


def test_parser_correct_first_title(parse_results: list[IHeartWebParseResult]) -> None:
    assert parse_results[0].title == "Homewrecker"


def test_parser_correct_first_artist(parse_results: list[IHeartWebParseResult]) -> None:
    assert parse_results[0].artist == "sombr"


def test_parser_correct_second_title(parse_results: list[IHeartWebParseResult]) -> None:
    assert parse_results[1].title == "WILDFLOWER"


def test_parser_correct_second_artist(parse_results: list[IHeartWebParseResult]) -> None:
    assert parse_results[1].artist == "Billie Eilish"


def test_played_at_has_timezone(parse_results: list[IHeartWebParseResult]) -> None:
    for result in parse_results:
        assert result.played_at.tzinfo is not None


def test_played_at_converted_to_utc(parse_results: list[IHeartWebParseResult]) -> None:
    for result in parse_results:
        assert result.played_at.utcoffset() is not None


def test_first_played_at_correct_utc(parse_results: list[IHeartWebParseResult]) -> None:
    # 2026-06-05T11:50:33 America/Los_Angeles (PDT = UTC-7) → 18:50:33 UTC
    ev = parse_results[0]
    assert ev.played_at.hour == 18
    assert ev.played_at.minute == 50


def test_http_error_returns_empty() -> None:
    result = parse_iheart_web_recently_played(b"<html/>", http_status=404)
    assert result == []


def test_http_500_returns_empty() -> None:
    result = parse_iheart_web_recently_played(b"<html/>", http_status=500)
    assert result == []


def test_empty_html_returns_empty() -> None:
    result = parse_iheart_web_recently_played(b"<html><body></body></html>")
    assert result == []


def test_figcaption_without_track_title_skipped() -> None:
    html = b"""
    <html><body>
    <figure>
      <figcaption><span>No track-title class here</span></figcaption>
    </figure>
    </body></html>
    """
    assert parse_iheart_web_recently_played(html) == []


def test_figcaption_missing_artist_skipped() -> None:
    html = b"""
    <html><body>
    <figure>
      <figcaption>
        <a class="track-title"><span>Some Song</span></a>
      </figcaption>
    </figure>
    </body></html>
    """
    assert parse_iheart_web_recently_played(html) == []


def test_next_data_strategy_still_works() -> None:
    import json
    data = {
        "props": {
            "pageProps": {
                "recentlyPlayedSongs": [
                    {"title": "Song A", "artist": "Artist A", "startTime": 1748000000000},
                    {"title": "Song B", "artist": "Artist B", "startTime": 1748000100000},
                ]
            }
        }
    }
    html = (
        b'<html><body><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(data).encode()
        + b"</script></body></html>"
    )
    results = parse_iheart_web_recently_played(html)
    assert len(results) == 2
    assert results[0].title == "Song A"
    assert results[0].artist == "Artist A"
