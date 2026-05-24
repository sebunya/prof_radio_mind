"""Tests for the manual CSV import pipeline."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.application.imports.csv_importer import (
    import_csv,
    validate_csv_schema,
)
from app.application.imports.manual_csv import ImportStatus

_VALID_CSV = Path(__file__).parent.parent.parent / "fixtures/csv/capital_fm_valid.csv"
_ERRORS_CSV = Path(__file__).parent.parent.parent / "fixtures/csv/capital_fm_with_errors.csv"


def _ids() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def test_valid_csv_imports_all_rows() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(
        _VALID_CSV.read_bytes(), station_id, source_id, run_id, "capital_fm_valid.csv"
    )

    assert result.batch.status == ImportStatus.COMPLETED
    assert len(result.play_events) == 5
    assert len(result.row_errors) == 0


def test_valid_csv_attributed_to_station() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_VALID_CSV.read_bytes(), station_id, source_id, run_id)

    for ev in result.play_events:
        assert ev.station_id == station_id
        assert ev.source_id == source_id


def test_valid_csv_played_at_is_timezone_aware() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_VALID_CSV.read_bytes(), station_id, source_id, run_id)

    for ev in result.play_events:
        assert ev.played_at.tzinfo is not None


def test_valid_csv_source_event_id_extracted() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_VALID_CSV.read_bytes(), station_id, source_id, run_id)
    post_malone = next(e for e in result.play_events if "Post" in e.raw_artist)
    assert post_malone.source_event_id == "cap-manual-001"


def test_csv_with_errors_returns_partial_status() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_ERRORS_CSV.read_bytes(), station_id, source_id, run_id, "errors.csv")

    assert result.batch.status == ImportStatus.PARTIAL
    assert result.batch.imported_rows > 0
    assert result.batch.error_rows > 0


def test_csv_with_errors_valid_rows_still_imported() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_ERRORS_CSV.read_bytes(), station_id, source_id, run_id)

    artists = {e.raw_artist for e in result.play_events}
    assert "Doja Cat" in artists
    assert "Olivia Rodrigo" in artists


def test_csv_with_errors_invalid_rows_produce_error_records() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_ERRORS_CSV.read_bytes(), station_id, source_id, run_id)

    assert len(result.row_errors) > 0
    # Row with missing played_at
    missing_date_errors = [e for e in result.row_errors if "played_at is empty" in e.error]
    assert len(missing_date_errors) >= 1


def test_csv_with_invalid_date_produces_error_record() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(_ERRORS_CSV.read_bytes(), station_id, source_id, run_id)

    date_parse_errors = [e for e in result.row_errors if "Cannot parse" in e.error]
    assert len(date_parse_errors) >= 1


def test_schema_validation_missing_column() -> None:
    missing = validate_csv_schema(["artist", "title"])  # missing played_at
    assert "played_at" in missing


def test_schema_validation_all_present() -> None:
    missing = validate_csv_schema(["played_at", "artist", "title", "label"])
    assert missing == []


def test_missing_required_columns_returns_failed_batch() -> None:
    bad_csv = b"artist,title\nDoja Cat,Paint The Town Red\n"
    station_id, source_id, run_id = _ids()
    result = import_csv(bad_csv, station_id, source_id, run_id)

    assert result.batch.status == ImportStatus.FAILED
    assert len(result.batch.errors) > 0


def test_empty_csv_returns_failed_batch() -> None:
    station_id, source_id, run_id = _ids()
    result = import_csv(b"", station_id, source_id, run_id)
    assert result.batch.status == ImportStatus.FAILED


def test_all_rows_invalid_returns_failed_batch() -> None:
    all_bad = b"played_at,artist,title\n,,\n,,\n"
    station_id, source_id, run_id = _ids()
    result = import_csv(all_bad, station_id, source_id, run_id)
    assert result.batch.status == ImportStatus.FAILED
    assert result.batch.imported_rows == 0
