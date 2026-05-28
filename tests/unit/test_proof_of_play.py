"""Tests for proof-of-play certificates — pure transformation, no DB."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from app.application.proof_of_play.certificate_service import (
    export_certificates_csv,
    generate_certificates,
)
from app.domain.entities.proof_of_play import AirplayCertificate

_STATION_ID = uuid.uuid4()
_DATE = date(2026, 5, 24)


# --- AirplayCertificate.create ---

def test_certificate_create_fields() -> None:
    cert = AirplayCertificate.create(
        station_id=_STATION_ID,
        station_call_sign="NOVA",
        artist="The Wiggles",
        title="Hot Potato",
        report_date=_DATE,
        play_count=7,
    )
    assert cert.station_call_sign == "NOVA"
    assert cert.artist == "The Wiggles"
    assert cert.title == "Hot Potato"
    assert cert.play_count == 7
    assert cert.certified_by == "RMIAS"
    assert isinstance(cert.id, uuid.UUID)
    assert cert.issued_at is not None


def test_certificate_content_hash_is_sha256_hex() -> None:
    cert = AirplayCertificate.create(
        station_id=_STATION_ID,
        station_call_sign="NOVA",
        artist="A",
        title="B",
        report_date=_DATE,
        play_count=1,
    )
    assert len(cert.content_hash) == 64
    assert all(c in "0123456789abcdef" for c in cert.content_hash)


def test_certificate_different_content_different_hash() -> None:
    cert1 = AirplayCertificate.create(
        station_id=_STATION_ID, station_call_sign="NOVA",
        artist="A", title="B", report_date=_DATE, play_count=1,
    )
    cert2 = AirplayCertificate.create(
        station_id=_STATION_ID, station_call_sign="NOVA",
        artist="A", title="B", report_date=_DATE, play_count=99,
    )
    assert cert1.content_hash != cert2.content_hash


def test_certificate_to_dict_has_required_keys() -> None:
    cert = AirplayCertificate.create(
        station_id=_STATION_ID, station_call_sign="KIIS",
        artist="A", title="B", report_date=_DATE, play_count=3,
    )
    d = cert.to_dict()
    for key in ("certificate_id", "station_id", "station", "artist", "title",
                "report_date", "play_count", "certified_by", "issued_at", "content_hash"):
        assert key in d, f"Missing key: {key}"


# --- generate_certificates ---

def test_generate_certificates_creates_one_per_song() -> None:
    ranked = [("A", "T1", 5), ("B", "T2", 3)]
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, ranked)
    assert len(certs) == 2


def test_generate_certificates_skips_zero_plays() -> None:
    ranked = [("A", "T1", 5), ("B", "T2", 0)]
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, ranked)
    assert len(certs) == 1
    assert certs[0].artist == "A"


def test_generate_certificates_empty_input() -> None:
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, [])
    assert certs == []


def test_generate_certificates_custom_certifier() -> None:
    ranked = [("A", "T1", 5)]
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, ranked, certified_by="ACME")
    assert certs[0].certified_by == "ACME"


# --- export_certificates_csv ---

def test_export_csv_has_header() -> None:
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, [("A", "T", 3)])
    csv_bytes = export_certificates_csv(certs)
    text = csv_bytes.decode("utf-8")
    assert "certificate_id" in text
    assert "content_hash" in text


def test_export_csv_row_count() -> None:
    ranked = [("A", "T1", 5), ("B", "T2", 3), ("C", "T3", 1)]
    certs = generate_certificates(_STATION_ID, "NOVA", _DATE, ranked)
    csv_bytes = export_certificates_csv(certs)
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"))))
    # 1 header + 3 data rows
    assert len(rows) == 4


def test_export_csv_empty_certs() -> None:
    csv_bytes = export_certificates_csv([])
    text = csv_bytes.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == 1  # header only
