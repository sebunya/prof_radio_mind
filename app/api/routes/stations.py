"""GET /stations — list all active stations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/stations", tags=["stations"])


class StationResponse(BaseModel):
    id: str
    call_sign: str
    name: str
    frequency: str | None
    city: str | None
    country_code: str


@router.get("", response_model=list[StationResponse])
async def list_stations(
    session: AsyncSession = Depends(get_db),
) -> list[StationResponse]:
    from app.infrastructure.database.repositories.station_repo import SQLStationRepository

    try:
        repo = SQLStationRepository(session)
        stations = await repo.list_active()
        return [
            StationResponse(
                id=str(s.id),
                call_sign=s.call_sign,
                name=s.name,
                frequency=s.frequency,
                city=s.city,
                country_code=s.country_code,
            )
            for s in stations
        ]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("stations_list_db_error: %s", e)
        return []

