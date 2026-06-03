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
    # CAPITALFM is retained as the stable internal key for deterministic UUID compatibility.
    # It represents Capital FM UK / London. Do not rename without a migration.
    StationSeed(
        call_sign="CAPITALFM",
        name="Capital FM UK",
        frequency="95.8 FM",
        city="London",
        country_code="GB",
    ),
)
