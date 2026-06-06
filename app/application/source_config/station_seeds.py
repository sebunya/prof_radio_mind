"""Static seed definitions for the active station set.

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
    # CAPITALFM is retained as the stable internal key for deterministic UUID compatibility.
    # It represents Capital FM UK / London. Do not rename without a migration.
    StationSeed(
        call_sign="CAPITALFM",
        name="Capital FM UK",
        frequency="95.8 FM",
        city="London",
        country_code="GB",
    ),
    StationSeed(
        call_sign="KIIS1027",
        name="KIIS-FM 102.7 Los Angeles",
        frequency="102.7 FM",
        city="Los Angeles",
        country_code="US",
    ),
)
