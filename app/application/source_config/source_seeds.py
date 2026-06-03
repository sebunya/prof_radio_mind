"""Static seed definitions for the three MVP stations' sources.

Validation status is noted in comments — do not assume anything is validated
unless VAL-* codes are confirmed in docs/VALIDATION_REGISTER.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.source import SourceType


@dataclass(frozen=True)
class SourceSeed:
    station_call_sign: str
    source_type: SourceType
    name: str
    base_url: str | None
    config: dict | None
    # Priority within the station (1 = primary)
    priority: int
    # Validation status note — informational only, not enforced at runtime
    validation_note: str


SOURCE_SEEDS: tuple[SourceSeed, ...] = (
    # --- Nova 96.9 ---
    # VAL-NOVA-001: Radiowave IDDS=11129 is UNVALIDATED; assumed from historical knowledge
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.RADIOWAVE,
        name="Nova 96.9 Radiowave Diary",
        base_url="https://www.radiowave.com.au/diary",
        config={"idds": "11129"},
        priority=1,
        validation_note="UNVALIDATED — VAL-NOVA-001 must be confirmed before Pass 6",
    ),
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.MANUAL_CSV,
        name="Nova 96.9 Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
    # --- KIIS-FM ---
    # VAL-KIIS-001: iHeart station ID 2501 is UNVALIDATED
    # VAL-KIIS-003: HTTP 204 behavior UNCONFIRMED — guard implemented regardless
    SourceSeed(
        station_call_sign="KIISFM",
        source_type=SourceType.IHEART,
        name="KIIS-FM iHeart Now Playing",
        base_url="https://api.iheart.com/api/v3/live-meta/stream",
        config={"station_id": "2501"},
        priority=1,
        validation_note="UNVALIDATED — VAL-KIIS-001 must confirm station_id=2501 before Pass 7",
    ),
    SourceSeed(
        station_call_sign="KIISFM",
        source_type=SourceType.MANUAL_CSV,
        name="KIIS-FM Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
    # --- Capital FM ---
    # VAL-CAPUK-ORB-001: Online Radio Box candidate source is UNVALIDATED
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.ONLINE_RADIO_BOX,
        name="Capital FM UK Online Radio Box Candidate",
        base_url="https://onlineradiobox.com/uk/capitalfmuk/",
        config={
            "station_slug": "capitalfmuk",
            "market": "uk",
            "city": "London",
            "country_code": "GB",
            "validation_status": "UNVALIDATED",
            "parser_status": "NOT_BUILT",
            "source_page_type": "online_radio_box_station_page",
        },
        priority=1,
        validation_note=(
            "UNVALIDATED — Capital FM UK Online Radio Box candidate source. "
            "Parser, fixture extraction, polling cadence and source behavior "
            "must be validated before enabling automated collection."
        ),
    ),
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.MANUAL_CSV,
        name="Capital FM UK Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note=(
            "Always available — manual fallback. "
            "Import schema must still be tested before client-facing reporting."
        ),
    ),
)
