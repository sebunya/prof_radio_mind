"""Proof-of-Play certificate service.

Generates airplay certificates from daily report data.
No DB calls — pure transformation from ranked play events.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from app.domain.entities.proof_of_play import AirplayCertificate


def generate_certificates(
    station_id: uuid.UUID,
    station_call_sign: str,
    report_date: date,
    ranked_plays: list[tuple[str, str, int]],
    certified_by: str = "RMIAS",
) -> list[AirplayCertificate]:
    """Generate one certificate per song entry.

    Args:
        station_id: Station UUID
        station_call_sign: Human-readable call sign for the certificate
        report_date: The broadcast date being certified
        ranked_plays: List of (artist, title, play_count) tuples
        certified_by: Certifying entity name
    """
    return [
        AirplayCertificate.create(
            station_id=station_id,
            station_call_sign=station_call_sign,
            artist=artist,
            title=title,
            report_date=report_date,
            play_count=play_count,
            certified_by=certified_by,
        )
        for artist, title, play_count in ranked_plays
        if play_count > 0
    ]


def export_certificates_csv(certs: list[AirplayCertificate]) -> bytes:
    """Serialise certificates to CSV bytes (APRA/AMCOS-compatible layout)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "certificate_id",
        "station",
        "artist",
        "title",
        "report_date",
        "play_count",
        "certified_by",
        "issued_at",
        "content_hash",
    ])
    for cert in certs:
        writer.writerow([
            str(cert.id),
            cert.station_call_sign,
            cert.artist,
            cert.title,
            cert.report_date.isoformat(),
            cert.play_count,
            cert.certified_by,
            cert.issued_at.isoformat(),
            cert.content_hash,
        ])
    return buf.getvalue().encode("utf-8")
