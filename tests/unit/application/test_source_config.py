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
    assert call_signs == {"NOVA969", "CAPITALFM", "KIIS1027"}


def test_station_seeds_countries() -> None:
    au_stations = {"NOVA969"}
    gb_stations = {"CAPITALFM"}
    us_stations = {"KIIS1027"}
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


def test_all_stations_have_manual_csv_fallback() -> None:
    for station_call_sign in ("NOVA969", "CAPITALFM", "KIIS1027"):
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


# --- Source type enum values ---

def test_iheart_web_source_type_parses() -> None:
    assert SourceType("iheart_web") == SourceType.IHEART_WEB
    assert SourceType.IHEART_WEB.value == "iheart_web"


def test_ukradiolive_source_type_parses() -> None:
    assert SourceType("ukradiolive") == SourceType.UKRADIOLIVE
    assert SourceType.UKRADIOLIVE.value == "ukradiolive"


def test_radoxo_source_type_parses() -> None:
    assert SourceType("radoxo") == SourceType.RADOXO
    assert SourceType.RADOXO.value == "radoxo"


def test_radio_australia_org_source_type_parses() -> None:
    assert SourceType("radio_australia_org") == SourceType.RADIO_AUSTRALIA_ORG
    assert SourceType.RADIO_AUSTRALIA_ORG.value == "radio_australia_org"


# --- Nova 96.9 source coverage ---

def test_nova_radiowave_url_corrected() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADIOWAVE
    )
    assert seed.base_url is not None
    assert "radiowavemonitor.com" in seed.base_url


def test_nova969_has_radoxo_fallback() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "NOVA969"]
    types = {s.source_type for s in seeds}
    assert SourceType.RADOXO in types


def test_nova969_radoxo_has_correct_url() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADOXO
    )
    assert seed.base_url is not None
    assert "radoxo.com" in seed.base_url
    assert "nova-969" in seed.base_url


def test_nova969_radoxo_validation_note_confirmed() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADOXO
    )
    assert "VALIDATED" in seed.validation_note


def test_nova969_radoxo_is_lower_priority_than_radiowave() -> None:
    rw = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADIOWAVE
    )
    radoxo = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADOXO
    )
    assert radoxo.priority > rw.priority


def test_nova969_has_radio_australia_org_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "NOVA969"]
    types = {s.source_type for s in seeds}
    assert SourceType.RADIO_AUSTRALIA_ORG in types


def test_nova969_radio_australia_is_priority_3() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADIO_AUSTRALIA_ORG
    )
    assert seed.priority == 3


def test_nova969_radio_australia_url_correct() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "NOVA969" and s.source_type == SourceType.RADIO_AUSTRALIA_ORG
    )
    assert seed.base_url is not None
    assert "radio-australia.org" in seed.base_url
    assert "nova-969" in seed.base_url


# --- Capital FM UK source coverage ---

def test_capitalfm_has_ukradiolive_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "CAPITALFM"]
    types = {s.source_type for s in seeds}
    assert SourceType.UKRADIOLIVE in types


def test_capitalfm_ukradiolive_is_priority_1() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "CAPITALFM" and s.source_type == SourceType.UKRADIOLIVE
    )
    assert seed.priority == 1


def test_capitalfm_online_radio_box_uses_playlist_url() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "CAPITALFM" and s.source_type == SourceType.ONLINE_RADIO_BOX
    )
    assert seed.base_url is not None
    assert "playlist" in seed.base_url


# --- KIIS-FM 102.7 Los Angeles source coverage ---

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


def test_kiis1027_has_iheart_web_source() -> None:
    seeds = [s for s in SOURCE_SEEDS if s.station_call_sign == "KIIS1027"]
    types = {s.source_type for s in seeds}
    assert SourceType.IHEART_WEB in types


def test_kiis1027_iheart_web_is_priority_1() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "KIIS1027" and s.source_type == SourceType.IHEART_WEB
    )
    assert seed.priority == 1


def test_kiis1027_radiowave_demoted_to_priority_2() -> None:
    seed = next(
        s for s in SOURCE_SEEDS
        if s.station_call_sign == "KIIS1027" and s.source_type == SourceType.RADIOWAVE
    )
    assert seed.priority == 2


# --- UUID match: seeder derivation must match scheduler constants ---

def test_nova_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _NOVA_STATION_ID
    assert station_id_for("NOVA969") == _NOVA_STATION_ID


def test_nova_radiowave_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _NOVA_RADIOWAVE_SOURCE_ID
    assert source_id_for("NOVA969", "radiowave") == _NOVA_RADIOWAVE_SOURCE_ID


def test_nova_radoxo_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _NOVA_RADOXO_SOURCE_ID
    assert source_id_for("NOVA969", "radoxo") == _NOVA_RADOXO_SOURCE_ID


def test_nova_rao_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _NOVA_RAO_SOURCE_ID
    assert source_id_for("NOVA969", "radio_australia_org") == _NOVA_RAO_SOURCE_ID


def test_capital_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _CAPITAL_STATION_ID
    assert station_id_for("CAPITALFM") == _CAPITAL_STATION_ID


def test_capital_ukradiolive_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _CAPITAL_UKRADIOLIVE_SOURCE_ID
    assert source_id_for("CAPITALFM", "ukradiolive") == _CAPITAL_UKRADIOLIVE_SOURCE_ID


def test_kiis1027_station_uuid_matches_scheduler() -> None:
    from app.application.seeder import station_id_for
    from app.infrastructure.scheduler.scheduler import _KIIS1027_STATION_ID
    assert station_id_for("KIIS1027") == _KIIS1027_STATION_ID


def test_kiis1027_radiowave_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _KIIS1027_RADIOWAVE_SOURCE_ID
    assert source_id_for("KIIS1027", "radiowave") == _KIIS1027_RADIOWAVE_SOURCE_ID


def test_kiis1027_iheart_web_source_uuid_matches_scheduler() -> None:
    from app.application.seeder import source_id_for
    from app.infrastructure.scheduler.scheduler import _KIIS1027_IHEART_WEB_SOURCE_ID
    assert source_id_for("KIIS1027", "iheart_web") == _KIIS1027_IHEART_WEB_SOURCE_ID
