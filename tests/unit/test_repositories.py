"""Unit tests for SQLAlchemy repository implementations (mocked session)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.collector_run import CollectorRun, CollectorStatus
from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.domain.entities.source import Source, SourceType
from app.domain.entities.station import Station
from app.domain.value_objects.raw_payload import RawPayload
from app.infrastructure.database.repositories.collector_run_repo import SQLCollectorRunRepository
from app.infrastructure.database.repositories.no_track_event_repo import SQLNoTrackEventRepository
from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
from app.infrastructure.database.repositories.raw_payload_repo import SQLRawPayloadRepository
from app.infrastructure.database.repositories.source_repo import SQLSourceRepository
from app.infrastructure.database.repositories.station_repo import SQLStationRepository


def _mock_session(execute_result: MagicMock | None = None) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    # execute must return a plain MagicMock so .scalar()/.scalars().all() aren't coroutines
    default_result = MagicMock()
    default_result.scalar.return_value = None
    default_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result or default_result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# --- Station repository ---

@pytest.mark.anyio
async def test_station_repo_save_new() -> None:
    session = _mock_session()
    repo = SQLStationRepository(session)
    station = Station(
        id=uuid.uuid4(), name="Nova 96.9", call_sign="NOVA969",
        frequency="96.9 FM", city="Sydney", country_code="AU", is_active=True,
    )
    await repo.save(station)
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.anyio
async def test_station_repo_get_by_id_missing() -> None:
    session = _mock_session()
    repo = SQLStationRepository(session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_station_repo_list_active() -> None:
    mock_row = MagicMock()
    mock_row.id = uuid.uuid4()
    mock_row.name = "Nova"
    mock_row.call_sign = "NOVA969"
    mock_row.frequency = "96.9 FM"
    mock_row.city = "Sydney"
    mock_row.country_code = "AU"
    mock_row.is_active = True
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [mock_row]
    session = _mock_session(execute_result=result_mock)
    repo = SQLStationRepository(session)
    result = await repo.list_active()
    assert len(result) == 1
    assert result[0].call_sign == "NOVA969"


# --- Source repository ---

@pytest.mark.anyio
async def test_source_repo_save_new() -> None:
    session = _mock_session()
    repo = SQLSourceRepository(session)
    source = Source(
        id=uuid.uuid4(), station_id=uuid.uuid4(),
        source_type=SourceType.RADIOWAVE, name="Nova Radiowave",
    )
    await repo.save(source)
    session.add.assert_called_once()


# --- CollectorRun repository ---

@pytest.mark.anyio
async def test_collector_run_repo_save() -> None:
    session = _mock_session()
    repo = SQLCollectorRunRepository(session)
    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    await repo.save(run)
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.anyio
async def test_collector_run_repo_update_status_missing() -> None:
    session = _mock_session()
    repo = SQLCollectorRunRepository(session)
    run = CollectorRun.create(source_id=uuid.uuid4(), station_id=uuid.uuid4())
    run.transition(CollectorStatus.FAILED)
    # get returns None — should not raise
    await repo.update_status(run)


# --- RawPayload repository ---

@pytest.mark.anyio
async def test_raw_payload_repo_save() -> None:
    session = _mock_session()
    repo = SQLRawPayloadRepository(session)
    payload = RawPayload.create(
        collector_run_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        raw_bytes=b"hello",
        storage_path="/data/test.bin",
    )
    await repo.save(payload)
    session.add.assert_called_once()


@pytest.mark.anyio
async def test_raw_payload_repo_exists_by_sha256_false() -> None:
    session = _mock_session()
    session.execute.return_value.scalar.return_value = None
    repo = SQLRawPayloadRepository(session)
    result = await repo.exists_by_sha256("aabbcc")
    assert result is False


# --- PlayEvent repository ---

@pytest.mark.anyio
async def test_play_event_repo_save() -> None:
    session = _mock_session()
    repo = SQLPlayEventRepository(session)
    event = PlayEvent.create(
        station_id=uuid.uuid4(), source_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(),
        played_at=datetime.now(UTC), raw_artist="Dua Lipa", raw_title="Levitating",
    )
    await repo.save(event)
    session.add.assert_called_once()


@pytest.mark.anyio
async def test_play_event_repo_exists_by_source_event_id_false() -> None:
    session = _mock_session()
    session.execute.return_value.scalar.return_value = None
    repo = SQLPlayEventRepository(session)
    result = await repo.exists_by_source_event_id(uuid.uuid4(), "ev-123")
    assert result is False


@pytest.mark.anyio
async def test_play_event_repo_exists_by_fingerprint_false() -> None:
    session = _mock_session()
    session.execute.return_value.scalar.return_value = None
    repo = SQLPlayEventRepository(session)
    result = await repo.exists_by_fingerprint(uuid.uuid4(), "aabbccdd")
    assert result is False


@pytest.mark.anyio
async def test_play_event_repo_list_for_station_empty() -> None:
    session = _mock_session()
    repo = SQLPlayEventRepository(session)
    result = await repo.list_for_station(
        uuid.uuid4(),
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert result == []


# --- NoTrackEvent repository ---

@pytest.mark.anyio
async def test_no_track_event_repo_save() -> None:
    session = _mock_session()
    repo = SQLNoTrackEventRepository(session)
    event = NoTrackEvent.create(
        station_id=uuid.uuid4(), source_id=uuid.uuid4(),
        collector_run_id=uuid.uuid4(), observed_at=datetime.now(UTC),
        reason=NoTrackReason.SOURCE_HTTP_204,
    )
    await repo.save(event)
    session.add.assert_called_once()
