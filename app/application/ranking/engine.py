"""Ranking engine — snapshot and ranked modes.

Snapshot mode: count plays per song in a time window, return ordered list.
Ranked mode:   compare snapshot against a previous snapshot to produce
               rank movements (new entry, up, down, re-entry, non-mover).

No database calls — operates on pre-loaded PlayEvent lists.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum


class RankMovement(StrEnum):
    NEW_ENTRY = "new_entry"
    RE_ENTRY = "re_entry"
    UP = "up"
    DOWN = "down"
    NON_MOVER = "non_mover"


@dataclass(frozen=True)
class SongKey:
    """Canonical identity for a song in a ranking."""

    artist: str
    title: str


@dataclass
class RankEntry:
    position: int
    song_key: SongKey
    play_count: int
    previous_position: int | None = None
    movement: RankMovement | None = None
    peak_position: int | None = None

    @property
    def position_change(self) -> int | None:
        if self.previous_position is None:
            return None
        return self.previous_position - self.position  # positive = moved up


@dataclass
class RankSnapshot:
    """Ordered list of songs by play count for a station/period."""

    station_id: str
    period_label: str
    entries: list[RankEntry] = field(default_factory=list)
    total_plays: int = 0


def build_snapshot(
    plays: list[tuple[str, str]],
    station_id: str,
    period_label: str,
    top_n: int = 40,
) -> RankSnapshot:
    """Build a ranking snapshot from a list of (artist, title) tuples.

    Args:
        plays: List of (artist, title) tuples (deduplicated, normalised)
        station_id: Station identifier for labelling
        period_label: Human-readable period (e.g. "2026-05-24")
        top_n: Maximum number of entries to include
    """
    counts: Counter[SongKey] = Counter()
    for artist, title in plays:
        counts[SongKey(artist=artist, title=title)] += 1

    ranked = counts.most_common(top_n)
    entries = [
        RankEntry(position=pos, song_key=key, play_count=count)
        for pos, (key, count) in enumerate(ranked, start=1)
    ]
    return RankSnapshot(
        station_id=station_id,
        period_label=period_label,
        entries=entries,
        total_plays=sum(counts.values()),
    )


def apply_movements(
    current: RankSnapshot,
    previous: RankSnapshot,
    all_time_history: set[SongKey] | None = None,
) -> RankSnapshot:
    """Apply rank movement labels by comparing current against previous snapshot.

    A song that wasn't in the previous snapshot but was in all_time_history
    is labelled RE_ENTRY; otherwise NEW_ENTRY.
    """
    prev_positions: dict[SongKey, int] = {
        e.song_key: e.position for e in previous.entries
    }
    all_history = all_time_history or set()

    for entry in current.entries:
        prev_pos = prev_positions.get(entry.song_key)
        entry.previous_position = prev_pos

        if prev_pos is None:
            entry.movement = (
                RankMovement.RE_ENTRY
                if entry.song_key in all_history
                else RankMovement.NEW_ENTRY
            )
        elif entry.position < prev_pos:
            entry.movement = RankMovement.UP
        elif entry.position > prev_pos:
            entry.movement = RankMovement.DOWN
        else:
            entry.movement = RankMovement.NON_MOVER

    return current
