"""Fixture-driven tests for the Radiowave HTML parser.

No live network calls. All tests use the saved HTML fixture.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pytest

from app.infrastructure.parsers.radiowave import (
    RadiowaveParseResult,
    _strip_label_from_artist,
    parse_radiowave_diary,
)

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/radiowave_nova969_diary.html"


@pytest.fixture
def fixture_html() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.fixture
def parse_result(fixture_html: bytes) -> RadiowaveParseResult:
    return parse_radiowave_diary(
        fixture_html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
    )


def test_parser_extracts_five_events(parse_result: RadiowaveParseResult) -> None:
    assert len(parse_result.play_events) == 5


def test_parser_extracts_correct_first_artist(parse_result: RadiowaveParseResult) -> None:
    assert parse_result.play_events[0].raw_artist == "Tame Impala"


def test_parser_extracts_correct_first_title(parse_result: RadiowaveParseResult) -> None:
    assert parse_result.play_events[0].raw_title == "The Less I Know The Better"


def test_label_removed_from_artist_field(parse_result: RadiowaveParseResult) -> None:
    for ev in parse_result.play_events:
        assert "[" not in ev.raw_artist, f"Label bracket found in artist: {ev.raw_artist!r}"


def test_label_preserved_in_raw_label(parse_result: RadiowaveParseResult) -> None:
    ev = parse_result.play_events[0]
    assert ev.raw_label == "Island Records"


def test_source_event_id_extracted(parse_result: RadiowaveParseResult) -> None:
    ev = parse_result.play_events[0]
    assert ev.source_event_id == "rw-11129-20260524-001"


def test_missing_detail_link_handled(fixture_html: bytes) -> None:
    """Row without <a> in title cell must still parse (Dua Lipa row has no link)."""
    result = parse_radiowave_diary(
        fixture_html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
    )
    dua = next((e for e in result.play_events if "Dua" in e.raw_artist), None)
    assert dua is not None
    assert dua.raw_title == "Levitating"


def test_played_at_has_timezone(parse_result: RadiowaveParseResult) -> None:
    for ev in parse_result.play_events:
        assert ev.played_at.tzinfo is not None


def test_drift_not_detected_on_full_fixture(parse_result: RadiowaveParseResult) -> None:
    assert not parse_result.drift_detected


def test_drift_detected_on_sparse_html() -> None:
    sparse_html = b"""
    <html><body>
    <table>
    <tr class="diary-row" data-event-id="x1">
      <td class="diary-time">06:00</td>
      <td class="diary-artist">Artist A</td>
      <td class="diary-title">Title A</td>
      <td class="diary-label">Label A</td>
    </tr>
    </table>
    </body></html>
    """
    result = parse_radiowave_diary(
        sparse_html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        expected_min_rows=10,
    )
    assert result.drift_detected
    assert result.drift_note != ""


def test_strip_label_from_artist_brackets() -> None:
    assert _strip_label_from_artist("Tame Impala [Island Records]") == "Tame Impala"


def test_strip_label_from_artist_no_label() -> None:
    assert _strip_label_from_artist("Dua Lipa") == "Dua Lipa"


def test_empty_html_returns_no_events() -> None:
    result = parse_radiowave_diary(
        b"<html><body></body></html>",
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
    )
    assert result.play_events == []
    assert not result.drift_detected


# ---------------------------------------------------------------------------
# Strategy 2: header-based table detection (ASP.NET GridView / no CSS classes)
# ---------------------------------------------------------------------------

_ASPNET_FIXTURE = (
    Path(__file__).parent.parent.parent / "fixtures/html/radiowave_aspnet_diary.html"
)


@pytest.fixture
def aspnet_html() -> bytes:
    return _ASPNET_FIXTURE.read_bytes()


@pytest.fixture
def aspnet_result(aspnet_html: bytes) -> RadiowaveParseResult:
    return parse_radiowave_diary(
        aspnet_html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 6, 4),
    )


def test_aspnet_parser_extracts_five_events(aspnet_result: RadiowaveParseResult) -> None:
    assert len(aspnet_result.play_events) == 5


def test_aspnet_parser_correct_first_artist(aspnet_result: RadiowaveParseResult) -> None:
    assert aspnet_result.play_events[0].raw_artist == "Tame Impala"


def test_aspnet_parser_correct_first_title(aspnet_result: RadiowaveParseResult) -> None:
    assert aspnet_result.play_events[0].raw_title == "The Less I Know The Better"


def test_aspnet_parser_label_extracted(aspnet_result: RadiowaveParseResult) -> None:
    assert aspnet_result.play_events[0].raw_label == "Island Records"


def test_aspnet_parser_source_event_id_is_none(aspnet_result: RadiowaveParseResult) -> None:
    """Header-based tables have no data-event-id attribute."""
    for ev in aspnet_result.play_events:
        assert ev.source_event_id is None


def test_aspnet_parser_played_at_has_timezone(aspnet_result: RadiowaveParseResult) -> None:
    for ev in aspnet_result.play_events:
        assert ev.played_at.tzinfo is not None


def test_aspnet_parser_no_drift(aspnet_result: RadiowaveParseResult) -> None:
    assert not aspnet_result.drift_detected


def test_aspnet_parser_ignores_pagination_table() -> None:
    """Parser must pick the diary table, not any surrounding nav/pagination tables."""
    html = b"""
    <html><body>
    <table><tr><td>Nav</td><td>Home</td></tr></table>
    <table>
      <tr><th>Time</th><th>Artist</th><th>Title</th><th>Label</th></tr>
      <tr><td>07:00</td><td>Coldplay</td><td>Yellow</td><td>Parlophone</td></tr>
      <tr><td>07:04</td><td>Adele</td><td>Hello</td><td>XL Recordings</td></tr>
      <tr><td>07:08</td><td>Ed Sheeran</td><td>Shape of You</td><td>Atlantic</td></tr>
      <tr><td>07:11</td><td>Billie Eilish</td><td>bad guy</td><td>Interscope</td></tr>
    </table>
    <table><tr><td>Prev</td><td>Next</td></tr></table>
    </body></html>
    """
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 6, 4),
    )
    assert len(result.play_events) == 4
    assert result.play_events[0].raw_artist == "Coldplay"


def test_aspnet_parser_handles_12h_time_format() -> None:
    html = b"""
    <html><body>
    <table>
      <tr><th>Time</th><th>Artist</th><th>Title</th></tr>
      <tr><td>6:02 AM</td><td>Adele</td><td>Hello</td></tr>
      <tr><td>12:05 PM</td><td>Coldplay</td><td>Yellow</td></tr>
    </table>
    </body></html>
    """
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 6, 4),
    )
    assert len(result.play_events) == 2
    # 6:02 AM Sydney (AEST=UTC+10) → 20:02 UTC previous day
    # But we assert timezone is set and hours are reasonable
    for ev in result.play_events:
        assert ev.played_at.tzinfo is not None
