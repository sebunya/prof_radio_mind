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
    # VAL-NOVA-001: URL corrected to radiowavemonitor.com (confirmed IDDS=11129).
    # Strategy 3 (card grid) confirmed working on real HTML 2026-06-06.
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.RADIOWAVE,
        name="Nova 96.9 Radiowave Diary",
        base_url="https://www.radiowavemonitor.com/pub_charts/diaries.aspx",
        config={"idds": "11129"},
        priority=1,
        validation_note=(
            "URL confirmed. Card-grid parser (Strategy 3) confirmed on real HTML 2026-06-06."
        ),
    ),
    # VAL-NOVA-RADOXO-001: radoxo.com/australia/nova-969/playlist UNVALIDATED.
    # Parser unimplemented — run dry_run_nova_radoxo once to inspect HTML structure.
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.RADOXO,
        name="Nova 96.9 Radoxo Playlist",
        base_url="https://radoxo.com/australia/nova-969/playlist",
        config={"station_slug": "nova-969"},
        priority=2,
        validation_note=(
            "UNVALIDATED — VAL-NOVA-RADOXO-001 required. "
            "Run dry_run_nova_radoxo to confirm HTML structure and implement parser."
        ),
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
    # --- Capital FM --- (EXTRACT-3 update)
    # VAL-CAPUK-URL-001: ukradiolive.com/capital-fm/playlist confirmed reachable 2026-06-05.
    # Parser selectors UNVALIDATED — run dry_run_capital_ukradiolive for raw HTML.
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.UKRADIOLIVE,
        name="Capital FM UK Radio Live Playlist",
        base_url="https://ukradiolive.com/capital-fm/playlist",
        config={"station_slug": "capital-fm"},
        priority=1,
        validation_note=(
            "UNVALIDATED — VAL-CAPUK-URL-001 required. Run dry_run_capital_ukradiolive "
            "to inspect HTML structure and confirm parser selectors."
        ),
    ),
    # VAL-CAPUK-ORB-001: Online Radio Box playlist URL confirmed 2026-06-06.
    # URL updated to include /playlist/ path as provided by user.
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.ONLINE_RADIO_BOX,
        name="Capital FM UK Online Radio Box Playlist",
        base_url="https://onlineradiobox.com/uk/capitalfmuk/playlist/",
        config={
            "station_slug": "capitalfmuk",
            "market": "uk",
            "city": "London",
            "country_code": "GB",
            "cs": "uk.capitalfmuk",
        },
        priority=2,
        validation_note=(
            "UNVALIDATED — VAL-CAPUK-ORB-001. URL updated to playlist path. "
            "Parser selectors require dry-run confirmation."
        ),
    ),
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.MANUAL_CSV,
        name="Capital FM UK Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
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
    # VAL-Z100-001: station_id corrected to 1469 per live iHeart v2 station search 2026-06-05.
    # Original seeded value 614 was unverified. v3 API unavailable (404 all paths).
    SourceSeed(
        station_call_sign="WHTZ",
        source_type=SourceType.IHEART,
        name="Z100 iHeart Now Playing",
        base_url="https://api.iheart.com/api/v3/live-meta/stream",
        config={"station_id": "1469"},
        priority=1,
        validation_note="ID corrected 614→1469 (live v2 search). v3 API unavailable; FAILED.",
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
    # VAL-WKSC-001: station_id corrected to 849 per live iHeart v2 station search 2026-06-05.
    # Original seeded value 821 was unverified. v3 API unavailable (404 all paths).
    SourceSeed(
        station_call_sign="WKSC",
        source_type=SourceType.IHEART,
        name="WKSC 103.5 iHeart Now Playing",
        base_url="https://api.iheart.com/api/v3/live-meta/stream",
        config={"station_id": "849"},
        priority=1,
        validation_note="ID corrected 821→849 (live v2 search). v3 API unavailable; FAILED.",
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
    # --- KIIS-FM 102.7 Los Angeles (EXTRACT-3) ---
    # VAL-KIIS1027-WEB-001: iHeart web recently-played page — UNVALIDATED.
    # iHeart v3 API is entirely dead (404 on all paths). This replaces it.
    SourceSeed(
        station_call_sign="KIIS1027",
        source_type=SourceType.IHEART_WEB,
        name="KIIS-FM 102.7 iHeart Recently Played",
        base_url="https://kiisfm.iheart.com/music/recently-played/",
        config={"station_slug": "kiisfm"},
        priority=1,
        validation_note=(
            "UNVALIDATED — VAL-KIIS1027-WEB-001 required. "
            "Run dry_run_kiis_iheart_web to inspect HTML/JSON structure."
        ),
    ),
    # VAL-KIIS-RAD-001: Radiowave IDDS=5080 FAILED live (0 tr.diary-row rows).
    # Kept at priority 2 pending parser selector fix after HTML dump inspection.
    SourceSeed(
        station_call_sign="KIIS1027",
        source_type=SourceType.RADIOWAVE,
        name="KIIS-FM 102.7 Radiowave Monitor Diary",
        base_url="https://www.radiowavemonitor.com/pub_charts/diaries.aspx",
        config={"idds": "5080"},
        priority=2,
        validation_note="VAL-KIIS-RAD-001 FAILED. Demoted to priority 2; selector fix pending.",
    ),
    SourceSeed(
        station_call_sign="KIIS1027",
        source_type=SourceType.MANUAL_CSV,
        name="KIIS-FM 102.7 Manual CSV Fallback",
        base_url=None,
        config=None,
        priority=99,
        validation_note="Always available — manual fallback",
    ),
)
