"""Static seed definitions for the MVP stations and extracted-collector stations.

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
    # --- EXTRACT-2: new stations for extracted collectors ---
    StationSeed(
        call_sign="BBCRADIO1",
        name="BBC Radio 1",
        frequency="97.6-99.8 FM",
        city="London",
        country_code="GB",
    ),
    StationSeed(
        call_sign="HEARTFMUK",
        name="Heart FM UK",
        frequency="106.2 FM",
        city="London",
        country_code="GB",
    ),
    StationSeed(
        call_sign="WHTZ",
        name="Z100 New York",
        frequency="100.3 FM",
        city="New York",
        country_code="US",
    ),
    StationSeed(
        call_sign="WKSC",
        name="WKSC 103.5 Chicago",
        frequency="103.5 FM",
        city="Chicago",
        country_code="US",
    ),
    # --- EXTRACT-3: KIIS-FM 102.7 Los Angeles (separate from KIISFM Sydney 106.5) ---
    StationSeed(
        call_sign="KIIS1027",
        name="KIIS-FM 102.7 Los Angeles",
        frequency="102.7 FM",
        city="Los Angeles",
        country_code="US",
    ),
)
