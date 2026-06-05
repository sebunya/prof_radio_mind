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


def test_station_seeds_has_eight_stations() -> None:
    assert len(STATION_SEEDS) == 8


def test_station_seeds_call_signs() -> None:
    call_signs = {s.call_sign for s in STATION_SEEDS}
    assert call_signs == {
        "NOVA969", "KIISFM", "CAPITALFM",
        "BBCRADIO1", "HEARTFMUK", "WHTZ", "WKSC",
        "KIIS1027",
    }


def test_station_seeds_countries() -> None:
    au_stations = {"NOVA969", "KIISFM"}
    gb_stations = {"CAPITALFM", "BBCRADIO1", "HEARTFMUK"}
    us_stations = {"WHTZ", "WKSC", "KIIS1027"}
    for seed in STATION_SEEDS:
        if seed.call_sign in au_stations:
            assert seed.country_code == "AU"
        elif seed.call_sign in gb_stations:
            assert seed.country_code == "GB"
        elif seed.call_sign in us_stations:
            assert seed.country_code == "US"


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
    for station_call_sign in (
        "NOVA969", "KIISFM", "CAPITALFM",
        "BBCRADIO1", "HEARTFMUK", "WHTZ", "WKSC",
        "KIIS1027",
    ):
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


# --- EXTRACT-2: new source type values ---

def test_bbc_sounds_source_type_parses() -> None:
    assert SourceType("bbc_sounds") == SourceType.BBC_SOUNDS
    assert SourceType.BBC_SOUNDS.value == "bbc_sounds"


def test_heart_last_played_source_type_parses() -> None:
    assert SourceType("heart_last_played") == SourceType.HEART_LAST_PLAYED
    assert SourceType.HEART_LAST_PLAYED.value == "heart_last_played"


def test_bbc_radio1_has_bbc_sounds_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "BBCRADIO1"]
    types = {s.source_type for s in seeds}
    assert SourceType.BBC_SOUNDS in types


def test_heartfmuk_has_heart_last_played_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "HEARTFMUK"]
    types = {s.source_type for s in seeds}
    assert SourceType.HEART_LAST_PLAYED in types


def test_z100_iheart_station_id_config() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "WHTZ" and s.source_type == SourceType.IHEART
    )
    assert seed.config is not None
    assert seed.config.get("station_id") == "614"


def test_wksc_iheart_station_id_config() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "WKSC" and s.source_type == SourceType.IHEART
    )
    assert seed.config is not None
    assert seed.config.get("station_id") == "821"


# --- EXTRACT-2: UUID match — seeder derivation must match scheduler constants ---

def test_bbcradio1_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _BBC1_STATION_ID
    assert station_id_for("BBCRADIO1") == _BBC1_STATION_ID


def test_bbcradio1_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _BBC1_SOURCE_ID
    assert source_id_for("BBCRADIO1", "bbc_sounds") == _BBC1_SOURCE_ID


def test_heartfmuk_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _HEARTFM_STATION_ID
    assert station_id_for("HEARTFMUK") == _HEARTFM_STATION_ID


def test_heartfmuk_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _HEARTFM_SOURCE_ID
    assert source_id_for("HEARTFMUK", "heart_last_played") == _HEARTFM_SOURCE_ID


def test_whtz_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _Z100_STATION_ID
    assert station_id_for("WHTZ") == _Z100_STATION_ID


def test_whtz_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _Z100_SOURCE_ID
    assert source_id_for("WHTZ", "iheart") == _Z100_SOURCE_ID


def test_wksc_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _WKSC_STATION_ID
    assert station_id_for("WKSC") == _WKSC_STATION_ID


def test_wksc_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _WKSC_SOURCE_ID
    assert source_id_for("WKSC", "iheart") == _WKSC_SOURCE_ID


# --- EXTRACT-3: KIIS-FM 102.7 Los Angeles ---

def test_kiis1027_has_radiowave_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "KIIS1027"]
    types = {s.source_type for s in seeds}
    assert SourceType.RADIOWAVE in types


def test_kiis1027_radiowave_idds_config() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "KIIS1027" and s.source_type == SourceType.RADIOWAVE
    )
    assert seed.config is not None
    assert seed.config.get("idds") == "5080"


def test_kiis1027_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _KIIS1027_STATION_ID
    assert station_id_for("KIIS1027") == _KIIS1027_STATION_ID


def test_kiis1027_radiowave_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _KIIS1027_RADIOWAVE_SOURCE_ID
    assert source_id_for("KIIS1027", "radiowave") == _KIIS1027_RADIOWAVE_SOURCE_ID
