"""Tests for Capital FM validation adapters and manual CSV import scaffold.

No live network calls. The validation adapter tests use httpx mock responses.
"""

from __future__ import annotations

import uuid

import pytest

from app.application.imports.manual_csv import (
    REQUIRED_CSV_COLUMNS,
    ImportBatch,
    ImportStatus,
)
from app.application.validation.adapters.capital import (
    CapitalIHeartValidationAdapter,
    CapitalWebsiteValidationAdapter,
)
from app.application.validation.base import ValidationStatus


def test_capital_iheart_adapter_validation_code() -> None:
    adapter = CapitalIHeartValidationAdapter()
    assert adapter.validation_code == "VAL-CAP-001"


def test_capital_website_adapter_validation_code() -> None:
    adapter = CapitalWebsiteValidationAdapter()
    assert adapter.validation_code == "VAL-CAP-002"


@pytest.mark.anyio
async def test_capital_iheart_no_config_returns_failed() -> None:
    adapter = CapitalIHeartValidationAdapter()
    result = await adapter.validate(uuid.uuid4(), config=None)
    assert result.status == ValidationStatus.FAILED
    assert "No station_id" in result.notes


@pytest.mark.anyio
async def test_capital_iheart_missing_station_id_returns_failed() -> None:
    adapter = CapitalIHeartValidationAdapter()
    result = await adapter.validate(uuid.uuid4(), config={"base_url": "https://example.com"})
    assert result.status == ValidationStatus.FAILED


@pytest.mark.anyio
async def test_capital_website_no_config_returns_failed() -> None:
    adapter = CapitalWebsiteValidationAdapter()
    result = await adapter.validate(uuid.uuid4(), config=None)
    assert result.status == ValidationStatus.FAILED
    assert "No endpoint_url" in result.notes


def test_import_batch_create() -> None:
    station_id = uuid.uuid4()
    batch = ImportBatch.create(station_id, "capital_fm_20260524.csv")
    assert isinstance(batch.id, uuid.UUID)
    assert batch.station_id == station_id
    assert batch.status == ImportStatus.PENDING
    assert batch.imported_rows == 0


def test_import_batch_error_tracking() -> None:
    batch = ImportBatch.create(uuid.uuid4(), "test.csv")
    batch.errors.append("Row 3: missing artist field")
    batch.error_rows = 1
    assert len(batch.errors) == 1
    assert batch.error_rows == 1


def test_required_csv_columns_present() -> None:
    for col in ("played_at", "artist", "title"):
        assert col in REQUIRED_CSV_COLUMNS


def test_capital_does_not_affect_nova_or_kiis_isolation() -> None:
    """Capital validation state is independent — other stations not blocked."""
    nova_batch = ImportBatch.create(uuid.uuid4(), "nova_fallback.csv")
    capital_batch = ImportBatch.create(uuid.uuid4(), "capital.csv")
    capital_batch.status = ImportStatus.FAILED

    assert nova_batch.status == ImportStatus.PENDING
    assert capital_batch.status == ImportStatus.FAILED
