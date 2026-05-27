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
async def list_recipients(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[RecipientResponse]:
    """Return recipients.  Total count in ``X-Total-Count`` response header."""
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    rows, total = await repo.list_page(limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(total)
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
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[SendLogResponse]:
    """Return email send log entries.  Total count in ``X-Total-Count`` header."""
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailSendLogRepository,
    )

    repo = SQLEmailSendLogRepository(session)
    rows, total = await repo.list_page(limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(total)
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


# ── GET /email-reports/unsubscribe ───────────────────────────────────────────
# Public endpoint — NO API key required.  Email clients follow this URL when the
# subscriber clicks "Unsubscribe" or triggers one-click via the List-Unsubscribe
# header (RFC 8058).

@router.get(
    "/unsubscribe",
    include_in_schema=True,
    tags=["email-reports"],
)
async def unsubscribe_get(
    id: uuid.UUID = Query(..., description="Recipient UUID from unsubscribe link"),
    token: str = Query(..., description="HMAC-SHA256 token binding id+email"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Unsubscribe a recipient via a signed link (used by browser clicks).

    Verifies the HMAC token, deactivates the recipient, and returns a plain
    HTML confirmation page.  Token is bound to both ``id`` and ``email`` so it
    cannot be replayed across accounts even if an ID is guessed.
    """
    from app.application.reports.email_report_builder import verify_unsubscribe_token
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    row = await repo.get(id)

    # Use a generic message for both "not found" and "bad token" to avoid leaking
    # whether a given UUID exists.
    if row is None or not verify_unsubscribe_token(token, row.id, row.email):
        html_body = _unsub_page(
            "Invalid or expired unsubscribe link",
            "This link is invalid or has already been used. "
            "Contact your RMIAS administrator if you need assistance.",
            success=False,
        )
        return Response(content=html_body, media_type="text/html", status_code=400)

    if row.is_active:
        row.is_active = False
        await session.flush()
        await session.commit()

    html_body = _unsub_page(
        "Unsubscribed",
        f"You have been unsubscribed from RMIAS radio reports. "
        f"Your address ({row.email}) will not receive any further automated emails.",
        success=True,
    )
    return Response(content=html_body, media_type="text/html")


@router.post(
    "/unsubscribe",
    include_in_schema=True,
    tags=["email-reports"],
    status_code=200,
)
async def unsubscribe_post(
    id: uuid.UUID = Query(...),
    token: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """One-click unsubscribe handler (RFC 8058 ``List-Unsubscribe-Post``).

    Email clients (Gmail, Apple Mail, Yahoo) POST to this URL with the body
    ``List-Unsubscribe=One-Click``.  The response is a plain 200 JSON — the
    client doesn't render it.  Same token verification as the GET endpoint.
    """
    from app.application.reports.email_report_builder import verify_unsubscribe_token
    from app.infrastructure.database.repositories.email_recipient_repo import (
        SQLEmailRecipientRepository,
    )

    repo = SQLEmailRecipientRepository(session)
    row = await repo.get(id)

    if row is None or not verify_unsubscribe_token(token, row.id, row.email):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")

    if row.is_active:
        row.is_active = False
        await session.flush()
        await session.commit()

    return {"status": "unsubscribed", "id": str(id)}


def _unsub_page(title: str, message: str, success: bool) -> str:
    """Return a minimal, self-contained HTML confirmation page."""
    import html as _html

    colour = "#10b981" if success else "#ef4444"
    icon   = "✓" if success else "✗"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_html.escape(title)} — RMIAS</title>
<style>
  body{{margin:0;padding:0;background:#0f172a;font-family:sans-serif;
        display:flex;align-items:center;justify-content:center;min-height:100vh}}
  .card{{background:#1e293b;border-radius:12px;padding:40px 48px;max-width:480px;
         text-align:center;border:1px solid #334155}}
  .icon{{font-size:48px;color:{colour};margin-bottom:16px}}
  h1{{margin:0 0 12px;font-size:22px;font-weight:700;color:#f1f5f9}}
  p{{margin:0;font-size:14px;color:#94a3b8;line-height:1.6}}
  .brand{{margin-top:32px;font-size:11px;color:#334155}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">{icon}</div>
  <h1>{_html.escape(title)}</h1>
  <p>{_html.escape(message)}</p>
  <p class="brand">RMIAS · Radio Music Intelligence &amp; Automation System</p>
</div>
</body>
</html>"""


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
