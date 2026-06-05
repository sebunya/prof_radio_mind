"""Static seed definitions for station sources.

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
    # --- BBC Radio 1 --- (EXTRACT-2)
    # VAL-BBC1-001: BBC Sounds/RMS API reachability UNVALIDATED
    # VAL-BBC1-006: BBC ToS for automated access UNCONFIRMED
    SourceSeed(
        station_call_sign="BBCRADIO1",
        source_type=SourceType.BBC_SOUNDS,
        name="BBC Radio 1 RMS API",
        base_url="https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest",
        config={"service_id": "bbc_radio_one"},
        priority=1,
        validation_note=(
            "UNVALIDATED — VAL-BBC1-001 (live reachability) and VAL-BBC1-006 (ToS) required"
        ),
    ),
    SourceSeed(
        station_call_sign="BBCRADIO1",
        source_type=SourceType.MANUAL_CSV,
        name="BBC Radio 1 Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
    # --- Heart FM UK --- (EXTRACT-2)
    # VAL-HEARTFM-002: CSS selectors against live page UNVALIDATED (synthetic fixture only)
    SourceSeed(
        station_call_sign="HEARTFMUK",
        source_type=SourceType.HEART_LAST_PLAYED,
        name="Heart FM Last Played Page",
        base_url="https://www.heart.co.uk/radio/",
        config={"parser": "heart_last_played_css"},
        priority=1,
        validation_note="UNVALIDATED — VAL-HEARTFM-002 (live CSS selectors) required",
    ),
    SourceSeed(
        station_call_sign="HEARTFMUK",
        source_type=SourceType.MANUAL_CSV,
        name="Heart FM UK Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
    # --- Z100 New York (WHTZ) --- (EXTRACT-2)
    # VAL-Z100-001: iHeart station_id=614 confirmed in fixture; not validated against live API
    SourceSeed(
        station_call_sign="WHTZ",
        source_type=SourceType.IHEART,
        name="Z100 iHeart Now Playing",
        base_url="https://api.iheart.com/api/v3/live-meta/stream",
        config={"station_id": "614"},
        priority=1,
        validation_note="UNVALIDATED — VAL-Z100-001 (live station_id=614) required before enable",
    ),
    SourceSeed(
        station_call_sign="WHTZ",
        source_type=SourceType.MANUAL_CSV,
        name="Z100 Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
    # --- WKSC 103.5 Chicago --- (EXTRACT-2)
    # VAL-WKSC-001: iHeart station_id=821 confirmed in fixture; not validated against live API
    SourceSeed(
        station_call_sign="WKSC",
        source_type=SourceType.IHEART,
        name="WKSC 103.5 iHeart Now Playing",
        base_url="https://api.iheart.com/api/v3/live-meta/stream",
        config={"station_id": "821"},
        priority=1,
        validation_note="UNVALIDATED — VAL-WKSC-001 (live station_id=821) required before enable",
    ),
    SourceSeed(
        station_call_sign="WKSC",
        source_type=SourceType.MANUAL_CSV,
        name="WKSC 103.5 Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
)
