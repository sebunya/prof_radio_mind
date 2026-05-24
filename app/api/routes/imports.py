"""POST /manual-imports — accept a CSV file for a given station."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.application.imports.csv_importer import import_csv
from app.application.imports.manual_csv import ImportStatus

router = APIRouter(prefix="/manual-imports", tags=["imports"])


class ImportResponse(BaseModel):
    batch_id: str
    station_id: str
    filename: str
    status: str
    total_rows: int
    imported_rows: int
    error_rows: int
    errors: list[str]


@router.post("/{station_id}", response_model=ImportResponse, status_code=201)
async def create_manual_import(
    station_id: uuid.UUID,
    file: UploadFile,
) -> ImportResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Use placeholder source_id and collector_run_id — real IDs wired in Pass 16
    source_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"manual_csv_{station_id}")
    collector_run_id = uuid.uuid4()

    result = import_csv(
        raw_bytes,
        station_id=station_id,
        source_id=source_id,
        collector_run_id=collector_run_id,
        filename=file.filename or "upload.csv",
    )

    if result.batch.status == ImportStatus.FAILED and result.batch.imported_rows == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Import failed — no rows could be imported",
                "errors": result.batch.errors,
            },
        )

    return ImportResponse(
        batch_id=str(result.batch.id),
        station_id=str(station_id),
        filename=result.batch.filename,
        status=result.batch.status.value,
        total_rows=result.batch.total_rows,
        imported_rows=result.batch.imported_rows,
        error_rows=result.batch.error_rows,
        errors=result.batch.errors,
    )
