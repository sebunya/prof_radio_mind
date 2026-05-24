"""Manual CSV import scaffold — full implementation in Pass 9.

This module defines the data structures and interface contract that
Pass 9 will implement. Capital FM uses manual CSV as its primary source
until an automated route is validated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class ImportStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ImportBatch:
    id: uuid.UUID
    station_id: uuid.UUID
    filename: str
    status: ImportStatus = ImportStatus.PENDING
    total_rows: int = 0
    imported_rows: int = 0
    error_rows: int = 0
    errors: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, station_id: uuid.UUID, filename: str) -> ImportBatch:
        return cls(id=uuid.uuid4(), station_id=station_id, filename=filename)


# Expected CSV columns for manual import
REQUIRED_CSV_COLUMNS: tuple[str, ...] = (
    "played_at",
    "artist",
    "title",
)

OPTIONAL_CSV_COLUMNS: tuple[str, ...] = (
    "label",
    "source_event_id",
    "notes",
)
