"""SQLAlchemy implementation of DailyReportRepository."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.reports import DailyReport, ReportVersion


class SQLDailyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_station_date(
        self, station_id: uuid.UUID, report_date: date
    ) -> DailyReport | None:
        from_dt = datetime(report_date.year, report_date.month, report_date.day)
        stmt = (
            select(DailyReport)
            .where(
                DailyReport.station_id == station_id,
                DailyReport.report_date == from_dt,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def save(self, report: DailyReport) -> None:
        existing = await self._session.get(DailyReport, report.id)
        if not existing:
            self._session.add(report)
        await self._session.flush()

    async def upsert(
        self,
        station_id: uuid.UUID,
        report_date: date,
        confidence_level: str,
        confidence_score: float,
        total_plays: int,
        unique_songs: int,
        source_coverage: dict,
        snapshot_rows: list[dict],
    ) -> tuple[DailyReport, int]:
        """Create or update a DailyReport; return the model and the new version number."""
        existing = await self.get_for_station_date(station_id, report_date)
        report_dt = datetime(report_date.year, report_date.month, report_date.day)

        if existing is None:
            report = DailyReport(
                id=uuid.uuid4(),
                station_id=station_id,
                report_date=report_dt,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                total_plays=total_plays,
                unique_songs=unique_songs,
                source_coverage=source_coverage,
            )
            self._session.add(report)
            await self._session.flush()
            version = 1
        else:
            prev_version = await self._get_latest_version(existing.id)
            version = prev_version + 1
            snapshot_model = ReportVersion(
                id=uuid.uuid4(),
                daily_report_id=existing.id,
                version_number=prev_version,
                snapshot={"rows": snapshot_rows},
                created_by="system",
                change_note=f"Superseded by version {version}",
            )
            self._session.add(snapshot_model)
            existing.confidence_level = confidence_level
            existing.confidence_score = confidence_score
            existing.total_plays = total_plays
            existing.unique_songs = unique_songs
            existing.source_coverage = source_coverage
            existing.is_corrected = True
            existing.correction_note = f"Regenerated as version {version}"
            report = existing
            await self._session.flush()

        return report, version

    async def _get_latest_version(self, report_id: uuid.UUID) -> int:
        stmt = (
            select(ReportVersion.version_number)
            .where(ReportVersion.daily_report_id == report_id)
            .order_by(ReportVersion.version_number.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        val = result.scalar()
        return val if val is not None else 1
