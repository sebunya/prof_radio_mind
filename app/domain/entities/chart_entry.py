"""Chart entry domain entity — ARIA Singles chart weekly data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass
class ChartEntry:
    id: uuid.UUID
    chart_name: str       # e.g. "ARIA Singles"
    chart_date: date      # Week ending date
    position: int
    artist: str
    title: str
    previous_position: int | None
    peak_position: int | None
    weeks_on_chart: int | None

    @classmethod
    def create(
        cls,
        chart_name: str,
        chart_date: date,
        position: int,
        artist: str,
        title: str,
        *,
        previous_position: int | None = None,
        peak_position: int | None = None,
        weeks_on_chart: int | None = None,
    ) -> ChartEntry:
        return cls(
            id=uuid.uuid4(),
            chart_name=chart_name,
            chart_date=chart_date,
            position=position,
            artist=artist,
            title=title,
            previous_position=previous_position,
            peak_position=peak_position,
            weeks_on_chart=weeks_on_chart,
        )
