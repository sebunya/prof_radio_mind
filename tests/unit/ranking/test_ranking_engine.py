"""Tests for the ranking engine — snapshot and ranked modes."""

from __future__ import annotations

from app.application.ranking.engine import (
    RankMovement,
    SongKey,
    apply_movements,
    build_snapshot,
)

_STATION = "NOVA969"


def _plays(*songs: tuple[str, str], repeat: int = 1) -> list[tuple[str, str]]:
    return [song for song in songs for _ in range(repeat)]


def test_snapshot_ranks_by_play_count() -> None:
    plays = (
        _plays(("Tame Impala", "The Less I Know The Better"), repeat=5)
        + _plays(("Flume", "Never Be Like You"), repeat=3)
        + _plays(("Dua Lipa", "Levitating"), repeat=7)
    )
    snap = build_snapshot(plays, _STATION, "2026-05-24")

    assert snap.entries[0].song_key.artist == "Dua Lipa"
    assert snap.entries[0].position == 1
    assert snap.entries[0].play_count == 7


def test_snapshot_position_1_has_most_plays() -> None:
    plays = (
        _plays(("A", "Song A"), repeat=10)
        + _plays(("B", "Song B"), repeat=5)
        + _plays(("C", "Song C"), repeat=1)
    )
    snap = build_snapshot(plays, _STATION, "2026-05-24")
    assert snap.entries[0].play_count >= snap.entries[1].play_count


def test_snapshot_total_plays() -> None:
    plays = _plays(("A", "T"), repeat=3) + _plays(("B", "U"), repeat=2)
    snap = build_snapshot(plays, _STATION, "2026-05-24", top_n=40)
    assert snap.total_plays == 5


def test_snapshot_top_n_limits_entries() -> None:
    plays = [(f"Artist {i}", f"Song {i}") for i in range(50)]
    snap = build_snapshot(plays, _STATION, "2026-05-24", top_n=10)
    assert len(snap.entries) <= 10


def test_snapshot_empty_plays() -> None:
    snap = build_snapshot([], _STATION, "2026-05-24")
    assert snap.entries == []
    assert snap.total_plays == 0


def test_movement_new_entry() -> None:
    prev_plays = _plays(("A", "T"), repeat=5)
    curr_plays = _plays(("A", "T"), repeat=5) + _plays(("B", "New Song"), repeat=3)

    prev = build_snapshot(prev_plays, _STATION, "week-1")
    curr = build_snapshot(curr_plays, _STATION, "week-2")
    curr = apply_movements(curr, prev)

    new_entry = next(e for e in curr.entries if e.song_key == SongKey("B", "New Song"))
    assert new_entry.movement == RankMovement.NEW_ENTRY


def test_movement_re_entry() -> None:
    prev_plays = _plays(("A", "T"), repeat=5)
    curr_plays = _plays(("A", "T"), repeat=5) + _plays(("B", "Old Song"), repeat=3)
    all_history = {SongKey("B", "Old Song")}

    prev = build_snapshot(prev_plays, _STATION, "week-1")
    curr = build_snapshot(curr_plays, _STATION, "week-2")
    curr = apply_movements(curr, prev, all_time_history=all_history)

    re_entry = next(e for e in curr.entries if e.song_key == SongKey("B", "Old Song"))
    assert re_entry.movement == RankMovement.RE_ENTRY


def test_movement_up() -> None:
    prev_plays = _plays(("A", "T1"), repeat=10) + _plays(("B", "T2"), repeat=5)
    curr_plays = _plays(("A", "T1"), repeat=5) + _plays(("B", "T2"), repeat=10)

    prev = build_snapshot(prev_plays, _STATION, "week-1")
    curr = build_snapshot(curr_plays, _STATION, "week-2")
    curr = apply_movements(curr, prev)

    b_entry = next(e for e in curr.entries if e.song_key == SongKey("B", "T2"))
    assert b_entry.movement == RankMovement.UP
    assert b_entry.position_change is not None
    assert b_entry.position_change > 0


def test_movement_down() -> None:
    prev_plays = _plays(("A", "T1"), repeat=5) + _plays(("B", "T2"), repeat=10)
    curr_plays = _plays(("A", "T1"), repeat=10) + _plays(("B", "T2"), repeat=5)

    prev = build_snapshot(prev_plays, _STATION, "week-1")
    curr = build_snapshot(curr_plays, _STATION, "week-2")
    curr = apply_movements(curr, prev)

    a_entry = next(e for e in curr.entries if e.song_key == SongKey("A", "T1"))
    assert a_entry.movement == RankMovement.UP
    b_entry = next(e for e in curr.entries if e.song_key == SongKey("B", "T2"))
    assert b_entry.movement == RankMovement.DOWN


def test_movement_non_mover() -> None:
    plays = _plays(("A", "T"), repeat=5)
    prev = build_snapshot(plays, _STATION, "week-1")
    curr = build_snapshot(plays, _STATION, "week-2")
    curr = apply_movements(curr, prev)

    a_entry = curr.entries[0]
    assert a_entry.movement == RankMovement.NON_MOVER
    assert a_entry.position_change == 0
