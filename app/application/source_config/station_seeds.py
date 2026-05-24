"""Static seed definitions for the three MVP stations.

These are loaded on startup if not already present in the database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StationSeed:
    call_sign: str
    name: str
    frequency: str
    city: str
    country_code: str = "AU"


STATION_SEEDS: tuple[StationSeed, ...] = (
    StationSeed(
        call_sign="NOVA969",
        name="Nova 96.9",
        frequency="96.9 FM",
        city="Sydney",
    ),
    StationSeed(
        call_sign="KIISFM",
        name="KIIS-FM",
        frequency="106.5 FM",
        city="Sydney",
    ),
    StationSeed(
        call_sign="CAPITALFM",
        name="Capital FM",
        frequency="96.1 FM",
        city="Sydney",
    ),
)
