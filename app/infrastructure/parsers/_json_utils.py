"""Shared JSON-traversal utilities for HTML parsers that extract embedded JSON."""

from __future__ import annotations

from typing import Any

_TRACK_LIST_KEYS = frozenset({
    "recentlyPlayedSongs", "recentlyPlayed", "songHistory",
    "playHistory", "songs", "tracks", "playlist",
    "history", "recentTracks", "nowPlaying", "playlistItems",
})
_MAX_DEPTH = 10


def find_track_list(data: Any, depth: int = 0) -> list | None:
    """Recursively find the first list that looks like a track list in nested JSON."""
    if depth > _MAX_DEPTH:
        return None
    if isinstance(data, dict):
        for key in _TRACK_LIST_KEYS:
            val = data.get(key)
            if isinstance(val, list) and val:
                return val
        for value in data.values():
            found = find_track_list(value, depth + 1)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_track_list(item, depth + 1)
            if found is not None:
                return found
    return None
