"""Email report builder — produces rich HTML emails with per-station breakdowns
and music-intelligence insights for daily, weekly, and monthly recipients.

Architecture
------------
``build_report_data()``      aggregates raw play events from the DB into a
                              ``ReportData`` dataclass for the requested period.

``render_html_email()``      converts ``ReportData`` → HTML string suitable for
                              email clients (inline styles, no external CSS).

``send_frequency_report()``  orchestrates fetch → build → send for one frequency.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import logging
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.core.settings import settings

logger = logging.getLogger(__name__)

Frequency = Literal["daily", "weekly", "monthly", "manual", "custom"]

# ── Palette (inline-safe hex values for email clients) ─────────────────────────
_C = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "border": "#334155",
    "accent": "#0ea5e9",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text1": "#f1f5f9",
    "text2": "#94a3b8",
    "text3": "#64748b",
    "gold": "#fbbf24",
    "silver": "#9ca3af",
    "bronze": "#92400e",
}


# ── Data structures ─────────────────────────────────────────────────────────────

@dataclass
class SongStat:
    artist: str
    title: str
    plays: int
    stations: list[str]
    is_new: bool = False   # True = first appearance in the period window


@dataclass
class StationStats:
    station_id: uuid.UUID
    call_sign: str
    name: str
    total_plays: int
    top_songs: list[SongStat]
    top_artists: list[tuple[str, int]]     # [(artist_name, play_count)]
    new_songs: int                          # songs played for the first time


@dataclass
class ReportData:
    frequency: Frequency
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    total_plays: int
    unique_songs: int
    unique_artists: int
    top_songs: list[SongStat]             # cross-station top 10
    top_artists: list[tuple[str, int]]    # cross-station top 5
    new_song_count: int                   # songs not seen in prior period
    rising: list[SongStat]               # gained >= 50 % more plays vs prior period
    falling: list[SongStat]              # lost >= 50 % plays vs prior period
    stations: list[StationStats]
    aria_hits: list[tuple[int, str, str]]  # [(position, artist, title)] for songs in ARIA
    stats_snapshot: dict                   # simple dict for DB storage


# ── Data aggregation ────────────────────────────────────────────────────────────

async def build_report_data(
    frequency: Frequency,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None,
) -> ReportData:
    """Query the DB and produce a ``ReportData`` for the given frequency.

    Parameters
    ----------
    frequency:
        One of ``daily``, ``weekly``, ``monthly``, ``manual``, or ``custom``.
    custom_start / custom_end:
        Required when *frequency* is ``"custom"``; ignored otherwise.
        Both must be timezone-aware UTC datetimes.
    """
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository
    from app.infrastructure.database.session import _get_factory

    now = datetime.now(UTC)
    period_start, period_end = _period_bounds(frequency, now, custom_start, custom_end)

    # Previous period: mirror of the current window shifted back by the same duration.
    # e.g. daily → day-before-yesterday; weekly → 14–7 days ago; monthly → 60–30 days ago.
    period_delta = period_end - period_start
    prev_end     = period_start
    prev_start   = prev_end - period_delta

    async with _get_factory()() as session:
        station_repo = SQLStationRepository(session)
        play_repo    = SQLPlayEventRepository(session)

        stations = await station_repo.list_active()

        # Gather events for current + previous period (for trend analysis)
        all_current: list[tuple] = []   # (artist, title, station_call_sign, station_id)
        all_previous: list[tuple] = []

        station_stats: list[StationStats] = []

        for stn in stations:
            cur_events  = await play_repo.list_for_station(stn.id, period_start, period_end)
            prev_events = await play_repo.list_for_station(stn.id, prev_start, prev_end)

            # Per-station aggregation
            cur_counts: Counter = Counter(
                (e.raw_artist, e.raw_title) for e in cur_events
            )
            prev_counts: Counter = Counter(
                (e.raw_artist, e.raw_title) for e in prev_events
            )
            artist_counts: Counter = Counter(e.raw_artist for e in cur_events)

            prev_songs = set(prev_counts.keys())
            cur_songs  = set(cur_counts.keys())
            new_songs  = cur_songs - prev_songs

            top_songs_stn = [
                SongStat(
                    artist=a, title=t, plays=c,
                    stations=[stn.call_sign],
                    is_new=(a, t) in new_songs,
                )
                for (a, t), c in cur_counts.most_common(5)
            ]
            top_artists_stn = artist_counts.most_common(3)

            station_stats.append(StationStats(
                station_id=stn.id,
                call_sign=stn.call_sign,
                name=stn.name,
                total_plays=len(cur_events),
                top_songs=top_songs_stn,
                top_artists=top_artists_stn,
                new_songs=len(new_songs),
            ))

            for e in cur_events:
                all_current.append((e.raw_artist, e.raw_title, stn.call_sign, stn.id))
            for e in prev_events:
                all_previous.append((e.raw_artist, e.raw_title, stn.call_sign, stn.id))

    # ── Cross-station aggregation ──────────────────────────────────────────
    cur_total: Counter = Counter((a, t) for a, t, _, _ in all_current)
    prev_total: Counter = Counter((a, t) for a, t, _, _ in all_previous)

    song_stations: dict[tuple, set] = defaultdict(set)
    for a, t, call_sign, _ in all_current:
        song_stations[(a, t)].add(call_sign)

    prev_songs_global = set(prev_total.keys())
    cur_songs_global  = set(cur_total.keys())

    top_10 = [
        SongStat(
            artist=a, title=t, plays=c,
            stations=sorted(song_stations[(a, t)]),
            is_new=(a, t) not in prev_songs_global,
        )
        for (a, t), c in cur_total.most_common(10)
    ]

    artist_total: Counter = Counter(a for a, _, _, _ in all_current)
    top_5_artists = artist_total.most_common(5)

    new_song_count = len(cur_songs_global - prev_songs_global)

    # Rising: current > 0, previous > 0, ratio >= 1.5
    rising = [
        SongStat(artist=a, title=t, plays=c, stations=sorted(song_stations[(a, t)]))
        for (a, t), c in cur_total.most_common(20)
        if prev_total.get((a, t), 0) > 0
        and c / prev_total[(a, t)] >= 1.5
    ][:5]

    # Falling: previous > 0, current < 50% of previous, at least 2 prev plays
    falling = [
        SongStat(artist=a, title=t, plays=cur_total.get((a, t), 0), stations=[])
        for (a, t), p in prev_total.most_common(20)
        if p >= 2 and cur_total.get((a, t), 0) < p * 0.5
    ][:5]

    # ── ARIA chart matches ─────────────────────────────────────────────────
    aria_hits = _find_aria_hits(cur_total)

    stats_snapshot = {
        "total_plays": len(all_current),
        "unique_songs": len(cur_songs_global),
        "unique_artists": len(set(a for a, _ in cur_songs_global)),
        "new_songs": new_song_count,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
    }

    return ReportData(
        frequency=frequency,
        period_start=period_start,
        period_end=period_end,
        generated_at=datetime.now(UTC),
        total_plays=len(all_current),
        unique_songs=len(cur_songs_global),
        unique_artists=len(set(a for a, _ in cur_songs_global)),
        top_songs=top_10,
        top_artists=top_5_artists,
        new_song_count=new_song_count,
        rising=rising,
        falling=falling,
        stations=station_stats,
        aria_hits=aria_hits,
        stats_snapshot=stats_snapshot,
    )


def _period_bounds(
    frequency: Frequency,
    now: datetime,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return ``(start, end)`` UTC datetimes that define the report window.

    Period definitions (all windows end at today's UTC midnight so every day
    counted is a *complete* 24-hour day):

    +-----------+----------------------------------------------------------+
    | Frequency | Window                                                   |
    +===========+==========================================================+
    | daily     | Yesterday: 1-day window  (T-1 00:00 → T 00:00 UTC)      |
    | weekly    | Rolling 7-day window     (T-7 00:00 → T 00:00 UTC)      |
    | monthly   | Rolling 30-day window    (T-30 00:00 → T 00:00 UTC)     |
    | manual    | Same as daily (on-demand trigger)                        |
    | custom    | Caller-supplied start / end (both must be UTC-aware)     |
    +-----------+----------------------------------------------------------+

    Using rolling windows (rather than calendar Mon–Sun or calendar months)
    ensures the window is always a predictable, fixed number of complete days
    regardless of when in the week or month the job runs.
    """
    if frequency == "custom":
        if custom_start is None or custom_end is None:
            raise ValueError(
                "frequency='custom' requires both custom_start and custom_end"
            )
        if custom_start.tzinfo is None or custom_end.tzinfo is None:
            raise ValueError("custom_start and custom_end must be UTC-aware datetimes")
        return custom_start, custom_end

    # Anchor: today's midnight UTC — the last complete day ends here.
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if frequency in ("daily", "manual"):
        # 1-day rolling window: yesterday (T-1 → T)
        return today - timedelta(days=1), today
    elif frequency == "weekly":
        # 7-day rolling window: T-7 → T
        return today - timedelta(days=7), today
    else:  # monthly
        # 30-day rolling window: T-30 → T
        return today - timedelta(days=30), today


def _find_aria_hits(
    song_counts: Counter,
) -> list[tuple[int, str, str]]:
    """Return list of (aria_position, artist, title) for songs in the ARIA cache."""
    try:
        from app.api.routes.charts import _chart_cache
        if not _chart_cache:
            return []
        latest_key = max(_chart_cache.keys(), key=lambda k: k[1])
        chart_entries = _chart_cache[latest_key]
        # Build normalised lookup: (lower_artist, lower_title) → position
        aria_map = {
            (e["artist"].lower(), e["title"].lower()): e["position"]
            for e in chart_entries
        }
        hits = []
        for (artist, title) in song_counts:
            pos = aria_map.get((artist.lower(), title.lower()))
            if pos is not None:
                hits.append((pos, artist, title))
        hits.sort(key=lambda x: x[0])
        return hits[:10]
    except Exception:
        return []


# ── HTML email renderer ─────────────────────────────────────────────────────────

_FREQ_LABEL = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "manual": "On-Demand",
    "custom": "Custom Range",
}


# ── Unsubscribe token helpers ───────────────────────────────────────────────────

def _unsubscribe_token(recipient_id: uuid.UUID, email: str) -> str:
    """Return a URL-safe HMAC-SHA256 token for the given recipient.

    Signed with ``settings.api_key`` (or a static fallback when auth is
    disabled).  The token binds both ``recipient_id`` and ``email`` so it
    cannot be reused across accounts even if an ID leaks.
    """
    secret = (settings.api_key or "rmias-unsub-fallback").encode()
    message = f"{recipient_id}:{email}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_unsubscribe_token(token: str, recipient_id: uuid.UUID, email: str) -> bool:
    """Constant-time comparison to verify an unsubscribe token."""
    expected = _unsubscribe_token(recipient_id, email)
    return hmac.compare_digest(token, expected)


def build_unsubscribe_url(recipient_id: uuid.UUID, email: str) -> str:
    """Return the absolute unsubscribe URL, or an empty string if BASE_URL is unset."""
    if not settings.base_url:
        return ""
    token = _unsubscribe_token(recipient_id, email)
    base = settings.base_url.rstrip("/")
    return f"{base}/email-reports/unsubscribe?id={recipient_id}&token={token}"

_PERIOD_FMT = {
    "daily": "%A, %-d %B %Y",
    "weekly": "%-d %b – ",
    "monthly": "%B %Y",
    "manual": "%-d %b %Y",
}


def render_html_email(
    data: ReportData,
    recipient_name: str = "",
    unsubscribe_url: str = "",
) -> str:
    """Convert a ``ReportData`` into a production-quality HTML email string.

    Parameters
    ----------
    unsubscribe_url:
        Absolute URL for the one-click unsubscribe link placed in the footer
        and the ``List-Unsubscribe`` header.  Pass an empty string to omit.
    """
    freq_label = _FREQ_LABEL.get(data.frequency, data.frequency.title())
    period_str = _format_period(data)
    greeting   = f"Hi {html.escape(recipient_name)}," if recipient_name else "Hello,"

    stations_html = "".join(_render_station(s) for s in data.stations)
    top_songs_html = _render_top_songs(data.top_songs)
    top_artists_html = _render_top_artists(data.top_artists)
    insights_html = _render_insights(data)
    aria_html = _render_aria_hits(data.aria_hits)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RMIAS {freq_label} Report — {period_str}</title>
</head>
<body style="margin:0;padding:0;background-color:#0f172a;font-family:sans-serif">

<!-- ── Outer wrapper ── -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#0f172a;min-height:100vh">
<tr><td align="center" style="padding:32px 16px">

<!-- ── Content card (max-width 600px) ── -->
<table width="600" cellpadding="0" cellspacing="0" border="0"
       style="width:600px;max-width:100%">

  <!-- HEADER -->
  <tr>
    <td style="background:#1e293b;border-radius:12px 12px 0 0;
               padding:28px 32px;border-bottom:1px solid #334155">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td>
            <span style="font-size:28px">📻</span>
            <span style="font-size:20px;font-weight:700;color:#f1f5f9;
                         margin-left:10px;vertical-align:middle">RMIAS</span>
            <span style="font-size:13px;color:#64748b;
                         margin-left:8px;vertical-align:middle">Radio Reports</span>
          </td>
          <td align="right">
            <span style="background:#0ea5e9;color:#fff;font-size:11px;
                         font-weight:600;padding:4px 10px;border-radius:20px;
                         text-transform:uppercase;letter-spacing:.5px">
              {html.escape(freq_label)}
            </span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- HERO -->
  <tr>
    <td style="background:#1e293b;padding:24px 32px 20px">
      <p style="margin:0 0 4px;font-size:13px;color:#64748b">{greeting}</p>
      <h1 style="margin:0 0 6px;font-size:22px;font-weight:700;color:#f1f5f9">
        {html.escape(freq_label)} Music Report
      </h1>
      <p style="margin:0;font-size:14px;color:#94a3b8">{html.escape(period_str)}</p>
    </td>
  </tr>

  <!-- KPI ROW -->
  <tr>
    <td style="background:#1e293b;padding:0 32px 24px">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          {_kpi_cell("🎵", f"{data.total_plays:,}", "Total Plays")}
          {_kpi_cell("🎤", f"{data.unique_songs:,}", "Unique Songs")}
          {_kpi_cell("👤", f"{data.unique_artists:,}", "Artists")}
          {_kpi_cell("✨", f"{data.new_song_count:,}", "New Songs")}
        </tr>
      </table>
    </td>
  </tr>

  <tr><td style="height:2px;background:#334155"></td></tr>

  <!-- STATION BREAKDOWN -->
  <tr>
    <td style="background:#1e293b;padding:24px 32px 8px">
      <h2 style="margin:0 0 16px;font-size:16px;font-weight:600;color:#f1f5f9">
        📡 Station Breakdown
      </h2>
      {stations_html}
    </td>
  </tr>

  <tr><td style="height:2px;background:#334155"></td></tr>

  <!-- TOP SONGS (cross-station) -->
  <tr>
    <td style="background:#1e293b;padding:24px 32px 8px">
      <h2 style="margin:0 0 16px;font-size:16px;font-weight:600;color:#f1f5f9">
        🏆 Top Songs This {html.escape(freq_label.rstrip('ly').title())}
      </h2>
      {top_songs_html}
    </td>
  </tr>

  <!-- TOP ARTISTS -->
  <tr>
    <td style="background:#1e293b;padding:8px 32px 20px">
      <h2 style="margin:0 0 12px;font-size:16px;font-weight:600;color:#f1f5f9">
        🎤 Most-Played Artists
      </h2>
      {top_artists_html}
    </td>
  </tr>

  <tr><td style="height:2px;background:#334155"></td></tr>

  <!-- MUSIC INSIGHTS -->
  <tr>
    <td style="background:#1e293b;padding:24px 32px 20px">
      <h2 style="margin:0 0 12px;font-size:16px;font-weight:600;color:#f1f5f9">
        📈 Music Intelligence Insights
      </h2>
      {insights_html}
    </td>
  </tr>

  <!-- ARIA CHART MATCHES (only if available) -->
  {_aria_section(aria_html, data.aria_hits)}

  <!-- FOOTER -->
  <tr>
    <td style="background:#0f172a;border-radius:0 0 12px 12px;
               padding:20px 32px;border-top:1px solid #334155;text-align:center">
      <p style="margin:0 0 6px;font-size:11px;color:#475569">
        Generated by RMIAS · Radio Music Intelligence &amp; Automation System
      </p>
      <p style="margin:0 0 6px;font-size:11px;color:#334155">
        {html.escape(data.generated_at.strftime("%Y-%m-%d %H:%M UTC"))}
      </p>
      {_unsubscribe_footer_html(unsubscribe_url)}
    </td>
  </tr>

</table>
<!-- /content card -->

</td></tr>
</table>
<!-- /outer -->

</body>
</html>"""


# ── HTML building blocks ────────────────────────────────────────────────────────

def _unsubscribe_footer_html(unsubscribe_url: str) -> str:
    if not unsubscribe_url:
        return (
            '<p style="margin:0;font-size:11px;color:#334155">'
            'To update your preferences, contact your RMIAS administrator.</p>'
        )
    safe = html.escape(unsubscribe_url)
    return (
        f'<p style="margin:0;font-size:11px;color:#334155">'
        f'<a href="{safe}" style="color:#475569;text-decoration:underline">'
        f'Unsubscribe</a>'
        f' &nbsp;·&nbsp; To update your preferences, contact your RMIAS administrator.'
        f'</p>'
    )


def _aria_section(aria_html: str, hits: list) -> str:
    """Conditionally render the ARIA chart section."""
    if not hits:
        return ""
    sep  = '<tr><td style="height:2px;background:#334155"></td></tr>'
    body = (
        '<tr><td style="background:#1e293b;padding:24px 32px 20px">'
        '<h2 style="margin:0 0 12px;font-size:16px;font-weight:600;color:#f1f5f9">'
        f"\U0001f947 ARIA Chart Matches</h2>{aria_html}</td></tr>"
    )
    return sep + body


def _kpi_cell(icon: str, value: str, label: str) -> str:
    return f"""
      <td width="25%" style="text-align:center;padding:12px 8px;
                              background:#0f172a;border-radius:8px;margin:4px">
        <div style="font-size:20px;margin-bottom:4px">{icon}</div>
        <div style="font-size:22px;font-weight:700;color:#0ea5e9">{html.escape(value)}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px">{html.escape(label)}</div>
      </td>"""


def _render_station(s: StationStats) -> str:
    if not s.total_plays:
        plays_block = (
            '<p style="margin:0;font-size:12px;color:#475569;font-style:italic">'
            'No plays recorded this period.</p>'
        )
    else:
        plays_block = "".join(
            f'<tr>'
            f'<td style="padding:4px 0;font-size:13px;color:#94a3b8;width:24px">'
            f'{"🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"}</td>'
            f'<td style="padding:4px 8px;font-size:13px;color:#f1f5f9">'
            f'{html.escape(song.artist)}</td>'
            f'<td style="padding:4px 0;font-size:12px;color:#94a3b8">'
            f'{html.escape(song.title)}</td>'
            f'<td style="padding:4px 0 4px 8px;font-size:12px;color:#0ea5e9;'
            f'text-align:right">{song.plays}×</td>'
            f'</tr>'
            for i, song in enumerate(s.top_songs)
        )
        plays_block = (
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
            f'{plays_block}</table>'
        )

    new_badge = (
        f' <span style="background:#10b981;color:#fff;font-size:10px;'
        f'padding:2px 6px;border-radius:10px;font-weight:600">'
        f'{s.new_songs} new</span>'
    ) if s.new_songs else ""

    return f"""
    <div style="background:#0f172a;border-radius:8px;padding:14px 16px;
                margin-bottom:12px;border-left:3px solid #0ea5e9">
      <div style="font-weight:700;font-size:14px;color:#f1f5f9;margin-bottom:2px">
        {html.escape(s.call_sign)}
        <span style="font-size:12px;font-weight:400;color:#64748b;margin-left:6px">
          {html.escape(s.name)}</span>
        {new_badge}
      </div>
      <div style="font-size:12px;color:#64748b;margin-bottom:10px">
        {s.total_plays:,} plays this period
      </div>
      {plays_block}
    </div>"""


def _render_top_songs(songs: list[SongStat]) -> str:
    if not songs:
        return '<p style="font-size:13px;color:#475569;font-style:italic">No plays recorded.</p>'
    rows = ""
    for i, s in enumerate(songs):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
        new_tag = (
            '<span style="background:#10b981;color:#fff;font-size:10px;'
            'padding:1px 5px;border-radius:8px;margin-left:6px">NEW</span>'
        ) if s.is_new else ""
        stations = ", ".join(s.stations) if s.stations else ""
        rows += f"""
        <tr style="border-bottom:1px solid #1e293b">
          <td style="padding:10px 8px 10px 0;font-size:14px;color:#94a3b8;width:36px;
                     font-weight:600">{medal}</td>
          <td style="padding:10px 8px">
            <div style="font-size:13px;font-weight:600;color:#f1f5f9">
              {html.escape(s.artist)}{new_tag}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:2px">
              {html.escape(s.title)}</div>
            <div style="font-size:11px;color:#475569;margin-top:2px">{html.escape(stations)}</div>
          </td>
          <td style="padding:10px 0;font-size:14px;font-weight:700;color:#0ea5e9;
                     text-align:right;white-space:nowrap">{s.plays:,} plays</td>
        </tr>"""
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<thead><tr>'
        f'<th style="padding:6px 0;font-size:11px;color:#475569;text-align:left;'
        f'font-weight:500;text-transform:uppercase;letter-spacing:.5px" colspan="3">'
        f'Cross-station rankings</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def _render_top_artists(artists: list[tuple[str, int]]) -> str:
    if not artists:
        return ""
    items = "".join(
        f'<td style="padding:0 6px;text-align:center">'
        f'<div style="background:#0f172a;border-radius:8px;padding:10px 12px">'
        f'<div style="font-size:12px;font-weight:600;color:#f1f5f9">{html.escape(name)}</div>'
        f'<div style="font-size:11px;color:#0ea5e9;margin-top:4px">{count} plays</div>'
        f'</div></td>'
        for name, count in artists
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr>{items}</tr></table>'
    )


def _render_insights(data: ReportData) -> str:
    blocks = []

    # Rising tracks
    if data.rising:
        items = "".join(
            f'<div style="padding:6px 0;border-bottom:1px solid #0f172a">'
            f'<span style="color:#10b981;font-size:12px">↑ Gaining</span> '
            f'<span style="font-size:13px;color:#f1f5f9;font-weight:600">'
            f'{html.escape(s.artist)}</span> '
            f'<span style="font-size:12px;color:#94a3b8">— {html.escape(s.title)}</span> '
            f'<span style="font-size:12px;color:#0ea5e9">{s.plays} plays</span>'
            f'</div>'
            for s in data.rising
        )
        blocks.append(
            f'<div style="background:#0f172a;border-radius:8px;padding:12px 14px;'
            f'margin-bottom:10px">'
            f'<div style="font-size:12px;font-weight:600;color:#10b981;margin-bottom:8px">'
            f'🚀 Rising Tracks (50%+ increase vs prior period)</div>'
            f'{items}</div>'
        )

    # Falling tracks
    if data.falling:
        items = "".join(
            f'<div style="padding:6px 0;border-bottom:1px solid #0f172a">'
            f'<span style="color:#ef4444;font-size:12px">↓ Dropping</span> '
            f'<span style="font-size:13px;color:#f1f5f9;font-weight:600">'
            f'{html.escape(s.artist)}</span> '
            f'<span style="font-size:12px;color:#94a3b8">— {html.escape(s.title)}</span>'
            f'</div>'
            for s in data.falling
        )
        blocks.append(
            f'<div style="background:#0f172a;border-radius:8px;padding:12px 14px;'
            f'margin-bottom:10px">'
            f'<div style="font-size:12px;font-weight:600;color:#ef4444;margin-bottom:8px">'
            f'📉 Falling Tracks (50%+ drop vs prior period)</div>'
            f'{items}</div>'
        )

    # New songs debut
    if data.new_song_count:
        new_debuts = [s for s in data.top_songs if s.is_new][:5]
        if new_debuts:
            items = "".join(
                f'<div style="padding:5px 0">'
                f'<span style="font-size:13px;color:#f1f5f9;font-weight:600">'
                f'{html.escape(s.artist)}</span> '
                f'<span style="font-size:12px;color:#94a3b8">— {html.escape(s.title)}</span>'
                f'</div>'
                for s in new_debuts
            )
            blocks.append(
                f'<div style="background:#0f172a;border-radius:8px;padding:12px 14px;'
                f'margin-bottom:10px">'
                f'<div style="font-size:12px;font-weight:600;color:#fbbf24;margin-bottom:8px">'
                f'✨ New Song Debuts ({data.new_song_count} total first plays this period)</div>'
                f'{items}</div>'
            )

    if not blocks:
        return (
            '<p style="font-size:13px;color:#475569;font-style:italic">'
            'Not enough data for trend comparison yet. Insights will appear once '
            'two consecutive periods have been collected.</p>'
        )
    return "".join(blocks)


def _render_aria_hits(hits: list[tuple[int, str, str]]) -> str:
    if not hits:
        return ""
    rows = "".join(
        f'<tr style="border-bottom:1px solid #0f172a">'
        f'<td style="padding:8px 12px 8px 0;font-size:13px;color:#fbbf24;'
        f'font-weight:700;width:40px">#{pos}</td>'
        f'<td style="padding:8px 8px"><span style="font-size:13px;font-weight:600;'
        f'color:#f1f5f9">{html.escape(artist)}</span></td>'
        f'<td style="padding:8px 0;font-size:12px;color:#94a3b8">{html.escape(title)}</td>'
        f'</tr>'
        for pos, artist, title in hits
    )
    return (
        f'<p style="margin:0 0 10px;font-size:12px;color:#64748b">'
        f'Songs on the ARIA Singles chart that received airplay this period:</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tbody style="background:#0f172a;border-radius:8px">{rows}</tbody></table>'
    )


def _format_period(data: ReportData) -> str:
    freq = data.frequency
    s, e = data.period_start, data.period_end - timedelta(seconds=1)
    if freq == "daily":
        return s.strftime("%A, %-d %B %Y")
    elif freq in ("weekly", "custom", "manual"):
        # Show the inclusive date range: e.g. "20 May – 26 May 2025"
        return f"{s.strftime('%-d %b')} – {e.strftime('%-d %b %Y')}"
    elif freq == "monthly":
        # Show the inclusive range for clarity: e.g. "27 Apr – 26 May 2025"
        return f"{s.strftime('%-d %b')} – {e.strftime('%-d %b %Y')}"
    else:
        return f"{s.strftime('%-d %b')} – {e.strftime('%-d %b %Y')}"


def render_text_email(
    data: ReportData,
    recipient_name: str = "",
    unsubscribe_url: str = "",
) -> str:
    """Produce a plain-text version of the report for multipart/alternative emails.

    Plain-text is required by major spam filters (SpamAssassin, Gmail, etc.) and
    ensures the email renders legibly in accessibility tools and terminal clients.
    """
    freq_label = _FREQ_LABEL.get(data.frequency, data.frequency.title())
    period_str = _format_period(data)
    greeting   = f"Hi {recipient_name}," if recipient_name else "Hello,"
    sep        = "─" * 54

    lines: list[str] = [
        f"RMIAS {freq_label} Report — {period_str}",
        "=" * 54,
        "",
        greeting,
        "",
        f"  TOTAL PLAYS   {data.total_plays:>6,}",
        f"  UNIQUE SONGS  {data.unique_songs:>6,}",
        f"  ARTISTS       {data.unique_artists:>6,}",
        f"  NEW THIS PERIOD {data.new_song_count:>4,}",
        "",
    ]

    # Per-station breakdown
    for stn in data.stations:
        lines.append(sep)
        lines.append(f"  {stn.call_sign}  —  {stn.name}")
        lines.append(f"  {stn.total_plays:,} plays  ·  {stn.new_songs} new songs")
        for i, s in enumerate(stn.top_songs, 1):
            new_tag = " [NEW]" if s.is_new else ""
            lines.append(f"    {i}. {s.artist} — {s.title} ({s.plays}×){new_tag}")
        lines.append("")

    # Top 10 cross-station
    if data.top_songs:
        lines += [sep, "  TOP SONGS (cross-station)", ""]
        for i, s in enumerate(data.top_songs, 1):
            new_tag = " [NEW]" if s.is_new else ""
            stations = ", ".join(s.stations) if s.stations else ""
            lines.append(f"  {i:>2}. {s.artist} — {s.title} ({s.plays:,}×){new_tag}")
            if stations:
                lines.append(f"      {stations}")
        lines.append("")

    # Insights
    if data.rising or data.falling or data.new_song_count:
        lines += [sep, "  MUSIC INTELLIGENCE INSIGHTS", ""]
        for s in data.rising:
            lines.append(f"  ↑ RISING   {s.artist} — {s.title} ({s.plays}×)")
        for s in data.falling:
            lines.append(f"  ↓ FALLING  {s.artist} — {s.title} ({s.plays}×)")
        new_debuts = [s for s in data.top_songs if s.is_new][:5]
        for s in new_debuts:
            lines.append(f"  ✦ DEBUT    {s.artist} — {s.title}")
        lines.append("")

    # ARIA chart matches
    if data.aria_hits:
        lines += [sep, "  ARIA CHART MATCHES", ""]
        for pos, artist, title in data.aria_hits:
            lines.append(f"  #{pos:<3}  {artist} — {title}")
        lines.append("")

    # Footer
    lines += [
        sep,
        f"Generated by RMIAS · {data.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "Radio Music Intelligence & Automation System",
    ]
    if unsubscribe_url:
        lines += ["", f"To unsubscribe: {unsubscribe_url}"]

    return "\n".join(lines)


# ── Orchestrator ────────────────────────────────────────────────────────────────

async def send_frequency_report(
    frequency: Frequency,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None,
) -> dict:
    """Build the report, send to all subscribed recipients, log the result.

    Parameters
    ----------
    frequency:
        Scheduled cadence or ``"custom"`` for an ad-hoc date range.
    custom_start / custom_end:
        Required when *frequency* is ``"custom"``.

    Returns a stats dict for the caller to log / forward.
    """
    from app.infrastructure.database.models.notifications import EmailSendLogDB
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
        SQLEmailSendLogRepository,
    )
    from app.infrastructure.database.session import _get_factory
    from app.infrastructure.email.sender import EmailSendError, build_sender

    logger.info("email_report_start frequency=%s", frequency)

    try:
        data = await build_report_data(frequency, custom_start, custom_end)
    except Exception as exc:
        logger.error("email_report_build_failed frequency=%s error=%s", frequency, exc)
        return {"status": "failed", "error": str(exc)}

    # Fetch recipients.
    # Custom sends go to every active recipient; scheduled sends respect the
    # per-recipient frequency subscription so people only get what they signed
    # up for.
    async with _get_factory()() as session:
        repo = SQLEmailRecipientRepository(session)
        if frequency == "custom":
            recipients = await repo.list_active()
        else:
            recipients = await repo.list_for_frequency(frequency)

    if not recipients:
        logger.info("email_report_no_recipients frequency=%s", frequency)
        return {"status": "no_recipients", "total_plays": data.total_plays}

    sender = build_sender()
    freq_label = _FREQ_LABEL.get(frequency, frequency.title())
    period_str = _format_period(data)
    subject    = f"RMIAS {freq_label} Report — {period_str}"

    errors: list[str] = []
    sent_to: list[str] = []

    for rec in recipients:
        try:
            unsub_url = build_unsubscribe_url(rec.id, rec.email)
            html_body = render_html_email(data, recipient_name=rec.name, unsubscribe_url=unsub_url)
            text_body = render_text_email(data, recipient_name=rec.name, unsubscribe_url=unsub_url)
            extra_headers: dict[str, str] = {}
            if unsub_url:
                extra_headers["List-Unsubscribe"] = f"<{unsub_url}>"
                extra_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            await sender.send(
                to_addresses=[f"{rec.name} <{rec.email}>"],
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                extra_headers=extra_headers,
            )
            sent_to.append(rec.email)
        except EmailSendError as exc:
            logger.error("email_send_failed to=%s error=%s", rec.email, exc)
            errors.append(f"{rec.email}: {exc}")
        except Exception as exc:
            logger.error("email_render_failed to=%s error=%s", rec.email, exc, exc_info=True)
            errors.append(f"{rec.email}: {exc}")

    # Write audit log
    status = "dry_run" if sender.is_dry_run else ("failed" if not sent_to else "sent")
    async with _get_factory()() as session:
        log_repo = SQLEmailSendLogRepository(session)
        all_addrs = ", ".join(sent_to) if sent_to else ", ".join(r.email for r in recipients)
        log_row = EmailSendLogDB(
            frequency=frequency,
            recipients=all_addrs,
            subject=subject,
            status=status,
            error_message="; ".join(errors) if errors else None,
            stats_snapshot=data.stats_snapshot,
        )
        await log_repo.save(log_row)
        await session.commit()

    result = {
        "status": status,
        "frequency": frequency,
        "recipients_count": len(recipients),
        "sent_count": len(sent_to),
        "total_plays": data.total_plays,
        "unique_songs": data.unique_songs,
        "dry_run": sender.is_dry_run,
    }
    logger.info("email_report_complete %s", result)
    return result
