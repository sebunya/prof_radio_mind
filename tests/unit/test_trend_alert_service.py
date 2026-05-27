"""Unit tests for trend_alert_service.check_and_fire_trend_alerts.

All DB and webhook calls are mocked — no live network or database needed.

The service uses module-level imports, so each dependency is patched directly
on the service module:  patch("app.application.alerts.trend_alert_service.X").

Tests verify:
  - Edge-trigger logic for song.trending (fires on first threshold crossing)
  - song.trending does NOT refire when already above threshold last period
  - song.new_entry for brand-new songs with significant plays
  - song.new_entry does NOT fire below minimum play count
  - song.aria_match for charting songs with active airplay
  - Empty-plays edge case produces zero alerts
"""

from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_MODULE = "app.application.alerts.trend_alert_service"


# ── Test doubles ──────────────────────────────────────────────────────────────

def _play(artist: str, title: str) -> MagicMock:
    e = MagicMock()
    e.raw_artist = artist
    e.raw_title  = title
    return e


def _station(call_sign: str) -> MagicMock:
    s = MagicMock()
    s.id        = call_sign
    s.call_sign = call_sign
    return s


def _build_mocks(
    stations: list,
    cur_map:  dict[str, list],
    prev_map: dict[str, list],
) -> tuple:
    """Return (async session ctx, station_repo mock, play_repo mock).

    play_repo.list_for_station returns cur_map on the 1st call per station and
    prev_map on the 2nd — matching how check_and_fire_trend_alerts queries each
    station twice (current period then previous period).
    """
    session = AsyncMock()

    station_repo_mock = AsyncMock()
    station_repo_mock.list_active = AsyncMock(return_value=stations)

    call_count: dict[str, int] = {}

    async def _list_for_station(station_id, start, end):
        count = call_count.get(station_id, 0)
        call_count[station_id] = count + 1
        return (cur_map if count == 0 else prev_map).get(station_id, [])

    play_repo_mock = AsyncMock()
    play_repo_mock.list_for_station = _list_for_station

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__  = AsyncMock(return_value=False)

    return ctx, station_repo_mock, play_repo_mock


def _base_patches(stack: ExitStack, ctx, stn_repo, play_repo, fired: list) -> MagicMock:
    """Enter the standard set of patches and return the settings mock."""
    stack.enter_context(
        patch(f"{_MODULE}._get_factory", return_value=lambda: ctx)
    )
    stack.enter_context(
        patch(f"{_MODULE}.SQLStationRepository", return_value=stn_repo)
    )
    stack.enter_context(
        patch(f"{_MODULE}.SQLPlayEventRepository", return_value=play_repo)
    )

    async def _fire(ev, payload):
        fired.append((ev, payload))

    stack.enter_context(patch(f"{_MODULE}.fire_event", side_effect=_fire))
    ms = stack.enter_context(patch(f"{_MODULE}.settings"))
    ms.trend_plays_threshold = 50
    ms.trend_new_entry_plays = 10
    return ms


# ── song.trending ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_trending_fires_when_threshold_first_crossed() -> None:
    """song.trending fires when current >= threshold and previous < threshold."""
    stn  = _station("KIIS")
    cur  = [_play("Artist A", "Song X")] * 60   # 60 plays this week
    prev = [_play("Artist A", "Song X")] * 20   # 20 last week — threshold=50

    fired: list[tuple] = []
    ctx, sr, pr = _build_mocks([stn], {"KIIS": cur}, {"KIIS": prev})

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        summary = await check_and_fire_trend_alerts()

    trending = [f for f in fired if f[0] == "song.trending"]
    assert len(trending) == 1
    assert trending[0][1]["plays"]      == 60
    assert trending[0][1]["prev_plays"] == 20
    assert summary["trending_fired"]    == 1


@pytest.mark.anyio
async def test_trending_does_not_refire_when_already_above_threshold() -> None:
    """song.trending must NOT fire if the song was already above threshold last period."""
    stn  = _station("NOVA")
    cur  = [_play("Artist B", "Song Y")] * 80
    prev = [_play("Artist B", "Song Y")] * 60  # already >= 50 → no edge crossing

    fired: list[tuple] = []
    ctx, sr, pr = _build_mocks([stn], {"NOVA": cur}, {"NOVA": prev})

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        summary = await check_and_fire_trend_alerts()

    assert [f for f in fired if f[0] == "song.trending"] == []
    assert summary["trending_fired"] == 0


# ── song.new_entry ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_new_entry_fires_for_brand_new_song() -> None:
    """song.new_entry fires when a song first appears with >= new_entry_plays plays."""
    stn  = _station("CAPITAL")
    cur  = [_play("Artist C", "Debut Hit")] * 15
    prev: list = []  # brand new this week

    fired: list[tuple] = []
    ctx, sr, pr = _build_mocks([stn], {"CAPITAL": cur}, {"CAPITAL": prev})

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        summary = await check_and_fire_trend_alerts()

    new_entries = [f for f in fired if f[0] == "song.new_entry"]
    assert len(new_entries) == 1
    assert new_entries[0][1]["plays"] == 15
    assert summary["new_entry_fired"] == 1


@pytest.mark.anyio
async def test_new_entry_does_not_fire_below_threshold() -> None:
    """song.new_entry must NOT fire when play count is below the minimum."""
    stn  = _station("KIIS")
    cur  = [_play("Artist D", "Quiet Song")] * 3   # below threshold of 10
    prev: list = []

    fired: list[tuple] = []
    ctx, sr, pr = _build_mocks([stn], {"KIIS": cur}, {"KIIS": prev})

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        await check_and_fire_trend_alerts()

    assert [f for f in fired if f[0] == "song.new_entry"] == []


# ── song.aria_match ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_aria_match_fires_for_charting_songs() -> None:
    """song.aria_match fires for songs on the ARIA chart with active airplay."""
    stn  = _station("NOVA")
    cur  = [_play("Charting Artist", "Chart Song")] * 40
    prev: list = []

    fired: list[tuple] = []
    ctx, sr, pr = _build_mocks([stn], {"NOVA": cur}, {"NOVA": prev})

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        stack.enter_context(
            patch(
                f"{_MODULE}._get_current_aria_matches",
                return_value=[(1, "Charting Artist", "Chart Song")],
            )
        )
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        summary = await check_and_fire_trend_alerts()

    aria = [f for f in fired if f[0] == "song.aria_match"]
    assert len(aria) == 1
    assert aria[0][1]["aria_position"] == 1
    assert summary["aria_fired"] == 1


# ── edge: no plays ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_no_alerts_when_no_plays() -> None:
    """Summary shows zero alerts when there are no play events in either period."""
    stn = _station("NOVA")
    ctx, sr, pr = _build_mocks([stn], {}, {})
    fired: list = []

    with ExitStack() as stack:
        _base_patches(stack, ctx, sr, pr, fired)
        from app.application.alerts.trend_alert_service import check_and_fire_trend_alerts
        summary = await check_and_fire_trend_alerts()

    assert summary["total_fired"] == 0
    assert fired == []


# ── _get_current_aria_matches ─────────────────────────────────────────────────

def test_get_aria_matches_returns_empty_when_no_cache() -> None:
    """Returns an empty list gracefully when no chart data is available."""
    from app.application.alerts.trend_alert_service import _get_current_aria_matches

    counts: Counter[tuple[str, str]] = Counter({("X", "Y"): 5})
    with patch("app.api.routes.charts._chart_cache", {}):
        result = _get_current_aria_matches(counts)
    assert result == []


def test_get_aria_matches_case_insensitive() -> None:
    """ARIA matching must succeed regardless of artist/title case in play events."""
    from app.application.alerts.trend_alert_service import _get_current_aria_matches

    counts: Counter[tuple[str, str]] = Counter({("TAYLOR SWIFT", "ANTI-HERO"): 10})
    fake_cache = {
        ("ARIA", datetime(2025, 5, 1)): [
            {"position": 2, "artist": "Taylor Swift", "title": "Anti-Hero"},
        ]
    }
    with patch("app.api.routes.charts._chart_cache", fake_cache):
        result = _get_current_aria_matches(counts)
    assert len(result) == 1
    assert result[0][0] == 2   # chart position
