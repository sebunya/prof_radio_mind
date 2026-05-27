"""Tests for ARIA chart HTML parser — no live network calls."""

from __future__ import annotations

from datetime import date

import pytest

from app.infrastructure.collectors.aria_chart import _parse_aria_html

_CHART_DATE = date(2026, 5, 24)


def _make_html(rows: list[tuple[int, str, str]]) -> str:
    """Build minimal ARIA chart HTML with chart-row class structure."""
    row_html = ""
    for pos, artist, title in rows:
        row_html += f"""
        <div class="chart-row">
            <span class="chart-row__position">{pos}</span>
            <span class="chart-row__artist">{artist}</span>
            <span class="chart-row__title">{title}</span>
        </div>
        """
    return f"<html><body>{row_html}</body></html>"


def test_parse_aria_html_returns_entries() -> None:
    html = _make_html([(1, "Taylor Swift", "Shake It Off"), (2, "The Weeknd", "Blinding Lights")])
    entries = _parse_aria_html(html, _CHART_DATE)
    assert len(entries) == 2


def test_parse_aria_html_positions_correct() -> None:
    html = _make_html([(3, "Adele", "Hello"), (7, "Ed Sheeran", "Shape of You")])
    entries = _parse_aria_html(html, _CHART_DATE)
    positions = {e.position for e in entries}
    assert 3 in positions
    assert 7 in positions


def test_parse_aria_html_sorted_by_position() -> None:
    html = _make_html([(5, "B", "T2"), (1, "A", "T1"), (3, "C", "T3")])
    entries = _parse_aria_html(html, _CHART_DATE)
    assert entries[0].position == 1
    assert entries[1].position == 3
    assert entries[2].position == 5


def test_parse_aria_html_chart_name() -> None:
    html = _make_html([(1, "A", "T")])
    entries = _parse_aria_html(html, _CHART_DATE)
    assert entries[0].chart_name == "ARIA Singles"


def test_parse_aria_html_chart_date_attached() -> None:
    html = _make_html([(1, "A", "T")])
    entries = _parse_aria_html(html, _CHART_DATE)
    assert entries[0].chart_date == _CHART_DATE


def test_parse_aria_html_no_entries_raises() -> None:
    html = "<html><body><p>Nothing here</p></body></html>"
    with pytest.raises(ValueError, match="selector"):
        _parse_aria_html(html, _CHART_DATE)


def test_parse_aria_html_optional_fields_none() -> None:
    html = _make_html([(1, "A", "T")])
    entries = _parse_aria_html(html, _CHART_DATE)
    assert entries[0].previous_position is None
    assert entries[0].peak_position is None
    assert entries[0].weeks_on_chart is None


def test_parse_aria_html_skips_rows_without_required_elements() -> None:
    incomplete_row = '<div class="chart-row"><span class="chart-row__position">1</span></div>'
    valid_row = _make_html([(2, "Valid", "Song")])[len("<html><body>"):-len("</body></html>")]
    html = f"<html><body>{incomplete_row}{valid_row}</body></html>"
    entries = _parse_aria_html(html, _CHART_DATE)
    assert len(entries) == 1
    assert entries[0].position == 2
