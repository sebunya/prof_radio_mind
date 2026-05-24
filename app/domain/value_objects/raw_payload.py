from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class RawPayload:
    id: uuid.UUID
    collector_run_id: uuid.UUID
    source_id: uuid.UUID
    sha256: str
    storage_path: str
    content_type: str | None
    byte_size: int
    http_status: int | None
    fetched_at: datetime

    @classmethod
    def create(
        cls,
        collector_run_id: uuid.UUID,
        source_id: uuid.UUID,
        raw_bytes: bytes,
        storage_path: str,
        *,
        content_type: str | None = None,
        http_status: int | None = None,
        fetched_at: datetime | None = None,
    ) -> RawPayload:

        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        return cls(
            id=uuid.uuid4(),
            collector_run_id=collector_run_id,
            source_id=source_id,
            sha256=sha256,
            storage_path=storage_path,
            content_type=content_type,
            byte_size=len(raw_bytes),
            http_status=http_status,
            fetched_at=fetched_at or datetime.now(tz=UTC),
        )
