"""Fixture-driven tests for the radio-australia.org weekly chart parser.

No live network calls. All tests use the saved HTML fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.infrastructure.parsers.radio_australia_org import (
    RadioAustraliaChartResult,
    parse_radio_australia_chart,
)

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/radio_australia_org_nova969.html"


@pytest.fixture
def fixture_html() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.fixture
def parse_results(fixture_html: bytes) -> list[RadioAustraliaChartResult]:
    return parse_radio_australia_chart(fixture_html)


def test_parser_extracts_five_chart_items(
    parse_results: list[RadioAustraliaChartResult],
) -> None:
    assert len(parse_results) == 5


def test_parser_correct_rank_one_title(parse_results: list[RadioAustraliaChartResult]) -> None:
    assert parse_results[0].title == "I Like That"


def test_parser_correct_rank_one_artist(parse_results: list[RadioAustraliaChartResult]) -> None:
    assert parse_results[0].artist == "Josh Fawaz"


def test_parser_correct_rank_numbers(parse_results: list[RadioAustraliaChartResult]) -> None:
    ranks = [r.rank for r in parse_results]
    assert ranks == [1, 2, 3, 4, 5]


def test_parser_correct_second_item(parse_results: list[RadioAustraliaChartResult]) -> None:
    assert parse_results[1].artist == "Tame Impala"
    assert parse_results[1].title == "Lucidity"


def test_collected_at_has_timezone(parse_results: list[RadioAustraliaChartResult]) -> None:
    for result in parse_results:
        assert result.collected_at.tzinfo is not None


def test_collected_at_accepts_override() -> None:
    fixture_html = _FIXTURE.read_bytes()
    fixed_time = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)
    results = parse_radio_australia_chart(fixture_html, collected_at=fixed_time)
    for r in results:
        assert r.collected_at == fixed_time


def test_weekly_chart_used_not_monthly(fixture_html: bytes) -> None:
    # Fixture has monthly chart with Tame Impala at rank 1.
    # Weekly chart has Josh Fawaz at rank 1.
    # Parser should use the weekly (data-period=7) chart.
    results = parse_radio_australia_chart(fixture_html)
    assert results[0].artist == "Josh Fawaz"


def test_http_error_returns_empty() -> None:
    result = parse_radio_australia_chart(b"<html/>", http_status=404)
    assert result == []


def test_http_503_returns_empty() -> None:
    result = parse_radio_australia_chart(b"<html/>", http_status=503)
    assert result == []


def test_empty_html_returns_empty() -> None:
    result = parse_radio_australia_chart(b"<html><body></body></html>")
    assert result == []


def test_no_chart_structure_returns_empty() -> None:
    html = b"""
    <html><body>
      <div class="latest-song"></div>
      <div class="previous-songs"></div>
    </body></html>
    """
    result = parse_radio_australia_chart(html)
    assert result == []


def test_missing_title_item_skipped() -> None:
    html = b"""
    <html><body>
    <div class="radio-songs__list" data-period="7">
      <ol>
        <li class="radio-songs__item">
          <span class="radio-songs__rank">1</span>
          <div class="radio-songs__details">
            <span class="radio-songs__artist">Test Artist</span>
          </div>
        </li>
        <li class="radio-songs__item">
          <span class="radio-songs__rank">2</span>
          <div class="radio-songs__details">
            <span class="radio-songs__title-text">Valid Title</span>
            <span class="radio-songs__artist">Valid Artist</span>
          </div>
        </li>
      </ol>
    </div>
    </body></html>
    """
    results = parse_radio_australia_chart(html)
    assert len(results) == 1
    assert results[0].title == "Valid Title"
    assert results[0].rank == 2
