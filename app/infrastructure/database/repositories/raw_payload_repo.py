"""SQLAlchemy implementation of RawPayloadRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.raw_payload_repository import RawPayloadRepository
from app.domain.value_objects.raw_payload import RawPayload
from app.infrastructure.database.models.collector_runs import RawPayload as RawPayloadModel


class SQLRawPayloadRepository(RawPayloadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, payload: RawPayload) -> None:
        self._session.add(
            RawPayloadModel(
                id=payload.id,
                collector_run_id=payload.collector_run_id,
                source_id=payload.source_id,
                sha256=payload.sha256,
                storage_path=payload.storage_path,
                content_type=payload.content_type,
                byte_size=payload.byte_size,
                http_status=payload.http_status,
                fetched_at=payload.fetched_at,
            )
        )
        await self._session.flush()

    async def exists_by_sha256(self, sha256: str) -> bool:
        stmt = select(RawPayloadModel.id).where(RawPayloadModel.sha256 == sha256).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar() is not None
