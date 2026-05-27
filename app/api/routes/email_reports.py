"""Email report management API.

Endpoints:
  GET    /email-reports/recipients              — list all recipients
  POST   /email-reports/recipients              — add recipient
  PATCH  /email-reports/recipients/{id}         — update recipient (name / email / frequencies)
  DELETE /email-reports/recipients/{id}         — deactivate recipient
  GET    /email-reports/logs                    — recent send log (last 50)
  POST   /email-reports/send-now               — trigger a manual send for a given frequency
  GET    /email-reports/preview/{frequency}     — preview HTML for the given frequency
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/email-reports", tags=["email-reports"])

Frequency = Literal["daily", "weekly", "monthly", "custom"]
_VALID_FREQ = {"daily", "weekly", "monthly", "custom"}


# ── Request / Response models ─────────────────────────────────────────────────

class RecipientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    frequencies: list[Frequency] = Field(..., min_length=1)


class RecipientUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    frequencies: list[Frequency] | None = None
    is_active: bool | None = None


class RecipientResponse(BaseModel):
    id: str
    name: str
    email: str
    frequencies: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SendLogResponse(BaseModel):
    id: str
    frequency: str
    recipients: str
    subject: str
    status: str
    error_message: str | None
    total_plays: int | None
    sent_at: datetime


class SendNowRequest(BaseModel):
    frequency: Frequency
    start_date: date | None = Field(
        None,
        description="Inclusive start date (YYYY-MM-DD). Required when frequency='custom'.",
    )
    end_date: date | None = Field(
        None,
        description=(
            "Inclusive end date (YYYY-MM-DD). Required when frequency='custom'. "
            "The window covers up to and including 23:59:59 UTC on this date."
        ),
    )


class SendNowResponse(BaseModel):
    status: str
    frequency: str
    recipients_count: int
    sent_count: int
    total_plays: int
    unique_songs: int
    dry_run: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_response(row: object) -> RecipientResponse:
    from app.infrastructure.database.models.notifications import EmailRecipientDB

    assert isinstance(row, EmailRecipientDB)
    return RecipientResponse(
        id=str(row.id),
        name=row.name,
        email=row.email,
        frequencies=list(row.frequencies or []),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _log_to_response(row: object) -> SendLogResponse:
    from app.infrastructure.database.models.notifications import EmailSendLogDB

    assert isinstance(row, EmailSendLogDB)
    snapshot = row.stats_snapshot or {}
    return SendLogResponse(
        id=str(row.id),
        frequency=row.frequency,
        recipients=row.recipients,
        subject=row.subject,
        status=row.status,
        error_message=row.error_message,
        total_plays=snapshot.get("total_plays"),
        sent_at=row.sent_at,
    )


# ── GET /email-reports/recipients ─────────────────────────────────────────────

@router.get(
    "/recipients",
    response_model=list[RecipientResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_recipients(session: AsyncSession = Depends(get_db)) -> list[RecipientResponse]:
    """Return all recipients (active and inactive)."""
    from sqlalchemy import select

    from app.infrastructure.database.models.notifications import EmailRecipientDB

    result = await session.execute(
        select(EmailRecipientDB).order_by(EmailRecipientDB.created_at)
    )
    rows = result.scalars().all()
    return [_row_to_response(r) for r in rows]


# ── POST /email-reports/recipients ────────────────────────────────────────────

@router.post(
    "/recipients",
    response_model=RecipientResponse,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
async def add_recipient(
    body: RecipientRequest,
    session: AsyncSession = Depends(get_db),
) -> RecipientResponse:
    """Add a new email recipient."""
    from app.infrastructure.database.models.notifications import EmailRecipientDB
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    existing = await repo.get_by_email(str(body.email))
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Recipient with email {body.email} already exists",
        )
    row = EmailRecipientDB(
        id=uuid.uuid4(),
        name=body.name,
        email=str(body.email),
        frequencies=list(body.frequencies),
        is_active=True,
    )
    await repo.save(row)
    await session.commit()
    return _row_to_response(row)


# ── PATCH /email-reports/recipients/{id} ──────────────────────────────────────

@router.patch(
    "/recipients/{recipient_id}",
    response_model=RecipientResponse,
    dependencies=[Depends(require_api_key)],
)
async def update_recipient(
    recipient_id: uuid.UUID,
    body: RecipientUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> RecipientResponse:
    """Partially update a recipient's name, email, frequencies, or active status."""
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    row = await repo.get(recipient_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")

    if body.name is not None:
        row.name = body.name
    if body.email is not None:
        # Check for conflicts
        conflict = await repo.get_by_email(str(body.email))
        if conflict and conflict.id != recipient_id:
            raise HTTPException(status_code=409, detail="Email already used by another recipient")
        row.email = str(body.email)
    if body.frequencies is not None:
        row.frequencies = list(body.frequencies)
    if body.is_active is not None:
        row.is_active = body.is_active

    await session.flush()
    await session.commit()
    return _row_to_response(row)


# ── DELETE /email-reports/recipients/{id} ────────────────────────────────────

@router.delete(
    "/recipients/{recipient_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
async def remove_recipient(
    recipient_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a recipient (soft delete)."""
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    removed = await repo.delete(recipient_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    await session.commit()


# ── GET /email-reports/logs ────────────────────────────────────────────────────

@router.get(
    "/logs",
    response_model=list[SendLogResponse],
    dependencies=[Depends(require_api_key)],
)
async def send_log(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
) -> list[SendLogResponse]:
    """Return recent email send log entries."""
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailSendLogRepository,
    )

    repo = SQLEmailSendLogRepository(session)
    rows = await repo.list_recent(limit=min(limit, 200))
    return [_log_to_response(r) for r in rows]


# ── POST /email-reports/send-now ──────────────────────────────────────────────

@router.post(
    "/send-now",
    response_model=SendNowResponse,
    dependencies=[Depends(require_api_key)],
)
async def send_now(body: SendNowRequest) -> SendNowResponse:
    """Trigger an immediate report send for the given frequency.

    For ``frequency="custom"`` supply ``start_date`` and ``end_date``
    (both inclusive, YYYY-MM-DD).  The custom window covers 00:00 UTC on
    *start_date* through 23:59:59 UTC on *end_date* and is sent to every
    active recipient regardless of their individual frequency subscriptions.

    For scheduled frequencies (daily / weekly / monthly) the window is
    computed automatically using the system's rolling-window definitions.

    This runs synchronously in the request context; for scheduled production
    sends the APScheduler jobs are preferred.
    """
    from app.application.reports.email_report_builder import send_frequency_report

    custom_start: datetime | None = None
    custom_end:   datetime | None = None

    if body.frequency == "custom":
        if body.start_date is None or body.end_date is None:
            raise HTTPException(
                status_code=422,
                detail="frequency='custom' requires both start_date and end_date",
            )
        if body.start_date > body.end_date:
            raise HTTPException(
                status_code=422,
                detail="start_date must not be after end_date",
            )
        custom_start = datetime(
            body.start_date.year, body.start_date.month, body.start_date.day,
            tzinfo=UTC,
        )
        # end is inclusive: cover the full day by pointing to the next day's midnight
        custom_end = datetime(
            body.end_date.year, body.end_date.month, body.end_date.day,
            tzinfo=UTC,
        ) + timedelta(days=1)

    try:
        result = await send_frequency_report(body.frequency, custom_start, custom_end)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Report generation failed: {exc}") from exc

    return SendNowResponse(
        status=result.get("status", "unknown"),
        frequency=body.frequency,
        recipients_count=result.get("recipients_count", 0),
        sent_count=result.get("sent_count", 0),
        total_plays=result.get("total_plays", 0),
        unique_songs=result.get("unique_songs", 0),
        dry_run=result.get("dry_run", True),
    )


# ── GET /email-reports/preview/{frequency} ────────────────────────────────────

@router.get(
    "/preview/{frequency}",
    dependencies=[Depends(require_api_key)],
)
async def preview_email(
    frequency: Frequency,
    response: Response,
    start_date: date | None = Query(
        None,
        description="Inclusive start date (YYYY-MM-DD). Required for frequency='custom'.",
    ),
    end_date: date | None = Query(
        None,
        description="Inclusive end date (YYYY-MM-DD). Required for frequency='custom'.",
    ),
) -> Response:
    """Return a preview of the HTML email for the given frequency.

    For ``frequency="custom"`` add ``?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD``
    query parameters.  Opens directly in the browser — useful for template
    verification before sending.
    """
    from app.application.reports.email_report_builder import build_report_data, render_html_email

    custom_start: datetime | None = None
    custom_end:   datetime | None = None

    if frequency == "custom":
        if start_date is None or end_date is None:
            raise HTTPException(
                status_code=422,
                detail="frequency='custom' requires start_date and end_date query params",
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=422,
                detail="start_date must not be after end_date",
            )
        custom_start = datetime(
            start_date.year, start_date.month, start_date.day, tzinfo=UTC,
        )
        custom_end = datetime(
            end_date.year, end_date.month, end_date.day, tzinfo=UTC,
        ) + timedelta(days=1)

    try:
        data = await build_report_data(frequency, custom_start, custom_end)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Report build failed: {exc}") from exc

    html_content = render_html_email(data, recipient_name="Preview Recipient")
    return Response(content=html_content, media_type="text/html")
