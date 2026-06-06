"""Fixture-driven tests for the radoxo.com playlist HTML parser.

No live network calls. All tests use the saved HTML fixture.
Timestamps confirmed against real radoxo.com HTML (2026-06-06).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.infrastructure.parsers.radoxo import (
    RadoxoParseResult,
    parse_radoxo_playlist,
)

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/radoxo_nova969_playlist.html"


@pytest.fixture
def fixture_html() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.fixture
def parse_results(fixture_html: bytes) -> list[RadoxoParseResult]:
    return parse_radoxo_playlist(fixture_html)


def test_parser_extracts_five_tracks(parse_results: list[RadoxoParseResult]) -> None:
    assert len(parse_results) == 5


def test_parser_correct_first_title(parse_results: list[RadoxoParseResult]) -> None:
    assert parse_results[0].title == "Scudda In The Mix"


def test_parser_correct_first_artist(parse_results: list[RadoxoParseResult]) -> None:
    assert parse_results[0].artist == "Nova Nation"


def test_parser_correct_second_title(parse_results: list[RadoxoParseResult]) -> None:
    assert parse_results[1].title == "New Religion"


def test_parser_correct_second_artist(parse_results: list[RadoxoParseResult]) -> None:
    assert parse_results[1].artist == "Bebe Rexha & Faithless"


def test_played_at_has_timezone(parse_results: list[RadoxoParseResult]) -> None:
    for result in parse_results:
        assert result.played_at.tzinfo is not None


def test_played_at_from_unix_timestamp(parse_results: list[RadoxoParseResult]) -> None:
    # data-ts=1780725836 → 2026-06-06T06:03:56 UTC
    ev = parse_results[0]
    assert ev.played_at == datetime(2026, 6, 6, 6, 3, 56, tzinfo=UTC)


def test_source_event_id_is_radoxo_prefixed(parse_results: list[RadoxoParseResult]) -> None:
    for r in parse_results:
        assert r.source_event_id is not None
        assert r.source_event_id.startswith("radoxo-")


def test_source_event_id_includes_timestamp(parse_results: list[RadoxoParseResult]) -> None:
    assert parse_results[0].source_event_id == "radoxo-1780725836"
    assert parse_results[1].source_event_id == "radoxo-1780725258"


def test_tracks_are_ordered_newest_first(parse_results: list[RadoxoParseResult]) -> None:
    # radoxo page orders newest first (latest broadcast time at top)
    timestamps = [r.played_at.timestamp() for r in parse_results]
    assert timestamps == sorted(timestamps, reverse=True)


def test_http_error_returns_empty() -> None:
    assert parse_radoxo_playlist(b"<html/>", http_status=404) == []


def test_http_503_returns_empty() -> None:
    assert parse_radoxo_playlist(b"<html/>", http_status=503) == []


def test_empty_html_returns_empty() -> None:
    assert parse_radoxo_playlist(b"<html><body></body></html>") == []


def test_missing_data_ts_falls_back_to_now() -> None:
    html = b"""
    <html><body>
    <li class="playlist-track">
      <span class="playlist-track__status js-playlist-local-time">08:21</span>
      <div class="playlist-track__info">
        <span class="playlist-track__song">Test Song</span>
        <span class="playlist-track__artist">Test Artist</span>
      </div>
    </li>
    </body></html>
    """
    results = parse_radoxo_playlist(html)
    assert len(results) == 1
    assert results[0].played_at.tzinfo is not None
    assert results[0].source_event_id is None


def test_track_missing_title_skipped() -> None:
    html = b"""
    <html><body>
    <li class="playlist-track">
      <span class="playlist-track__status" data-ts="1780725836">06:03</span>
      <div class="playlist-track__info">
        <span class="playlist-track__artist">Some Artist</span>
      </div>
    </li>
    <li class="playlist-track">
      <span class="playlist-track__status" data-ts="1780725000">05:50</span>
      <div class="playlist-track__info">
        <span class="playlist-track__song">Good Song</span>
        <span class="playlist-track__artist">Good Artist</span>
      </div>
    </li>
    </body></html>
    """
    results = parse_radoxo_playlist(html)
    assert len(results) == 1
    assert results[0].title == "Good Song"


def test_real_html_parses_86_tracks() -> None:
    """Smoke test against the actual captured HTML — must find >= 80 tracks."""
    _fname = "10d8735d-radoxo_com_australia_nova_969.html"
    _uploads = "43924d6f-45ac-540f-9413-a47c35e3f8d9"
    real_html_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / ".claude/uploads" / _uploads / _fname
    )
    if not real_html_path.exists():
        pytest.skip("Real HTML fixture not available in this environment")
    results = parse_radoxo_playlist(real_html_path.read_bytes())
    assert len(results) >= 80
    assert results[0].artist == "Nova Nation"
    assert results[0].title == "Scudda In The Mix"
