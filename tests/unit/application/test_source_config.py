"""Tests for source config seeds and validation framework."""

from __future__ import annotations

import uuid

import pytest

from app.application.source_config.source_seeds import SOURCE_SEEDS
from app.application.source_config.station_seeds import STATION_SEEDS
from app.application.validation.base import (
    SourceValidationAdapter,
    ValidationResult,
    ValidationStatus,
)
from app.domain.entities.source import SourceType


def test_station_seeds_has_three_stations() -> None:
    assert len(STATION_SEEDS) == 3


def test_station_seeds_call_signs() -> None:
    call_signs = {s.call_sign for s in STATION_SEEDS}
    assert call_signs == {"NOVA969", "KIISFM", "CAPITALFM"}


def test_station_seeds_are_au() -> None:
    for seed in STATION_SEEDS:
        assert seed.country_code == "AU"


def test_nova_has_radiowave_source() -> None:
    nova_sources = [s for s in SOURCE_SEEDS if s.station_call_sign == "NOVA969"]
    types = {s.source_type for s in nova_sources}
    assert SourceType.RADIOWAVE in types


def test_nova_radiowave_idds_config() -> None:
    seed = next(
        s
        for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADIOWAVE
    )
    assert seed.config is not None
    assert seed.config.get("idds") == "11129"


def test_kiis_iheart_station_id_config() -> None:
    seed = next(
        s
        for s in SOURCE_SEEDS
        if s.station_call_sign == "KIISFM" and s.source_type == SourceType.IHEART
    )
    assert seed.config is not None
    assert seed.config.get("station_id") == "2501"


def test_all_stations_have_manual_csv_fallback() -> None:
    for station_call_sign in ("NOVA969", "KIISFM", "CAPITALFM"):
        manual = [
            s
            for s in SOURCE_SEEDS
            if s.station_call_sign == station_call_sign
            and s.source_type == SourceType.MANUAL_CSV
        ]
        assert len(manual) >= 1, f"{station_call_sign} missing manual CSV fallback"


def test_manual_csv_is_lowest_priority() -> None:
    for seed in SOURCE_SEEDS:
        if seed.source_type == SourceType.MANUAL_CSV:
            assert seed.priority > 1, f"Manual CSV for {seed.station_call_sign} must not be primary"


def test_validation_status_values() -> None:
    assert ValidationStatus.VALIDATED == "validated"
    assert ValidationStatus.FAILED == "failed"
    assert ValidationStatus.UNVALIDATED == "unvalidated"


def test_validation_result_defaults_validated_at() -> None:
    result = ValidationResult(
        source_id=uuid.uuid4(),
        validation_code="VAL-NOVA-001",
        status=ValidationStatus.UNVALIDATED,
        notes="test",
    )
    assert result.validated_at is not None
    assert result.validated_at.tzinfo is not None


def test_source_validation_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        SourceValidationAdapter()  # type: ignore[abstract]
