"""Integration tests for repository implementations against a real PostgreSQL DB.

Run with: RMIAS_INTEGRATION_TESTS=1 pytest tests/integration/ -v
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from tests.integration.conftest import skip_if_no_db


@skip_if_no_db
@pytest.mark.anyio
async def test_station_roundtrip(db_session: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.entities.station import Station
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository

    assert isinstance(db_session, AsyncSession)
    repo = SQLStationRepository(db_session)

    station = Station(
        id=uuid.uuid4(),
        name="Integration Test FM",
        call_sign=f"ITFM{uuid.uuid4().hex[:4].upper()}",
        frequency="99.9 FM",
        city="Sydney",
        country_code="AU",
        is_active=True,
    )
    await repo.save(station)
    await db_session.flush()

    fetched = await repo.get_by_id(station.id)
    assert fetched is not None
    assert fetched.call_sign == station.call_sign
    assert fetched.name == "Integration Test FM"


@skip_if_no_db
@pytest.mark.anyio
async def test_play_event_roundtrip(db_session: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.entities.play_event import PlayEvent
    from app.domain.entities.source import Source, SourceType
    from app.domain.entities.station import Station
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository
    from app.infrastructure.database.repositories.source_repo import SQLSourceRepository
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository

    assert isinstance(db_session, AsyncSession)

    # Station and Source must exist (FK constraint)
    station_id = uuid.uuid4()
    source_id = uuid.uuid4()
    call_sign = f"ITFM{uuid.uuid4().hex[:4].upper()}"
    await SQLStationRepository(db_session).save(
        Station(id=station_id, name="IT Station", call_sign=call_sign,
                country_code="AU", is_active=True)
    )
    await SQLSourceRepository(db_session).save(
        Source(id=source_id, station_id=station_id, source_type=SourceType.MANUAL_CSV,
               name="IT Source")
    )
    await db_session.flush()

    run_id = uuid.uuid4()
    event = PlayEvent.create(
        station_id=station_id, source_id=source_id, collector_run_id=run_id,
        played_at=datetime.now(UTC), raw_artist="Dua Lipa", raw_title="Levitating",
    )

    # CollectorRun FK must also exist — insert a stub row directly
    from app.infrastructure.database.models.collector_runs import CollectorRun as RunModel

    db_session.add(RunModel(
        id=run_id, source_id=source_id, station_id=station_id,
        status="completed",
    ))
    await db_session.flush()

    play_repo = SQLPlayEventRepository(db_session)
    await play_repo.save(event)
    await db_session.flush()

    events = await play_repo.list_for_station(
        station_id,
        datetime(2020, 1, 1, tzinfo=UTC),
        datetime(2099, 1, 1, tzinfo=UTC),
    )
    assert any(e.raw_artist == "Dua Lipa" for e in events)
