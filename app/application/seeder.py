"""Startup DB seeder — idempotently creates stations and sources from seed data.

Uses deterministic uuid5 IDs so that the scheduler's pre-computed station/source IDs
always match what is in the database, even across restarts.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.source_config.source_seeds import SOURCE_SEEDS
from app.application.source_config.station_seeds import STATION_SEEDS
from app.domain.entities.source import Source, SourceType
from app.domain.entities.station import Station
from app.infrastructure.database.repositories.source_repo import SQLSourceRepository
from app.infrastructure.database.repositories.station_repo import SQLStationRepository

logger = logging.getLogger(__name__)

# Deterministic ID derivation — must match the IDs used in the scheduler.
# Any change here requires a data migration.
_NS = uuid.NAMESPACE_DNS


def station_id_for(call_sign: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"station.{call_sign}")


def source_id_for(call_sign: str, source_type: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"source.{call_sign}.{source_type}")


async def seed_database(session: AsyncSession) -> None:
    """Create stations and sources if they do not already exist."""
    station_repo = SQLStationRepository(session)
    source_repo = SQLSourceRepository(session)

    for station_seed in STATION_SEEDS:
        sid = station_id_for(station_seed.call_sign)
        existing = await station_repo.get_by_id(sid)
        if existing is None:
            await station_repo.save(
                Station(
                    id=sid,
                    name=station_seed.name,
                    call_sign=station_seed.call_sign,
                    frequency=station_seed.frequency,
                    city=station_seed.city,
                    country_code=station_seed.country_code,
                    is_active=True,
                )
            )
            logger.info("seeder created station call_sign=%s id=%s", station_seed.call_sign, sid)
        else:
            logger.debug("seeder skip station call_sign=%s (exists)", station_seed.call_sign)

    for source_seed in SOURCE_SEEDS:
        type_key = source_seed.source_type.value
        src_id = source_id_for(source_seed.station_call_sign, type_key)
        existing_src = await source_repo.get_by_id(src_id)
        if existing_src is None:
            station_sid = station_id_for(source_seed.station_call_sign)
            await source_repo.save(
                Source(
                    id=src_id,
                    station_id=station_sid,
                    source_type=SourceType(type_key),
                    name=source_seed.name,
                    base_url=source_seed.base_url,
                    config=source_seed.config,
                    is_active=True,
                )
            )
            logger.info("seeder created source name=%s id=%s", source_seed.name, src_id)
        else:
            logger.debug("seeder skip source name=%s (already exists)", source_seed.name)

    await session.commit()
    logger.info("seeder complete")
