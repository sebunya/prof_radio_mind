"""Source validation command.

Runs a SourceValidationAdapter and persists the result to source_validations.
Keeps the use-case logic separate from the adapter implementations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.application.validation.base import SourceValidationAdapter, ValidationResult
from app.domain.ports.source_repository import SourceRepository


@dataclass
class RunSourceValidationCommand:
    source_id: uuid.UUID
    adapter: SourceValidationAdapter
    source_repository: SourceRepository

    async def execute(self) -> ValidationResult:
        source = await self.source_repository.get_by_id(self.source_id)
        if source is None:
            raise ValueError(f"Source {self.source_id} not found")

        result = await self.adapter.validate(self.source_id, source.config)
        return result
