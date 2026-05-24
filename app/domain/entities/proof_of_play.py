"""Proof-of-Play domain entity — airplay certificate for publishers/labels."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass
class AirplayCertificate:
    id: uuid.UUID
    station_id: uuid.UUID
    station_call_sign: str
    artist: str
    title: str
    report_date: date
    play_count: int
    # Certifying entity — the operator or system that signs this certificate
    certified_by: str
    issued_at: datetime
    # SHA-256 fingerprint of the certificate content for tamper detection
    content_hash: str

    @classmethod
    def create(
        cls,
        station_id: uuid.UUID,
        station_call_sign: str,
        artist: str,
        title: str,
        report_date: date,
        play_count: int,
        certified_by: str = "RMIAS",
    ) -> AirplayCertificate:
        issued_at = datetime.now(tz=UTC)
        content = (
            f"{station_call_sign}|{artist}|{title}|{report_date}|{play_count}|{issued_at.isoformat()}"
        )
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return cls(
            id=uuid.uuid4(),
            station_id=station_id,
            station_call_sign=station_call_sign,
            artist=artist,
            title=title,
            report_date=report_date,
            play_count=play_count,
            certified_by=certified_by,
            issued_at=issued_at,
            content_hash=content_hash,
        )

    def to_dict(self) -> dict:
        return {
            "certificate_id": str(self.id),
            "station_id": str(self.station_id),
            "station": self.station_call_sign,
            "artist": self.artist,
            "title": self.title,
            "report_date": self.report_date.isoformat(),
            "play_count": self.play_count,
            "certified_by": self.certified_by,
            "issued_at": self.issued_at.isoformat(),
            "content_hash": self.content_hash,
        }
