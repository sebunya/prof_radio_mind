"""Playlist automation API — rotation tier recommendations and approvals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/playlist", tags=["playlist"])

# In-memory recommendation store.
# NOTE: data is lost on worker restart. Recommendations are short-lived (approve within
# the same session) so this is acceptable for MVP. A DB-backed repo would be needed for
# multi-worker HA deployments.
_recommendation_store: dict[str, object] = {}
# Timestamp of when each recommendation was added (for TTL eviction)
_recommendation_ts: dict[str, float] = {}
# Evict recommendations older than 4 hours to prevent unbounded memory growth
_REC_TTL_SECONDS = 4 * 3600


def _evict_expired_recommendations() -> None:
    """Remove recommendations older than _REC_TTL_SECONDS from the in-memory store."""
    import time
    cutoff = time.monotonic() - _REC_TTL_SECONDS
    expired = [k for k, ts in _recommendation_ts.items() if ts < cutoff]
    for k in expired:
        _recommendation_store.pop(k, None)
        _recommendation_ts.pop(k, None)


class RecommendationResponse(BaseModel):
    id: str
    station_id: str
    artist: str
    title: str
    current_tier: str | None
    recommended_tier: str
    recommendation_type: str
    weekly_spins: int
    reason: str
    approved: bool
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class ApproveRequest(BaseModel):
    approved_by: str


def _to_response(rec: object) -> RecommendationResponse:
    from app.domain.entities.playlist_recommendation import PlaylistRecommendation

    assert isinstance(rec, PlaylistRecommendation)
    return RecommendationResponse(
        id=str(rec.id),
        station_id=str(rec.station_id),
        artist=rec.artist,
        title=rec.title,
        current_tier=rec.current_tier.value if rec.current_tier else None,
        recommended_tier=rec.recommended_tier.value,
        recommendation_type=rec.recommendation_type.value,
        weekly_spins=rec.weekly_spins,
        reason=rec.reason,
        approved=rec.approved,
        approved_by=rec.approved_by,
        approved_at=rec.approved_at,
        created_at=rec.created_at,
    )


@router.post(
    "/{station_id}/analyse",
    response_model=list[RecommendationResponse],
    dependencies=[Depends(require_api_key)],
)
async def analyse_rotation(
    station_id: uuid.UUID,
    lookback_days: int = 7,
    session: AsyncSession = Depends(get_db),
) -> list[RecommendationResponse]:
    """Compute rotation tier recommendations for a station from recent plays.

    Reads the last `lookback_days` of play events, classifies each song into
    a rotation tier, and returns change recommendations.
    """
    from app.application.playlist.rotation_engine import (
        build_recommendations,
        spin_counts_from_plays,
    )
    from app.infrastructure.database.repositories.play_event_repo import SQLPlayEventRepository

    now = datetime.now(UTC)
    from_dt = now - timedelta(days=lookback_days)

    play_repo = SQLPlayEventRepository(session)
    try:
        events = await play_repo.list_for_station(station_id, from_dt, now)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not events:
        return []

    plays = [(e.raw_artist, e.raw_title) for e in events]
    spin_counts = spin_counts_from_plays(plays)
    recommendations = build_recommendations(station_id, spin_counts)

    # Cache in memory for approval; evict stale entries first
    import time
    _evict_expired_recommendations()
    now_mono = time.monotonic()
    for rec in recommendations:
        key = str(rec.id)
        _recommendation_store[key] = rec
        _recommendation_ts[key] = now_mono

    return [_to_response(r) for r in recommendations]


@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=RecommendationResponse,
    dependencies=[Depends(require_api_key)],
)
async def approve_recommendation(
    recommendation_id: uuid.UUID,
    body: ApproveRequest,
) -> RecommendationResponse:
    """Approve a playlist recommendation (human gate)."""
    rec = _recommendation_store.get(str(recommendation_id))
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation {recommendation_id} not found",
        )

    from app.domain.entities.playlist_recommendation import PlaylistRecommendation

    assert isinstance(rec, PlaylistRecommendation)
    if rec.approved:
        raise HTTPException(status_code=409, detail="Recommendation already approved")

    rec.approve(approved_by=body.approved_by)
    return _to_response(rec)


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_recommendation(recommendation_id: uuid.UUID) -> RecommendationResponse:
    """Retrieve a specific recommendation by ID."""
    rec = _recommendation_store.get(str(recommendation_id))
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation {recommendation_id} not found",
        )
    return _to_response(rec)
