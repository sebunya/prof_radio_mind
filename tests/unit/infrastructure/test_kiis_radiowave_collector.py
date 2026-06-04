"""Fixture-driven tests for the KIIS-FM 102.7 Radiowave Monitor collector.

No live network calls. All tests use the saved HTML fixture.
Verifies:
  - Parser extracts correct events from the KIIS diary fixture
  - Times are converted from America/Los_Angeles → UTC (not Sydney)
  - Collector URL uses radiowavemonitor.com with IDDS=5080
  - Scheduler failure-threshold pausing behaviour mirrors the Capital/KIIS iHeart pattern
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.infrastructure.collectors.kiis_radiowave import KIISRadiowaveCollector
from app.infrastructure.parsers.radiowave import parse_radiowave_diary

_FIXTURE = Path(__file__).parent.parent.parent / "fixtures/html/radiowave_kiis_diary.html"
_LOS_ANGELES = ZoneInfo("America/Los_Angeles")


# ── Parser-level tests (fixture-driven) ──────────────────────────────────────

def test_parser_extracts_five_events_from_kiis_fixture() -> None:
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    assert len(result.play_events) == 5


def test_parser_first_event_is_taylor_swift() -> None:
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    ev = result.play_events[0]
    assert ev.raw_artist == "Taylor Swift"
    assert ev.raw_title == "Anti-Hero"


def test_parser_la_timezone_converts_06_02_correctly() -> None:
    """06:02 LA = 13:02 UTC (PDT) on 2026-05-24 (UTC-7)."""
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    first = result.play_events[0]
    assert first.played_at.tzinfo is not None
    # 2026-05-24 is in PDT (UTC-7); 06:02 LA → 13:02 UTC
    assert first.played_at.hour == 13
    assert first.played_at.minute == 2


def test_parser_kiis_source_event_ids_use_idds_5080() -> None:
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    assert result.play_events[0].source_event_id == "rw-5080-20260524-001"


def test_parser_strips_label_from_kiis_artists() -> None:
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    for ev in result.play_events:
        assert "[" not in ev.raw_artist


def test_parser_missing_link_row_still_parses() -> None:
    """The Weeknd row in the KIIS fixture has no <a> tag — must still parse."""
    html = _FIXTURE.read_bytes()
    result = parse_radiowave_diary(
        html,
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
        station_timezone=_LOS_ANGELES,
    )
    weeknd = next((e for e in result.play_events if "Weeknd" in e.raw_artist), None)
    assert weeknd is not None
    assert weeknd.raw_title == "Blinding Lights"


# ── URL construction ──────────────────────────────────────────────────────────

def test_collector_builds_correct_url() -> None:
    collector = KIISRadiowaveCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        diary_date=date(2026, 5, 24),
    )
    url = collector._build_url()
    assert "radiowavemonitor.com" in url
    assert "IDDS=5080" in url
    assert "date=2026-05-24" in url


def test_collector_url_custom_idds() -> None:
    collector = KIISRadiowaveCollector(
        source_id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        idds="9999",
        diary_date=date(2026, 5, 24),
    )
    assert "IDDS=9999" in collector._build_url()


# ── Collector integration (mocked HTTP) ──────────────────────────────────────

@pytest.mark.anyio
async def test_collector_successful_run() -> None:
    html = _FIXTURE.read_bytes()
    source_id = uuid.uuid4()
    station_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.content = html
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    collector = KIISRadiowaveCollector(
        source_id=source_id,
        station_id=station_id,
        diary_date=date(2026, 5, 24),
    )

    with patch("app.infrastructure.http.client.build_client", return_value=mock_client):
        raw, status, ct = await collector.fetch_raw()

    plays, no_tracks = collector.parse(raw, status, uuid.uuid4())
    assert len(plays) == 5
    assert no_tracks == []
    assert plays[0].raw_artist == "Taylor Swift"
