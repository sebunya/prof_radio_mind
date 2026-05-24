from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class Station:
    id: uuid.UUID
    name: str
    call_sign: str
    frequency: str | None = None
    city: str | None = None
    country_code: str = "AU"
    is_active: bool = True

    @classmethod
    def create(
        cls,
        name: str,
        call_sign: str,
        *,
        frequency: str | None = None,
        city: str | None = None,
        country_code: str = "AU",
    ) -> Station:
        return cls(
            id=uuid.uuid4(),
            name=name,
            call_sign=call_sign,
            frequency=frequency,
            city=city,
            country_code=country_code,
        )
