"""Sources API — list sources and trigger validation runs."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/sources", tags=["sources"])


class ValidationResultResponse(BaseModel):
    source_id: str
    validation_code: str
    status: str
    notes: str
    response_status_code: int | None
    validated_at: datetime
    validated_by: str


class SourceValidationSummary(BaseModel):
    source_id: str
    latest_status: str | None
    latest_validated_at: datetime | None
    total_runs: int


@router.post(
    "/{source_id}/validate",
    response_model=ValidationResultResponse,
    dependencies=[Depends(require_api_key)],
)
async def validate_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ValidationResultResponse:
    """Run the appropriate validation adapter for a source and persist the result."""
    from app.application.validation.adapters.capital import CapitalIHeartValidationAdapter
    from app.infrastructure.database.repositories.source_repo import SQLSourceRepository
    from app.infrastructure.database.repositories.source_validation_repo import (
        SQLSourceValidationRepository,
    )

    source_repo = SQLSourceRepository(session)
    source = await source_repo.get_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    st = source.source_type
    source_type = st.value if hasattr(st, "value") else str(st)

    if source_type == "iheart":
        adapter = CapitalIHeartValidationAdapter()
    else:
        raise HTTPException(
            status_code=422,
            detail=f"No validation adapter registered for source type '{source_type}'",
        )

    try:
        result = await adapter.validate(source_id, source.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Collector error: {exc}") from exc

    val_repo = SQLSourceValidationRepository(session)
    await val_repo.save(result)

    return ValidationResultResponse(
        source_id=str(result.source_id),
        validation_code=result.validation_code,
        status=result.status.value,
        notes=result.notes,
        response_status_code=result.response_status_code,
        validated_at=result.validated_at,
        validated_by=result.validated_by,
    )


@router.get(
    "/{source_id}/validations",
    response_model=SourceValidationSummary,
    dependencies=[Depends(require_api_key)],
)
async def get_source_validation_history(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SourceValidationSummary:
    """Return the latest validation result and total run count for a source."""
    from app.infrastructure.database.repositories.source_validation_repo import (
        SQLSourceValidationRepository,
    )

    val_repo = SQLSourceValidationRepository(session)
    latest = await val_repo.latest_for_source(source_id)
    all_runs = await val_repo.list_for_source(source_id)

    return SourceValidationSummary(
        source_id=str(source_id),
        latest_status=latest.status if latest else None,
        latest_validated_at=latest.validated_at if latest else None,
        total_runs=len(all_runs),
    )
