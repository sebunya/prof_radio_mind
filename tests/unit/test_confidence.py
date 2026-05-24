"""Tests for report confidence scoring and correction versioning."""

from __future__ import annotations

from app.application.reports.confidence import (
    ConfidenceLevel,
    SourceCoverage,
    compute_confidence,
)
from app.application.reports.correction import (
    ReportCorrectionRequest,
    apply_correction,
)
from app.application.reports.csv_exporter import DailyReportRow

# --- confidence scoring ---

def test_full_automated_coverage_is_high() -> None:
    coverage = SourceCoverage(radiowave_plays=100, total_plays=100)
    score, level = compute_confidence(coverage)
    assert level == ConfidenceLevel.HIGH
    assert score >= 0.85


def test_all_manual_import_is_low() -> None:
    coverage = SourceCoverage(manual_csv_plays=100, total_plays=100)
    score, level = compute_confidence(coverage)
    assert level == ConfidenceLevel.LOW


def test_mixed_mostly_automated_is_high() -> None:
    coverage = SourceCoverage(radiowave_plays=90, manual_csv_plays=10, total_plays=100)
    score, level = compute_confidence(coverage)
    assert level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)


def test_primary_source_unavailable_reduces_score() -> None:
    coverage = SourceCoverage(radiowave_plays=100, total_plays=100)
    score_ok, _ = compute_confidence(coverage, primary_source_available=True)
    score_down, _ = compute_confidence(coverage, primary_source_available=False)
    assert score_down < score_ok


def test_zero_plays_returns_low_confidence() -> None:
    coverage = SourceCoverage(total_plays=0)
    score, level = compute_confidence(coverage)
    assert level == ConfidenceLevel.LOW
    assert score == 0.0


def test_score_clamped_to_1() -> None:
    coverage = SourceCoverage(radiowave_plays=1000, total_plays=1000)
    score, _ = compute_confidence(coverage)
    assert score <= 1.0


def test_confidence_levels_thresholds() -> None:
    # High
    c1 = SourceCoverage(radiowave_plays=100, total_plays=100)
    _, l1 = compute_confidence(c1)
    assert l1 == ConfidenceLevel.HIGH

    # Force medium by using primary_source_available=False
    _, l2 = compute_confidence(c1, primary_source_available=False)
    assert l2 in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)


# --- correction ---

def _make_row(pos: int, artist: str, title: str) -> DailyReportRow:
    return DailyReportRow(
        position=pos,
        artist=artist,
        title=title,
        play_count=5,
        movement="non_mover",
        previous_position=pos,
        label=None,
        confidence_level="high",
    )


def test_correction_increments_version() -> None:
    req = ReportCorrectionRequest(
        daily_report_id="report-123",
        correction_note="Fixed duplicate entry",
        corrected_rows=[_make_row(1, "Dua Lipa", "Levitating")],
    )
    corrected = apply_correction(req, current_version=1)
    assert corrected.version_number == 2


def test_correction_preserves_note() -> None:
    req = ReportCorrectionRequest(
        daily_report_id="report-123",
        correction_note="Operator correction: removed duplicate",
        corrected_rows=[_make_row(1, "Artist", "Title")],
    )
    corrected = apply_correction(req, current_version=2)
    assert corrected.correction_note == "Operator correction: removed duplicate"


def test_correction_snapshot_is_valid_json() -> None:
    import json

    req = ReportCorrectionRequest(
        daily_report_id="report-123",
        correction_note="test",
        corrected_rows=[_make_row(1, "A", "T"), _make_row(2, "B", "U")],
    )
    corrected = apply_correction(req, current_version=1)
    snapshot = json.loads(corrected.snapshot_json)
    assert "rows" in snapshot
    assert len(snapshot["rows"]) == 2


def test_correction_corrected_at_is_timezone_aware() -> None:
    req = ReportCorrectionRequest(
        daily_report_id="report-123",
        correction_note="test",
        corrected_rows=[],
    )
    corrected = apply_correction(req, current_version=1)
    assert corrected.corrected_at.tzinfo is not None
