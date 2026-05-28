"""Trend alert service — detects threshold-crossing songs and fires webhook events.

Three event types are produced:

``song.trending``
    A song has accumulated *at least* ``settings.trend_plays_threshold`` plays in
    the rolling 7-day window AND was *below* that threshold in the preceding 7-day
    window.  This is **edge-triggered**: the event fires exactly once — the first
    night the threshold is crossed — so webhooks receive at most one notification
    per song per two-week cycle without any persistent state.

``song.new_entry``
    A song appears for the *first time* in the rolling 7-day window with at least
    ``settings.trend_new_entry_plays`` plays (zero plays in the prior window).
    Captures breakout new releases before they reach the trending threshold.

``song.aria_match``
    A song being actively played on monitored stations is currently ranked on the
    ARIA Singles chart.  Fires each night a match exists — webhook consumers
    should deduplicate by (artist, title, week) if they only want one alert per
    chart cycle.  Silently skipped if no ARIA chart data is cached in memory.

All events are delivered through the existing ``fire_event`` webhook infrastructure
(HMAC-signed, with retry logic).

Payload shapes
--------------
``song.trending`` / ``song.new_entry``::

    {
      "event":        "song.trending",
      "artist":       "Taylor Swift",
      "title":        "Anti-Hero",
      "plays":        87,
      "prev_plays":   32,           # absent for song.new_entry
      "period_days":  7,
      "threshold":    50,           # absent for song.new_entry
      "stations":     ["KIIS 106.5", "Nova 96.9"],
      "triggered_at": "2025-05-27T22:00:00+00:00"
    }

``song.aria_match``::

    {
      "event":          "song.aria_match",
      "artist":         "Billie Eilish",
      "title":          "Birds of a Feather",
      "aria_position":  4,
      "plays_this_week": 61,
      "stations":       ["Nova 96.9"],
      "triggered_at":   "2025-05-27T22:00:00+00:00"
    }
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

# Module-level imports so unit tests can patch these names directly via
# patch("app.application.alerts.trend_alert_service.<name>").
from app.application.webhooks.service import fire_event
from app.core.settings import settings
from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
from app.infrastructure.database.repositories.station_repo import SQLStationRepository
from app.infrastructure.database.session import _get_factory

logger = logging.getLogger(__name__)


async def check_and_fire_trend_alerts() -> dict:
    """Run the full trend-detection sweep and fire matching webhook events.

    Returns a summary dict with counts of alerts fired and songs checked,
    suitable for structured logging by the caller.
    """

    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Current window: last 7 complete days (rolling)
    cur_start = today - timedelta(days=7)
    cur_end   = today

    # Previous window: 8–14 days ago — mirror of current, no overlap
    prev_start = today - timedelta(days=14)
    prev_end   = cur_start

    logger.info(
        "trend_alert_sweep_start cur=%s–%s prev=%s–%s",
        cur_start.date(), cur_end.date(),
        prev_start.date(), prev_end.date(),
    )

    # ── Aggregate plays across all active stations ────────────────────────────
    cur_counts:   Counter[tuple[str, str]] = Counter()
    prev_counts:  Counter[tuple[str, str]] = Counter()
    song_stations: dict[tuple[str, str], set[str]] = defaultdict(set)

    async with _get_factory()() as session:
        station_repo = SQLStationRepository(session)
        play_repo    = SQLPlayEventRepository(session)
        stations     = await station_repo.list_active()

        for stn in stations:
            cur_events  = await play_repo.list_for_station(stn.id, cur_start, cur_end)
            prev_events = await play_repo.list_for_station(stn.id, prev_start, prev_end)

            for evt in cur_events:
                key = (evt.raw_artist, evt.raw_title)
                cur_counts[key]  += 1
                song_stations[key].add(stn.call_sign)

            for evt in prev_events:
                key = (evt.raw_artist, evt.raw_title)
                prev_counts[key] += 1

    triggered_at = now.isoformat()
    trending_fired = 0
    new_entry_fired = 0
    aria_fired = 0

    # ── 1. Trending songs (edge-triggered threshold crossing) ─────────────────
    threshold = settings.trend_plays_threshold
    for (artist, title), cur_plays in cur_counts.most_common():
        prev_plays = prev_counts.get((artist, title), 0)
        if cur_plays >= threshold and prev_plays < threshold:
            await fire_event(
                "song.trending",
                {
                    "artist":       artist,
                    "title":        title,
                    "plays":        cur_plays,
                    "prev_plays":   prev_plays,
                    "period_days":  7,
                    "threshold":    threshold,
                    "stations":     sorted(song_stations[(artist, title)]),
                    "triggered_at": triggered_at,
                },
            )
            trending_fired += 1
            logger.info(
                "trend_alert_trending artist=%r title=%r plays=%d prev=%d",
                artist, title, cur_plays, prev_plays,
            )

    # ── 2. New entries (first appearance with significant plays) ──────────────
    new_entry_min = settings.trend_new_entry_plays
    for (artist, title), cur_plays in cur_counts.most_common():
        if cur_plays >= new_entry_min and (artist, title) not in prev_counts:
            await fire_event(
                "song.new_entry",
                {
                    "artist":       artist,
                    "title":        title,
                    "plays":        cur_plays,
                    "period_days":  7,
                    "stations":     sorted(song_stations[(artist, title)]),
                    "triggered_at": triggered_at,
                },
            )
            new_entry_fired += 1
            logger.info(
                "trend_alert_new_entry artist=%r title=%r plays=%d",
                artist, title, cur_plays,
            )

    # ── 3. ARIA chart matches (songs on chart with active airplay) ────────────
    aria_matches = _get_current_aria_matches(cur_counts)
    for pos, artist, title in aria_matches:
        await fire_event(
            "song.aria_match",
            {
                "artist":          artist,
                "title":           title,
                "aria_position":   pos,
                "plays_this_week": cur_counts.get((artist, title), 0),
                "stations":        sorted(song_stations.get((artist, title), set())),
                "triggered_at":    triggered_at,
            },
        )
        aria_fired += 1
        logger.info(
            "trend_alert_aria_match position=%d artist=%r title=%r",
            pos, artist, title,
        )

    summary = {
        "songs_checked":    len(cur_counts),
        "trending_fired":   trending_fired,
        "new_entry_fired":  new_entry_fired,
        "aria_fired":       aria_fired,
        "total_fired":      trending_fired + new_entry_fired + aria_fired,
    }
    logger.info("trend_alert_sweep_complete %s", summary)
    return summary


def _get_current_aria_matches(
    song_counts: Counter[tuple[str, str]],
) -> list[tuple[int, str, str]]:
    """Return ``[(position, artist, title)]`` for songs in both the play window
    and the current in-memory ARIA chart cache.

    Returns an empty list if no chart data is available (fail-safe).
    """
    try:
        from app.api.routes.charts import _chart_cache

        if not _chart_cache:
            return []
        latest_key = max(_chart_cache.keys(), key=lambda k: k[1])
        chart_entries = _chart_cache[latest_key]
        aria_map: dict[tuple[str, str], int] = {
            (e["artist"].lower(), e["title"].lower()): e["position"]
            for e in chart_entries
        }
        hits: list[tuple[int, str, str]] = []
        for artist, title in song_counts:
            pos = aria_map.get((artist.lower(), title.lower()))
            if pos is not None:
                hits.append((pos, artist, title))
        hits.sort(key=lambda x: x[0])
        return hits[:10]
    except Exception:
        return []
