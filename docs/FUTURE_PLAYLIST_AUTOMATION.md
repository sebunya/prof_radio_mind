# Future Design: Playlist Automation

**Status:** Design-only. Not scheduled for MVP implementation.  
**MVP Boundary:** No playlist automation code exists in passes 1–21.  
**Prerequisite passes:** 22+ (DB persistence layer, async sessions, auth hardening)

---

## Overview

Playlist Automation extends RMIAS from a passive monitoring system to an active programming assistant. It answers: "Given this station's airplay history and chart data, what should be added to, removed from, or rotated in the playlist?"

This is a recommendation engine, not an auto-scheduler — a human operator makes all final programming decisions.

---

## Problem Statement

Radio music directors currently spend 2–4 hours per day manually reviewing airplay logs, chart services (ARIA, Billboard), and label pitches to maintain active playlists. The goal is to surface actionable recommendations — "Doja Cat 'Paint The Town Red' is trending up on NOVA969, consider moving to A-rotation" — so the director can act in minutes rather than hours.

---

## Functional Requirements

### R1 — Rotation tier classification
Songs classified into rotation tiers based on weekly spin counts:

| Tier | Spins/week | Description |
|---|---|---|
| A | 35–50 | Power rotation — flagship tracks |
| B | 20–34 | Medium rotation |
| C | 10–19 | Light rotation |
| New Entry | 1–9 | Testing phase |
| Retired | 0 | Removed from rotation |

### R2 — Recommendation types
- **Add to rotation:** Song trending up on chart and not yet in playlist
- **Increase rotation:** A/B/C tier upgrade based on spin trend and chart position
- **Decrease rotation:** Downgrade when track showing fatigue (declining engagement proxy)
- **Retire:** Song consistently underperforming vs. format benchmark

### R3 — Chart integration
Ingest ARIA Singles chart weekly (public data via scraper) and Billboard Hot 100 for international context. Chart rank feeds the recommendation engine.

### R4 — Human approval gate
Every recommendation requires explicit operator approval before any playlist change is recorded. The system never auto-applies changes.

### R5 — Playlist version history
All playlist states are versioned (append-only). Rollback to any prior state must be possible.

---

## Non-Functional Requirements

- Recommendation latency: < 5 seconds per station
- Chart data staleness: < 24 hours
- Audit trail: all recommendations and approvals stored immutably
- No vendor lock-in: chart scrapers must be replaceable adapters

---

## Proposed Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Playlist Automation                         │
│                                                                    │
│  ┌──────────────┐   ┌────────────────┐   ┌───────────────────┐   │
│  │ Chart Ingester│   │  Airplay Store │   │  Recommendation   │   │
│  │ (ARIA/BB100) │──▶│  (play_events) │──▶│  Engine           │   │
│  └──────────────┘   └────────────────┘   └────────┬──────────┘   │
│                                                    │              │
│                           ┌────────────────────────▼──────────┐   │
│                           │   PlaylistRecommendation Table     │   │
│                           │   (pending | approved | rejected)  │   │
│                           └────────────────────────┬──────────┘   │
│                                                    │              │
│                           ┌────────────────────────▼──────────┐   │
│                           │   Operator Approval API            │   │
│                           │   POST /playlist-recs/{id}/approve │   │
│                           └───────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### New domain entities required

```python
class RotationTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    NEW_ENTRY = "new_entry"
    RETIRED = "retired"

class RecommendationType(StrEnum):
    ADD = "add"
    INCREASE_ROTATION = "increase_rotation"
    DECREASE_ROTATION = "decrease_rotation"
    RETIRE = "retire"

@dataclass
class PlaylistRecommendation:
    id: uuid.UUID
    station_id: uuid.UUID
    song_id: uuid.UUID
    recommendation_type: RecommendationType
    from_tier: RotationTier | None
    to_tier: RotationTier | None
    confidence: float         # 0.0–1.0
    rationale: str            # human-readable explanation
    chart_rank: int | None
    weekly_spins: int
    status: Literal["pending", "approved", "rejected"]
    approved_by: str | None
    created_at: datetime
```

### New API endpoints required

| Method | Path | Description |
|---|---|---|
| GET | `/playlist/{station_id}` | Current playlist with rotation tiers |
| GET | `/playlist-recs/{station_id}` | Pending recommendations |
| POST | `/playlist-recs/{id}/approve` | Approve a recommendation |
| POST | `/playlist-recs/{id}/reject` | Reject with notes |

### Recommendation engine algorithm (sketch)

```
For each song active in last 14 days on station:
    weekly_spins = count(play_events, last_7_days)
    spin_trend = weekly_spins / prior_7_day_spins  (1.0 = flat)
    chart_rank = latest_aria_chart_rank or None
    current_tier = playlist.rotation_tier(song)

    if song not in playlist and chart_rank <= 20 and weekly_spins >= 5:
        yield ADD recommendation

    elif spin_trend > 1.25 and current_tier in (B, C):
        yield INCREASE_ROTATION recommendation

    elif spin_trend < 0.75 and current_tier in (A, B):
        yield DECREASE_ROTATION recommendation

    elif weekly_spins == 0 and song in playlist for > 30 days:
        yield RETIRE recommendation
```

---

## Schema additions (Phase D)

```sql
CREATE TABLE chart_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_name VARCHAR(64) NOT NULL,   -- 'aria_singles', 'billboard_hot100'
    week_ending DATE NOT NULL,
    song_id UUID REFERENCES songs(id),
    rank INTEGER NOT NULL,
    peak_rank INTEGER,
    weeks_on_chart INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE playlist_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID REFERENCES stations(id),
    song_id UUID REFERENCES songs(id),
    rotation_tier VARCHAR(16) NOT NULL,
    added_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ,
    added_by VARCHAR(255)
);

CREATE TABLE playlist_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID REFERENCES stations(id),
    song_id UUID REFERENCES songs(id),
    recommendation_type VARCHAR(32) NOT NULL,
    from_tier VARCHAR(16),
    to_tier VARCHAR(16),
    confidence NUMERIC(4,3) NOT NULL,
    rationale TEXT NOT NULL,
    chart_rank INTEGER,
    weekly_spins INTEGER NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    approved_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Implementation roadmap (post-MVP)

| Pass | Deliverable |
|---|---|
| 22 | Async DB session wiring — persist play_events, review_items |
| 23 | ARIA chart scraper + `chart_rankings` table |
| 24 | `playlist_entries` table + seed current playlists |
| 25 | Recommendation engine core + `playlist_recommendations` API |
| 26 | Operator approval UI (minimal web form or CLI) |
| 27 | Playlist version diff reporting |

---

## Open questions

1. **Engagement proxy:** RMIAS tracks spins but not listener engagement (requests, skip rate). Do we have access to a station's digital analytics? If so, weight recommendations accordingly.
2. **Format constraints:** Different stations have different format rules (e.g., no two songs from same artist in same hour). Does the recommendation engine need to be format-aware?
3. **Label relationships:** Should label priority affect recommendations? If so, how do we model ethical guardrails to prevent pay-to-play scenarios?
4. **Chart services:** ARIA web scraping is fragile. Is there a licensed API (ARIA CONNECT) available?
