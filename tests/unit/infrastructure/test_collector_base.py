"""Fixture-driven tests for BaseCollector lifecycle.

No live network calls. Uses in-memory stub collectors.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.entities.collector_run import CollectorStatus
from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.infrastructure.collectors.base import BaseCollector


class _StubCollector(BaseCollector):
    """Collector that returns a fixed play event from in-memory bytes."""

    def __init__(
        self,
        raw_bytes: bytes,
        http_status: int | None = 200,
        content_type: str = "text/html",
        storage_root: str = "/tmp/test_payloads",
        raise_on_fetch: bool = False,
        raise_on_parse: bool = False,
    ) -> None:
        super().__init__(uuid.uuid4(), uuid.uuid4(), storage_root=storage_root)
        self._raw_bytes = raw_bytes
        self._http_status = http_status
        self._content_type = content_type
        self._raise_on_fetch = raise_on_fetch
        self._raise_on_parse = raise_on_parse

    async def fetch_raw(self) -> tuple[bytes, int | None, str | None]:
        if self._raise_on_fetch:
            raise ConnectionError("simulated network failure")
        return self._raw_bytes, self._http_status, self._content_type

    def parse(
        self,
        raw_bytes: bytes,
        http_status: int | None,
        collector_run_id: uuid.UUID,
    ) -> tuple[list[PlayEvent], list[NoTrackEvent]]:
        if self._raise_on_parse:
            raise ValueError("simulated parse failure")
        if http_status == 204:
            ev = NoTrackEvent.create(
                self.station_id,
                self.source_id,
                collector_run_id,
                observed_at=datetime.now(tz=UTC),
                reason=NoTrackReason.SOURCE_HTTP_204,
                raw_http_status=204,
            )
            return [], [ev]
        play = PlayEvent.create(
            self.station_id,
            self.source_id,
            collector_run_id,
            played_at=datetime.now(tz=UTC),
            raw_artist="Test Artist",
            raw_title="Test Title",
        )
        return [play], []


@pytest.mark.anyio
async def test_successful_run_stores_raw_payload(tmp_path: pytest.fixture) -> None:
    raw = b"<html>test</html>"
    collector = _StubCollector(raw, storage_root=str(tmp_path))
    result = await collector.run()

    assert result.raw_payload is not None
    assert result.raw_payload.byte_size == len(raw)
    assert len(result.raw_payload.sha256) == 64
    # Verify file actually written
    import os

    assert os.path.exists(result.raw_payload.storage_path)


@pytest.mark.anyio
async def test_successful_run_sha256_matches_content(tmp_path: pytest.fixture) -> None:
    import hashlib

    raw = b"real payload content"
    collector = _StubCollector(raw, storage_root=str(tmp_path))
    result = await collector.run()

    assert result.raw_payload is not None
    assert result.raw_payload.sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.anyio
async def test_successful_run_produces_play_event(tmp_path: pytest.fixture) -> None:
    collector = _StubCollector(b"data", storage_root=str(tmp_path))
    result = await collector.run()

    assert len(result.play_events) == 1
    assert result.collector_run.status == CollectorStatus.COMPLETED


@pytest.mark.anyio
async def test_http_204_produces_no_track_event(tmp_path: pytest.fixture) -> None:
    collector = _StubCollector(b"", http_status=204, storage_root=str(tmp_path))
    result = await collector.run()

    assert len(result.no_track_events) == 1
    assert len(result.play_events) == 0
    assert result.no_track_events[0].reason == NoTrackReason.SOURCE_HTTP_204
    assert result.no_track_events[0].raw_http_status == 204


@pytest.mark.anyio
async def test_fetch_failure_sets_failed_status_does_not_raise(tmp_path: pytest.fixture) -> None:
    collector = _StubCollector(b"", raise_on_fetch=True, storage_root=str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.FAILED
    assert result.collector_run.error_message is not None
    assert "simulated network failure" in result.collector_run.error_message


@pytest.mark.anyio
async def test_parse_failure_sets_failed_status_does_not_raise(tmp_path: pytest.fixture) -> None:
    collector = _StubCollector(b"data", raise_on_parse=True, storage_root=str(tmp_path))
    result = await collector.run()

    assert result.collector_run.status == CollectorStatus.FAILED
    assert result.collector_run.error_message is not None
    assert "simulated parse failure" in result.collector_run.error_message
    # Raw payload was still stored before parse failure
    assert result.raw_payload is not None


@pytest.mark.anyio
async def test_failed_collector_does_not_stop_second_run(tmp_path: pytest.fixture) -> None:
    failing = _StubCollector(b"", raise_on_fetch=True, storage_root=str(tmp_path))
    passing = _StubCollector(b"data", storage_root=str(tmp_path))

    result1 = await failing.run()
    result2 = await passing.run()

    assert result1.collector_run.status == CollectorStatus.FAILED
    assert result2.collector_run.status == CollectorStatus.COMPLETED
