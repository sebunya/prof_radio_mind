"""Diagnostic CLI — single read-only fetch per source, prints parsed songs, exits.

NO DATABASE WRITES. NO DISK WRITES BY DEFAULT. NO SCHEDULER. NO GLOBAL ENABLE.
This tool is for live endpoint validation only. It calls fetch_raw() + parse()
directly on each collector, bypassing run() (which writes raw payloads to disk).

─── COMPLIANCE STATUS (2026-06-05) ────────────────────────────────────────────

robots.txt checks — REQUIRED before production enablement of T2 sources:

  Source                    Domain                   robots.txt     Status
  ─────────────────────────────────────────────────────────────────────────
  NOVA969   / radiowave     radiowave.com.au         NOT CHECKED    PENDING
  KIIS1027  / radiowave     radiowavemonitor.com     NOT CHECKED    PENDING
  CAPITALFM / online_radio  onlineradiobox.com       NOT CHECKED    PENDING
  HEARTFMUK / heart_html    heart.co.uk              NOT CHECKED    PENDING

  T1 API sources (BBC RMS, iHeart) have no robots.txt — ToS review only.
  T3 ICY stream sources not included — stream URLs unknown (run D8 first).

ToS reviews — PENDING for all sources (VAL-BBC1-006, VAL-HEARTFM-007, etc.).

These PENDING statuses mean NO SOURCE IS APPROVED for production enablement.
The diagnostic is a one-shot read-only probe for developer validation only.
See docs/passes/COMPLIANCE-AND-RETENTION-GUARDRAILS.md §2, §3, §6.

─── HARD EXCLUSIONS ───────────────────────────────────────────────────────────

  - No proxy rotation (proxy_urls must be empty; direct connection only)
  - No robots.txt bypass
  - No headless browsers
  - No Spotify or MusicBrainz enrichment
  - No database writes (SQLAlchemy not imported)
  - No scheduler interaction
  - No audio bytes written to any storage path
  - No evasion of any kind

Note: the underlying build_client() rotates User-Agent headers (pre-existing
behaviour in the codebase). This is flagged as a compliance concern in
COMPLIANCE-AND-RETENTION-GUARDRAILS.md §7 (Spoofing User-Agent). It applies
only to T2 HTML sources. T1 API sources are unaffected.

─── USAGE ─────────────────────────────────────────────────────────────────────

  # All stations (inside the running app container)
  docker exec rmias-app-1 python -m app.tools.diagnose_sources

  # Single station
  docker exec rmias-app-1 python -m app.tools.diagnose_sources --station BBCRADIO1

  # Save raw response bytes to a directory (still no DB writes)
  docker exec rmias-app-1 python -m app.tools.diagnose_sources --save-payloads /tmp/diag

  # List available station names
  docker exec rmias-app-1 python -m app.tools.diagnose_sources --list-stations
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Type

from app.infrastructure.collectors.base import BaseCollector

logger = logging.getLogger("diagnose_sources")

_NS = uuid.NAMESPACE_DNS


# ─── Data types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DiagSource:
    """Static descriptor for one diagnostic source probe."""

    station_call_sign: str
    source_label: str
    seed_id_suffix: str           # appended to "source.{call_sign}." for uuid5
    collector_cls: Type[BaseCollector]
    collector_kwargs: dict[str, Any]
    display_url: str
    robots_txt_status: str        # e.g. "PENDING — not yet checked"
    compliance_note: str


@dataclass
class DiagResult:
    """Result of one diagnostic probe."""

    source: DiagSource
    http_status: int | None = None
    content_type: str | None = None
    byte_size: int = 0
    play_events: list = field(default_factory=list)
    no_track_events: list = field(default_factory=list)
    fetch_error: str | None = None
    parse_error: str | None = None

    @property
    def ok(self) -> bool:
        return self.fetch_error is None and self.parse_error is None

    @property
    def has_tracks(self) -> bool:
        return bool(self.play_events)


# ─── Source catalogue ────────────────────────────────────────────────────────


def _build_catalogue() -> list[DiagSource]:
    """Return the list of sources to probe.

    ICY stream sources are omitted — stream URLs are not yet discovered.
    Run D8 (stream URL discovery) first, then add them here.

    iHeart corrected station IDs:
      WHTZ  seed=614  corrected=1469  (from v2 /api/v2/station/id/614 → search)
      WKSC  seed=821  corrected=849   (from v2 station search)
    The v3 live-meta API is unavailable for all IDs — expected to return 404.
    """
    from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector
    from app.infrastructure.collectors.iheart_now_playing import IHeartNowPlayingCollector
    from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector
    from app.infrastructure.collectors.bbc_radio_1 import BBCRadio1Collector
    from app.infrastructure.collectors.heart_radio import HeartRadioCollector
    from app.infrastructure.collectors.kiis_radiowave import KIISRadiowaveCollector

    return [
        DiagSource(
            station_call_sign="NOVA969",
            source_label="radiowave (radiowave.com.au)",
            seed_id_suffix="radiowave",
            collector_cls=NovaRadiowaveCollector,
            collector_kwargs={"base_url": "https://www.radiowave.com.au/diary", "idds": "11129"},
            display_url="https://www.radiowave.com.au/diary?idds=11129",
            robots_txt_status="PENDING — https://www.radiowave.com.au/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML diary. VAL-NOVA-001 UNVALIDATED (domain discrepancy: "
                "collector uses radiowave.com.au; D5 diagnostic incorrectly tested "
                "radiowavemonitor.com). robots.txt + ToS review required before production."
            ),
        ),
        DiagSource(
            station_call_sign="KIISFM",
            source_label="iheart v3 (expected: 404 — API unavailable)",
            seed_id_suffix="iheart",
            collector_cls=IHeartNowPlayingCollector,
            collector_kwargs={"iheart_station_id": "2501"},
            display_url="https://api.iheart.com/api/v3/live-meta/stream/2501/currentTrack",
            robots_txt_status="N/A — JSON API endpoint (no robots.txt applicable)",
            compliance_note=(
                "T1 iHeart v3 live-meta API. Known-unavailable (404 for all station IDs). "
                "Seeded station_id=2501. This probe is expected to fail — confirms API is gone."
            ),
        ),
        DiagSource(
            station_call_sign="CAPITALFM",
            source_label="online_radio_box",
            seed_id_suffix="online_radio_box",
            collector_cls=OnlineRadioBoxCollector,
            collector_kwargs={"base_url": "https://onlineradiobox.com/uk/capitalfmuk/"},
            display_url="https://onlineradiobox.com/uk/capitalfmuk/",
            robots_txt_status="PENDING — https://onlineradiobox.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML. VAL-CAPUK-ORB-001 UNVALIDATED. robots.txt + ToS review "
                "required. Parser status unknown against live page."
            ),
        ),
        DiagSource(
            station_call_sign="BBCRADIO1",
            source_label="bbc_sounds (rms.api.bbc.co.uk)",
            seed_id_suffix="bbc_sounds",
            collector_cls=BBCRadio1Collector,
            collector_kwargs={},
            display_url="https://rms.api.bbc.co.uk/v2/services/bbc_radio_one/segments/latest",
            robots_txt_status="N/A — official BBC API (no robots.txt applicable)",
            compliance_note=(
                "T1 official BBC RMS API. VAL-BBC1-001 PASSED (endpoint reachable). "
                "Production enablement blocked pending manual ToS review (VAL-BBC1-006). "
                "Diagnostic only — no production enablement without VAL-BBC1-006 PASS."
            ),
        ),
        DiagSource(
            station_call_sign="HEARTFMUK",
            source_label="heart_last_played (heart.co.uk)",
            seed_id_suffix="heart_last_played",
            collector_cls=HeartRadioCollector,
            collector_kwargs={"base_url": "https://www.heart.co.uk/radio/last-played-songs/"},
            display_url="https://www.heart.co.uk/radio/last-played-songs/",
            robots_txt_status="PENDING — https://www.heart.co.uk/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML. VAL-HEARTFM-002 FAILED — CSS selectors drifted. "
                "New classes found: now-playing__wrapper, last_played_songs, song_wrapper, "
                "song__text-content. Parser repair required. robots.txt + ToS check pending."
            ),
        ),
        DiagSource(
            station_call_sign="WHTZ",
            source_label="iheart v3 corrected id=1469 (expected: 404)",
            seed_id_suffix="iheart",
            collector_cls=IHeartNowPlayingCollector,
            collector_kwargs={"iheart_station_id": "1469"},
            display_url="https://api.iheart.com/api/v3/live-meta/stream/1469/currentTrack",
            robots_txt_status="N/A — JSON API endpoint",
            compliance_note=(
                "T1 iHeart v3 live-meta API. Seeded station_id=614; corrected to 1469 "
                "via live iHeart v2 station search. v3 API known-unavailable; expected 404."
            ),
        ),
        DiagSource(
            station_call_sign="WKSC",
            source_label="iheart v3 corrected id=849 (expected: 404)",
            seed_id_suffix="iheart",
            collector_cls=IHeartNowPlayingCollector,
            collector_kwargs={"iheart_station_id": "849"},
            display_url="https://api.iheart.com/api/v3/live-meta/stream/849/currentTrack",
            robots_txt_status="N/A — JSON API endpoint",
            compliance_note=(
                "T1 iHeart v3 live-meta API. Seeded station_id=821; corrected to 849 "
                "via live iHeart v2 station search. v3 API known-unavailable; expected 404."
            ),
        ),
        DiagSource(
            station_call_sign="KIIS1027",
            source_label="radiowave_monitor (radiowavemonitor.com)",
            seed_id_suffix="radiowave",
            collector_cls=KIISRadiowaveCollector,
            collector_kwargs={
                "base_url": "https://www.radiowavemonitor.com/pub_charts/diaries.aspx",
                "idds": "5080",
            },
            display_url="https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080",
            robots_txt_status="PENDING — https://www.radiowavemonitor.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML diary. VAL-KIIS-RAD-001 FAILED (0 tr.diary-row rows). "
                "IDDS=5080 UNVALIDATED — radiowavemonitor.com may not track US stations. "
                "robots.txt + ToS check pending."
            ),
        ),
    ]


# ─── Probe logic ─────────────────────────────────────────────────────────────


async def probe_source(src: DiagSource, save_dir: Path | None) -> DiagResult:
    """Run a single read-only fetch+parse for one source.

    Calls fetch_raw() and parse() directly — does NOT call run(), so no raw
    payload is written to disk and no CollectorRun record is created.
    """
    station_id = uuid.uuid5(_NS, f"station.{src.station_call_sign}")
    source_id = uuid.uuid5(_NS, f"source.{src.station_call_sign}.{src.seed_id_suffix}")

    # storage_root is irrelevant here: we never call _store_payload()
    collector = src.collector_cls(
        source_id=source_id,
        station_id=station_id,
        **src.collector_kwargs,
    )

    # Step 1 — fetch
    try:
        raw_bytes, http_status, content_type = await collector.fetch_raw()
    except Exception as exc:
        return DiagResult(source=src, fetch_error=str(exc))

    # Step 2 — optionally save raw bytes (no DB, no hashing)
    if save_dir is not None:
        label_slug = src.source_label.replace(" ", "_").replace("/", "-")[:40]
        fname = f"{src.station_call_sign}_{label_slug}_{datetime.now(tz=UTC).strftime('%H%M%S')}.bin"
        fpath = save_dir / fname
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(raw_bytes)
            logger.debug("Saved raw payload: %s (%d bytes)", fpath, len(raw_bytes))
        except OSError as exc:
            logger.warning("Could not save payload to %s: %s", fpath, exc)

    # Step 3 — parse (ephemeral run_id — never persisted)
    run_id = uuid.uuid4()
    try:
        play_events, no_track_events = collector.parse(raw_bytes, http_status, run_id)
    except Exception as exc:
        return DiagResult(
            source=src,
            http_status=http_status,
            content_type=content_type,
            byte_size=len(raw_bytes),
            parse_error=str(exc),
        )

    return DiagResult(
        source=src,
        http_status=http_status,
        content_type=content_type,
        byte_size=len(raw_bytes),
        play_events=play_events,
        no_track_events=no_track_events,
    )


# ─── Printing ────────────────────────────────────────────────────────────────


_DIVIDER = "─" * 72
_TICK = "✓"
_CROSS = "✗"
_WARN = "!"


def print_compliance_header() -> None:
    print(_DIVIDER)
    print("TenX Radar — Source Diagnostic (read-only, no DB writes)")
    print(f"Run time: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(_DIVIDER)
    print("COMPLIANCE: robots.txt checks PENDING for all T2 sources.")
    print("No source is approved for production enablement until VAL-* entries")
    print("are recorded as PASS in docs/VALIDATION_REGISTER.md.")
    print(_DIVIDER)


def print_result(result: DiagResult) -> None:
    src = result.source
    station_width = 10
    station = src.station_call_sign.ljust(station_width)
    print(f"\n[{station}] {src.source_label}")
    print(f"  URL  : {src.display_url}")
    print(f"  robots.txt : {src.robots_txt_status}")

    if result.fetch_error:
        print(f"  [{_CROSS}] FETCH ERROR: {result.fetch_error}")
        return

    print(f"  HTTP : {result.http_status}  ({result.byte_size} bytes)")

    if result.parse_error:
        print(f"  [{_CROSS}] PARSE ERROR: {result.parse_error}")
        return

    if result.play_events:
        print(f"  [{_TICK}] TRACKS ({len(result.play_events)}):")
        for i, play in enumerate(result.play_events, 1):
            played_str = (
                play.played_at.strftime("%H:%M:%S")
                if play.played_at
                else "time_unknown"
            )
            print(f"       {i:2d}. {play.raw_artist} — {play.raw_title}  [{played_str}]")
    elif result.no_track_events:
        for ev in result.no_track_events:
            print(f"  [{_WARN}] NO_TRACK: reason={ev.reason}  notes={ev.notes!r}")
    else:
        print(f"  [{_WARN}] NO_EVENTS: parse returned 0 tracks and 0 no-track events")


def print_summary(results: list[DiagResult]) -> None:
    print(f"\n{_DIVIDER}")
    print("SUMMARY")
    print(_DIVIDER)
    any_pass = False
    for r in results:
        if r.fetch_error:
            status = f"FETCH_FAIL  ({r.fetch_error[:60]})"
        elif r.parse_error:
            status = f"PARSE_FAIL  ({r.parse_error[:60]})"
        elif r.has_tracks:
            status = f"OK          {len(r.play_events)} tracks"
            any_pass = True
        elif r.no_track_events:
            reason = r.no_track_events[0].reason if r.no_track_events else "unknown"
            status = f"NO_TRACK    reason={reason}"
        else:
            status = "EMPTY       0 events"
        label = f"{r.source.station_call_sign}/{r.source.seed_id_suffix}"
        print(f"  {label:<35} {status}")

    print(_DIVIDER)
    if any_pass:
        print("At least one source returned parseable tracks.")
    else:
        print("No source returned parseable tracks — see individual results above.")


# ─── Entry point ─────────────────────────────────────────────────────────────


async def main(station_filter: str | None, save_dir: Path | None) -> int:
    """Run all (or filtered) diagnostic probes. Returns exit code."""
    catalogue = _build_catalogue()

    if station_filter:
        upper = station_filter.upper()
        catalogue = [s for s in catalogue if s.station_call_sign == upper]
        if not catalogue:
            valid = sorted({s.station_call_sign for s in _build_catalogue()})
            logger.error(
                "Unknown station %r. Valid call signs: %s",
                station_filter,
                ", ".join(valid),
            )
            return 1

    print_compliance_header()

    results: list[DiagResult] = []
    for src in catalogue:
        logger.info(
            "Probing %s / %s ...",
            src.station_call_sign,
            src.seed_id_suffix,
        )
        result = await probe_source(src, save_dir)
        results.append(result)
        print_result(result)

    print_summary(results)

    any_tracks = any(r.has_tracks for r in results)
    return 0 if any_tracks else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.tools.diagnose_sources",
        description=(
            "Read-only source diagnostic. Fetches and parses each source once, "
            "prints results, exits. No database writes."
        ),
    )
    parser.add_argument(
        "--station",
        metavar="CALL_SIGN",
        help=(
            "Probe only this station (e.g. BBCRADIO1). "
            "Omit to probe all configured stations."
        ),
    )
    parser.add_argument(
        "--save-payloads",
        metavar="DIR",
        help=(
            "Save raw response bytes to DIR (created if absent). "
            "Default: do not save. No DB writes in either mode."
        ),
    )
    parser.add_argument(
        "--list-stations",
        action="store_true",
        help="Print available station call signs and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


def cli() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if args.list_stations:
        call_signs = sorted({s.station_call_sign for s in _build_catalogue()})
        print("Available station call signs:")
        for cs in call_signs:
            print(f"  {cs}")
        sys.exit(0)

    save_dir = Path(args.save_payloads) if args.save_payloads else None
    exit_code = asyncio.run(main(args.station, save_dir))
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
