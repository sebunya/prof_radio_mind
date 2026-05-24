"""GET /stations — list all active stations."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.application.source_config.station_seeds import STATION_SEEDS

router = APIRouter(prefix="/stations", tags=["stations"])


class StationResponse(BaseModel):
    call_sign: str
    name: str
    frequency: str
    city: str
    country_code: str


@router.get("", response_model=list[StationResponse])
def list_stations() -> list[StationResponse]:
    return [
        StationResponse(
            call_sign=s.call_sign,
            name=s.name,
            frequency=s.frequency,
            city=s.city,
            country_code=s.country_code,
        )
        for s in STATION_SEEDS
    ]
