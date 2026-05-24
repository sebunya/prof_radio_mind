"""Tests for StreamTheWorld ICY metadata collector — no live network calls."""

from __future__ import annotations

import uuid

import pytest

from app.domain.entities.no_track_event import NoTrackReason
from app.infrastructure.collectors.streamtheworld_icy import StreamTheWorldICYCollector


_SOURCE_ID = uuid.uuid4()
_STATION_ID = uuid.uuid4()
_RUN_ID = uuid.uuid4()


def _collector() -> StreamTheWorldICYCollector:
    return StreamTheWorldICYCollector(
        source_id=_SOURCE_ID,
        station_id=_STATION_ID,
        stream_url="https://stream.example.com/station",
    )


def _icy_bytes(stream_title: str) -> bytes:
    return f"StreamTitle='{stream_title}';".encode("utf-8")


# --- parse() ---

def test_parse_returns_play_event_for_valid_stream_title() -> None:
    raw = _icy_bytes("Taylor Swift - Shake It Off")
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert len(plays) == 1
    assert len(no_tracks) == 0
    assert plays[0].raw_artist == "Taylor Swift"
    assert plays[0].raw_title == "Shake It Off"


def test_parse_attribution_is_streamtheworld() -> None:
    raw = _icy_bytes("Artist - Title")
    plays, _ = _collector().parse(raw, 200, _RUN_ID)
    assert plays[0].attribution == "streamtheworld"


def test_parse_non_200_status_returns_no_track() -> None:
    raw = _icy_bytes("Artist - Title")
    plays, no_tracks = _collector().parse(raw, 503, _RUN_ID)
    assert plays == []
    assert len(no_tracks) == 1
    assert no_tracks[0].reason == NoTrackReason.UNKNOWN


def test_parse_missing_stream_title_returns_parse_failure() -> None:
    raw = b"ICY 200 OK\r\nContent-Type: audio/mpeg\r\n\r\n"
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert plays == []
    assert len(no_tracks) == 1
    assert no_tracks[0].reason == NoTrackReason.PARSE_FAILURE


def test_parse_commercial_break_returns_no_track() -> None:
    raw = _icy_bytes("commercial")
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert plays == []
    assert len(no_tracks) == 1
    assert no_tracks[0].reason == NoTrackReason.COMMERCIAL_BREAK_OR_TALK


def test_parse_ads_keyword_returns_no_track() -> None:
    raw = _icy_bytes("ads")
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert plays == []
    assert len(no_tracks) == 1


def test_parse_empty_stream_title_returns_no_track() -> None:
    raw = _icy_bytes("")
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert plays == []
    assert len(no_tracks) == 1


def test_parse_no_dash_separator_uses_stream_title_as_both() -> None:
    raw = _icy_bytes("Radio Jingle")
    plays, no_tracks = _collector().parse(raw, 200, _RUN_ID)
    assert len(plays) == 1
    assert plays[0].raw_artist == "Radio Jingle"
    assert plays[0].raw_title == "Radio Jingle"


def test_parse_station_id_preserved() -> None:
    raw = _icy_bytes("A - B")
    plays, _ = _collector().parse(raw, 200, _RUN_ID)
    assert plays[0].station_id == _STATION_ID


def test_parse_source_id_preserved() -> None:
    raw = _icy_bytes("A - B")
    plays, _ = _collector().parse(raw, 200, _RUN_ID)
    assert plays[0].source_id == _SOURCE_ID
