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
    # VAL-NOVA-RADOXO-001: radoxo.com parser confirmed on real HTML 2026-06-06.
    # data-ts Unix timestamps give exact broadcast times to second precision.
    # 86+ tracks per day available (full day playlist).
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.RADOXO,
        name="Nova 96.9 Radoxo Playlist",
        base_url="https://radoxo.com/australia/nova-969/playlist",
        config={"station_slug": "nova-969"},
        priority=2,
        validation_note=(
            "VALIDATED — li.playlist-track + data-ts Unix timestamps confirmed 2026-06-06. "
            "86+ tracks/day. Exact broadcast times to second precision."
        ),
    ),
    # VAL-NOVA-RAO-001: radio-australia.org weekly chart — confirmed SSR, parser validated
    # 2026-06-06. NOTE: played_at is synthetic (collection time). Chart covers last 7 days.
    SourceSeed(
        station_call_sign="NOVA969",
        source_type=SourceType.RADIO_AUSTRALIA_ORG,
        name="Nova 96.9 Radio Australia Chart",
        base_url="https://www.radio-australia.org/nova-969",
        config={"station_slug": "nova-969", "chart_period_days": 7},
        priority=3,
        validation_note=(
            "VALIDATED — SSR chart confirmed 2026-06-06. "
            "played_at is synthetic (collection timestamp, not broadcast time)."
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
    # --- Capital FM UK ---
    # VAL-CAPUK-URL-001: ukradiolive.com/capital-fm/playlist confirmed reachable 2026-06-05.
    # Parser selectors confirmed on real HTML 2026-06-06.
    SourceSeed(
        station_call_sign="CAPITALFM",
        source_type=SourceType.UKRADIOLIVE,
        name="Capital FM UK Radio Live Playlist",
        base_url="https://ukradiolive.com/capital-fm/playlist",
        config={"station_slug": "capital-fm"},
        priority=1,
        validation_note=(
            "VALIDATED — plist-item parser confirmed on real HTML 2026-06-06. "
            "Run dry_run_capital_ukradiolive to re-validate selectors."
        ),
    ),
    # VAL-CAPUK-ORB-001: Online Radio Box playlist URL confirmed 2026-06-06.
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
    # --- KIIS-FM 102.7 Los Angeles ---
    # VAL-KIIS1027-WEB-001: iHeart web recently-played page — figcaption parser
    # confirmed on real HTML 2026-06-06.
    SourceSeed(
        station_call_sign="KIIS1027",
        source_type=SourceType.IHEART_WEB,
        name="KIIS-FM 102.7 iHeart Recently Played",
        base_url="https://kiisfm.iheart.com/music/recently-played/",
        config={"station_slug": "kiisfm"},
        priority=1,
        validation_note=(
            "VALIDATED — figcaption parser confirmed on real HTML 2026-06-06. "
            "Run dry_run_kiis_iheart_web to re-validate."
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
