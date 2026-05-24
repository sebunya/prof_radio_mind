from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ValidationStatus(StrEnum):
    VALIDATED = "validated"
    FAILED = "failed"
    UNVALIDATED = "unvalidated"
    DEFERRED = "deferred"


@dataclass
class ValidationResult:
    source_id: uuid.UUID
    validation_code: str
    status: ValidationStatus
    notes: str
    response_status_code: int | None = None
    response_snapshot: dict | None = None
    validated_at: datetime = None  # type: ignore[assignment]
    validated_by: str = "system"

    def __post_init__(self) -> None:
        if self.validated_at is None:
            self.validated_at = datetime.now(tz=UTC)


class SourceValidationAdapter(ABC):
    """Abstract base for all source validation adapters.

    Each adapter is responsible for one source type. It checks whether
    the source is reachable and the response matches the expected schema.
    No adapter may claim success unless a real response was received and
    checked against a known-good fixture or schema.
    """

    @abstractmethod
    async def validate(self, source_id: uuid.UUID, config: dict | None) -> ValidationResult: ...

    @property
    @abstractmethod
    def validation_code(self) -> str:
        """The VAL-* code this adapter satisfies (e.g. 'VAL-NOVA-001')."""
        ...
