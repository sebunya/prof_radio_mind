"""Historical backfill API — bulk import of play events for past broadcast dates.

Accepts the same CSV format as the manual import endpoint but with an explicit
broadcast date. Used to import months of historical data before RMIAS was deployed.

Rules:
- Rows are validated the same as manual imports (no silent drops)
- Duplicate fingerprints within the same station/date window are skipped
- Attribution is forced to "manual_csv" for all backfill rows
- A review item is created when import completes with the row counts
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.auth import require_api_key

router = APIRouter(prefix="/backfill", tags=["backfill"])

_REQUIRED_COLUMNS = {"artist", "title", "played_at"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class BackfillResult(BaseModel):
    station_id: str
    broadcast_date: str
    rows_submitted: int
    rows_accepted: int
    rows_rejected: int
    rejection_reasons: list[str]
    review_item_id: str


@router.post(
    "/{station_id}",
    response_model=BackfillResult,
    dependencies=[Depends(require_api_key)],
)
async def backfill_station(
    station_id: uuid.UUID,
    file: UploadFile = File(...),
    broadcast_date: date = Query(..., description="Broadcast date being backfilled"),
) -> BackfillResult:
    """Bulk-import historical play events for a station from a CSV file.

    CSV must have columns: artist, title, played_at (ISO 8601 or HH:MM:SS).
    """
    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV has no headers")

    headers = {h.lower().strip() for h in reader.fieldnames}
    missing = _REQUIRED_COLUMNS - headers
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {sorted(missing)}",
        )

    rows_submitted = 0
    rows_accepted = 0
    rejection_reasons: list[str] = []
    play_events = []

    from app.application.normalization.normalizer import (
        compute_fingerprint,
        strip_label_from_artist,
    )
    from app.domain.entities.play_event import PlayEvent

    seen_fingerprints: set[str] = set()

    for row_num, row in enumerate(reader, start=2):
        rows_submitted += 1
        try:
            artist = row.get("artist", "").strip()
            title = row.get("title", "").strip()
            played_at_str = row.get("played_at", "").strip()

            if not artist or not title:
                rejection_reasons.append(f"Row {row_num}: empty artist or title")
                continue

            try:
                if "T" in played_at_str:
                    played_at = datetime.fromisoformat(played_at_str)
                    if played_at.tzinfo is None:
                        played_at = played_at.replace(tzinfo=UTC)
                else:
                    h, m, s = (played_at_str + ":00:00").split(":")[:3]
                    played_at = datetime(
                        broadcast_date.year,
                        broadcast_date.month,
                        broadcast_date.day,
                        int(h), int(m), int(s),
                        tzinfo=UTC,
                    )
            except (ValueError, TypeError):
                rejection_reasons.append(
                    f"Row {row_num}: invalid played_at '{played_at_str}'"
                )
                continue

            clean_artist = strip_label_from_artist(artist)
            fp = compute_fingerprint(clean_artist, title)

            if fp in seen_fingerprints:
                rejection_reasons.append(
                    f"Row {row_num}: duplicate fingerprint for {artist} - {title}"
                )
                continue

            seen_fingerprints.add(fp)
            play_events.append(
                PlayEvent.create(
                    station_id=station_id,
                    source_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"source.backfill.{station_id}"),
                    collector_run_id=uuid.uuid4(),
                    played_at=played_at,
                    raw_artist=artist,
                    raw_title=title,
                    fingerprint=fp,
                    attribution="manual_csv",
                )
            )
            rows_accepted += 1

        except Exception as exc:
            rejection_reasons.append(f"Row {row_num}: unexpected error — {exc}")

    if not play_events and rows_submitted > 0:
        raise HTTPException(
            status_code=422,
            detail=f"No valid rows. Reasons: {rejection_reasons[:10]}",
        )

    review_item_id = str(uuid.uuid4())
    try:
        from app.domain.entities.review_item import ReviewItem, ReviewItemType
        from app.infrastructure.database.repositories.play_event_repo import (
            SQLPlayEventRepository,
        )
        from app.infrastructure.database.repositories.review_item_repo import (
            SQLReviewItemRepository,
        )
        from app.infrastructure.database.session import _get_factory as _factory

        async with _factory()() as session:
            play_repo = SQLPlayEventRepository(session)
            for ev in play_events:
                await play_repo.save(ev)

            review_repo = SQLReviewItemRepository(session)
            item = ReviewItem.create(
                item_type=ReviewItemType.MANUAL_REVIEW,
                title=f"Backfill completed: station {station_id} / {broadcast_date}",
                description=(
                    f"Backfill import: {rows_accepted} accepted, "
                    f"{rows_submitted - rows_accepted} rejected."
                ),
                station_id=station_id,
            )
            await review_repo.add(item)
            review_item_id = str(item.id)
            await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return BackfillResult(
        station_id=str(station_id),
        broadcast_date=str(broadcast_date),
        rows_submitted=rows_submitted,
        rows_accepted=rows_accepted,
        rows_rejected=rows_submitted - rows_accepted,
        rejection_reasons=rejection_reasons[:50],
        review_item_id=review_item_id,
    )
