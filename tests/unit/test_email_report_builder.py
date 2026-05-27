"""Unit tests for email_report_builder period-bounds logic.

Rules under test
----------------
- daily   → rolling 1-day window  (yesterday 00:00 UTC → today 00:00 UTC)
- weekly  → rolling 7-day window  (T-7 00:00 UTC → T 00:00 UTC)
- monthly → rolling 30-day window (T-30 00:00 UTC → T 00:00 UTC)
- manual  → same as daily
- custom  → caller-supplied start/end (both UTC-aware)

Previous-period derivation
--------------------------
prev_end   = period_start
prev_start = period_start - (period_end - period_start)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.reports.email_report_builder import _period_bounds

# ── Helpers ───────────────────────────────────────────────────────────────────

def _today_midnight(now: datetime) -> datetime:
    """Return midnight UTC for the calendar day of *now*."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


# ── Test: daily / manual ──────────────────────────────────────────────────────

def test_daily_window_is_yesterday() -> None:
    now = datetime(2025, 5, 27, 14, 30, 0, tzinfo=UTC)
    start, end = _period_bounds("daily", now)
    today = _today_midnight(now)
    assert start == today - timedelta(days=1)
    assert end   == today


def test_manual_window_equals_daily() -> None:
    now = datetime(2025, 5, 27, 14, 30, 0, tzinfo=UTC)
    assert _period_bounds("manual", now) == _period_bounds("daily", now)


def test_daily_window_duration_is_exactly_24h() -> None:
    now = datetime(2025, 5, 27, 22, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("daily", now)
    assert (end - start) == timedelta(days=1)


# ── Test: weekly ──────────────────────────────────────────────────────────────

def test_weekly_window_is_rolling_7_days() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)  # Tuesday
    start, end = _period_bounds("weekly", now)
    today = _today_midnight(now)
    assert start == today - timedelta(days=7)
    assert end   == today


def test_weekly_window_duration_is_exactly_7_days() -> None:
    for day_offset in range(7):
        now = datetime(2025, 5, 26, 8, 0, 0, tzinfo=UTC) + timedelta(days=day_offset)
        start, end = _period_bounds("weekly", now)
        assert (end - start) == timedelta(days=7), f"Failed for now={now}"


def test_weekly_window_is_not_calendar_week() -> None:
    """Weekly must NOT depend on which day of the week it is."""
    # Monday vs Friday of the same week should produce windows of equal length
    # both ending at today's midnight UTC.
    monday  = datetime(2025, 5, 26, 8, 0, 0, tzinfo=UTC)
    friday  = datetime(2025, 5, 30, 8, 0, 0, tzinfo=UTC)
    s_mon, e_mon = _period_bounds("weekly", monday)
    s_fri, e_fri = _period_bounds("weekly", friday)
    # Both windows are 7 days; they just start on different calendar dates.
    assert (e_mon - s_mon) == timedelta(days=7)
    assert (e_fri - s_fri) == timedelta(days=7)
    # Friday's window is 4 days later than Monday's (as expected for a rolling window)
    assert s_fri == s_mon + timedelta(days=4)


# ── Test: monthly ─────────────────────────────────────────────────────────────

def test_monthly_window_is_rolling_30_days() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("monthly", now)
    today = _today_midnight(now)
    assert start == today - timedelta(days=30)
    assert end   == today


def test_monthly_window_duration_is_exactly_30_days() -> None:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("monthly", now)
    assert (end - start) == timedelta(days=30)


def test_monthly_window_crosses_month_boundary() -> None:
    """A 30-day window starting on the 15th of a month should cross the boundary."""
    now = datetime(2025, 5, 14, 10, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("monthly", now)
    # end is May 14 00:00, start is April 14 00:00
    assert start.month == 4
    assert end.month == 5


# ── Test: custom ──────────────────────────────────────────────────────────────

def test_custom_returns_caller_supplied_bounds() -> None:
    now    = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    cs     = datetime(2025, 5, 1, 0, 0, 0, tzinfo=UTC)
    ce     = datetime(2025, 5, 15, 0, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("custom", now, custom_start=cs, custom_end=ce)
    assert start == cs
    assert end   == ce


def test_custom_raises_when_dates_missing() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="custom"):
        _period_bounds("custom", now)


def test_custom_raises_when_start_missing() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    ce  = datetime(2025, 5, 15, 0, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="custom"):
        _period_bounds("custom", now, custom_end=ce)


def test_custom_raises_when_naive_datetime_supplied() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    cs  = datetime(2025, 5, 1, 0, 0, 0)   # naive — no tzinfo
    ce  = datetime(2025, 5, 15, 0, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="UTC-aware"):
        _period_bounds("custom", now, custom_start=cs, custom_end=ce)


# ── Test: previous-period derivation ─────────────────────────────────────────

def test_daily_prev_period_is_day_before_yesterday() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("daily", now)
    prev_end   = start
    prev_start = prev_end - (end - start)
    today = _today_midnight(now)
    # yesterday = today-1, day-before-yesterday = today-2
    assert prev_start == today - timedelta(days=2)
    assert prev_end   == today - timedelta(days=1)


def test_weekly_prev_period_is_mirror_of_current() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("weekly", now)
    prev_end   = start
    prev_start = prev_end - (end - start)
    today = _today_midnight(now)
    assert prev_start == today - timedelta(days=14)
    assert prev_end   == today - timedelta(days=7)


def test_monthly_prev_period_is_mirror_of_current() -> None:
    now = datetime(2025, 5, 27, 10, 0, 0, tzinfo=UTC)
    start, end = _period_bounds("monthly", now)
    prev_end   = start
    prev_start = prev_end - (end - start)
    today = _today_midnight(now)
    assert prev_start == today - timedelta(days=60)
    assert prev_end   == today - timedelta(days=30)
