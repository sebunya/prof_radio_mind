"""Diagnostic CLI — single read-only fetch per source, prints parsed songs, exits.

NO DATABASE WRITES. NO DISK WRITES BY DEFAULT. NO SCHEDULER. NO GLOBAL ENABLE.
This tool is for live endpoint validation only. It calls fetch_raw() + parse()
directly on each collector, bypassing run() (which writes raw payloads to disk).

─── STATIONS AND SOURCES ──────────────────────────────────────────────────────

  Station     Source                  robots.txt     Status
  ─────────────────────────────────────────────────────────
  NOVA969     radiowave               PENDING        VAL-NOVA-001
  NOVA969     radoxo                  PENDING        VAL-NOVA-RADOXO-001
  NOVA969     radio_australia_org     PENDING        VAL-NOVA-RAO-001
  CAPITALFM   online_radio_box        PENDING        VAL-CAPUK-ORB-001
  CAPITALFM   ukradiolive             PENDING        VAL-CAPUK-URL-001
  KIIS1027    iheart_web              PENDING        VAL-KIIS1027-WEB-001
  KIIS1027    radiowave               PENDING        VAL-KIIS-RAD-001 (FAILED)

PENDING statuses mean NO SOURCE IS APPROVED for production enablement.
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
  docker exec rmias-app-1 python -m app.tools.diagnose_sources --station NOVA969

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
from typing import Any

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
    collector_cls: type[BaseCollector]
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
    """Return the list of sources to probe."""
    from app.infrastructure.collectors.capital_ukradiolive import CapitalUKRadioLiveCollector
    from app.infrastructure.collectors.kiis_iheart_web import KIISIHeartWebCollector
    from app.infrastructure.collectors.kiis_radiowave import KIISRadiowaveCollector
    from app.infrastructure.collectors.nova_radoxo import NovaRadoxoCollector
    from app.infrastructure.collectors.nova_radiowave import NovaRadiowaveCollector
    from app.infrastructure.collectors.online_radio_box import OnlineRadioBoxCollector
    from app.infrastructure.collectors.radio_australia_org import RadioAustraliaOrgCollector

    return [
        # --- Nova 96.9 ---
        DiagSource(
            station_call_sign="NOVA969",
            source_label="radiowave (radiowavemonitor.com IDDS=11129)",
            seed_id_suffix="radiowave",
            collector_cls=NovaRadiowaveCollector,
            collector_kwargs={},
            display_url="https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=11129",
            robots_txt_status="PENDING — https://www.radiowavemonitor.com/robots.txt not checked",
            compliance_note=(
                "T2 public HTML diary. VAL-NOVA-001: URL corrected to radiowavemonitor.com. "
                "Card-grid parser (Strategy 3) confirmed on real HTML 2026-06-06. "
                "robots.txt + ToS review required before production enablement."
            ),
        ),
        DiagSource(
            station_call_sign="NOVA969",
            source_label="radoxo (radoxo.com/australia/nova-969/playlist)",
            seed_id_suffix="radoxo",
            collector_cls=NovaRadoxoCollector,
            collector_kwargs={},
            display_url="https://radoxo.com/australia/nova-969/playlist",
            robots_txt_status="PENDING — https://radoxo.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML. VAL-NOVA-RADOXO-001: li.playlist-track + data-ts "
                "Unix timestamps confirmed 2026-06-06. 86+ tracks/day. "
                "robots.txt + ToS review required."
            ),
        ),
        DiagSource(
            station_call_sign="NOVA969",
            source_label="radio_australia_org (radio-australia.org/nova-969)",
            seed_id_suffix="radio_australia_org",
            collector_cls=RadioAustraliaOrgCollector,
            collector_kwargs={"url": "https://www.radio-australia.org/nova-969"},
            display_url="https://www.radio-australia.org/nova-969",
            robots_txt_status="PENDING — https://www.radio-australia.org/robots.txt not checked",
            compliance_note=(
                "T2 SSR chart. VAL-NOVA-RAO-001: confirmed 2026-06-06. "
                "played_at is synthetic (collection timestamp, not broadcast time). "
                "robots.txt + ToS review required."
            ),
        ),
        # --- Capital FM UK ---
        DiagSource(
            station_call_sign="CAPITALFM",
            source_label="online_radio_box (onlineradiobox.com)",
            seed_id_suffix="online_radio_box",
            collector_cls=OnlineRadioBoxCollector,
            collector_kwargs={"base_url": "https://onlineradiobox.com/uk/capitalfmuk/playlist/"},
            display_url="https://onlineradiobox.com/uk/capitalfmuk/playlist/",
            robots_txt_status="PENDING — https://onlineradiobox.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML. VAL-CAPUK-ORB-001 UNVALIDATED. URL updated to playlist path. "
                "robots.txt + ToS review required."
            ),
        ),
        DiagSource(
            station_call_sign="CAPITALFM",
            source_label="ukradiolive (ukradiolive.com/capital-fm/playlist)",
            seed_id_suffix="ukradiolive",
            collector_cls=CapitalUKRadioLiveCollector,
            collector_kwargs={},
            display_url="https://ukradiolive.com/capital-fm/playlist",
            robots_txt_status="PENDING — https://ukradiolive.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public HTML. VAL-CAPUK-URL-001: plist-item parser confirmed on real HTML "
                "2026-06-06. robots.txt + ToS review required."
            ),
        ),
        # --- KIIS-FM 102.7 Los Angeles ---
        DiagSource(
            station_call_sign="KIIS1027",
            source_label="iheart_web (kiisfm.iheart.com/music/recently-played/)",
            seed_id_suffix="iheart_web",
            collector_cls=KIISIHeartWebCollector,
            collector_kwargs={},
            display_url="https://kiisfm.iheart.com/music/recently-played/",
            robots_txt_status="PENDING — https://kiisfm.iheart.com/robots.txt not yet checked",
            compliance_note=(
                "T2 public station website. VAL-KIIS1027-WEB-001: figcaption parser confirmed "
                "on real HTML 2026-06-06. robots.txt + ToS review required."
            ),
        ),
        DiagSource(
            station_call_sign="KIIS1027",
            source_label="radiowave (radiowavemonitor.com IDDS=5080)",
            seed_id_suffix="radiowave",
            collector_cls=KIISRadiowaveCollector,
            collector_kwargs={},
            display_url="https://www.radiowavemonitor.com/pub_charts/diaries.aspx?IDDS=5080",
            robots_txt_status="PENDING — https://www.radiowavemonitor.com/robots.txt not checked",
            compliance_note=(
                "T2 public HTML diary. VAL-KIIS-RAD-001 FAILED (0 tr.diary-row rows). "
                "IDDS=5080 may not be tracked by radiowavemonitor.com. "
                "robots.txt + ToS check pending. Selector fix required."
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
        ts = datetime.now(tz=UTC).strftime("%H%M%S")
        fname = f"{src.station_call_sign}_{label_slug}_{ts}.bin"
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
