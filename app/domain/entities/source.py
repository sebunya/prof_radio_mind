from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class SourceType(StrEnum):
    RADIOWAVE = "radiowave"
    ONLINE_RADIO_BOX = "online_radio_box"
    MANUAL_CSV = "manual_csv"
    UNKNOWN = "unknown"
    IHEART_WEB = "iheart_web"
    UKRADIOLIVE = "ukradiolive"
    RADOXO = "radoxo"
    RADIO_AUSTRALIA_ORG = "radio_australia_org"


@dataclass
class Source:
    id: uuid.UUID
    station_id: uuid.UUID
    source_type: SourceType
    name: str
    base_url: str | None = None
    config: dict | None = None
    is_active: bool = True

    @classmethod
    def create(
        cls,
        station_id: uuid.UUID,
        source_type: SourceType,
        name: str,
        *,
        base_url: str | None = None,
        config: dict | None = None,
    ) -> Source:
        return cls(
            id=uuid.uuid4(),
            station_id=station_id,
            source_type=source_type,
            name=name,
            base_url=base_url,
            config=config,
        )
