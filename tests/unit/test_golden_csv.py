"""Golden CSV test for daily report export.

The golden file at tests/fixtures/golden/nova969_daily_report_golden.csv
was generated from known input and must not change unless the report
format changes (which requires a version bump).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

from app.application.ranking.engine import apply_movements, build_snapshot
from app.application.reports.csv_exporter import (
    CSVExport,
    build_daily_report_rows,
    export_daily_report_csv,
)

_GOLDEN = Path(__file__).parent.parent / "fixtures/golden/nova969_daily_report_golden.csv"


def _build_test_export() -> bytes:
    plays = (
        [("Dua Lipa", "Levitating")] * 7
        + [("Tame Impala", "The Less I Know The Better")] * 5
        + [("Flume", "Never Be Like You")] * 4
        + [("The Weeknd", "Blinding Lights")] * 3
        + [("Kylie Minogue", "Padam Padam")] * 2
    )
    snap = build_snapshot(plays, "NOVA969", "2026-05-24", top_n=10)

    prev_plays = (
        [("Tame Impala", "The Less I Know The Better")] * 6
        + [("Dua Lipa", "Levitating")] * 4
        + [("Flume", "Never Be Like You")] * 4
        + [("The Weeknd", "Blinding Lights")] * 3
    )
    prev = build_snapshot(prev_plays, "NOVA969", "2026-05-23", top_n=10)
    snap = apply_movements(snap, prev)

    label_map = {
        "Dua Lipa|Levitating": "Warner Records",
        "Tame Impala|The Less I Know The Better": "Island Records",
        "Flume|Never Be Like You": "Future Classic",
        "The Weeknd|Blinding Lights": "Republic Records",
        "Kylie Minogue|Padam Padam": "BMG",
    }
    rows = build_daily_report_rows(snap.entries, confidence_level="high", label_map=label_map)
    export = CSVExport(
        station_call_sign="NOVA969",
        report_date=date(2026, 5, 24),
        version=1,
        confidence_level="high",
        rows=rows,
    )
    return export_daily_report_csv(export)


def test_golden_csv_matches() -> None:
    actual_bytes = _build_test_export()
    expected_bytes = _GOLDEN.read_bytes()
    assert actual_bytes == expected_bytes, (
        "Golden CSV mismatch — if the report format changed intentionally, "
        "regenerate the golden file and bump export_version."
    )


def test_golden_csv_has_expected_columns() -> None:
    csv_bytes = _build_test_export()
    reader = csv.DictReader(io.StringIO(csv_bytes.decode()))
    assert reader.fieldnames is not None
    required = {"position", "artist", "title", "play_count", "movement", "confidence_level"}
    assert required <= set(reader.fieldnames)


def test_golden_csv_position_1_is_dua_lipa() -> None:
    csv_bytes = _build_test_export()
    reader = csv.DictReader(io.StringIO(csv_bytes.decode()))
    rows = list(reader)
    assert rows[0]["position"] == "1"
    assert rows[0]["artist"] == "Dua Lipa"


def test_golden_csv_movements_correct() -> None:
    csv_bytes = _build_test_export()
    reader = csv.DictReader(io.StringIO(csv_bytes.decode()))
    movements = {row["artist"]: row["movement"] for row in reader}
    assert movements["Dua Lipa"] == "up"
    assert movements["Tame Impala"] == "down"
    assert movements["Kylie Minogue"] == "new_entry"
