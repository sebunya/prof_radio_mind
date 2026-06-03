"""phase_e_play_events_dedup_index

Revision ID: c4e2a1f9b8d7
Revises: b3c9d1f04a2e
Create Date: 2026-06-03 00:00:00.000000

Phase E — non-destructive duplicate guard for play_events.

Adds a DB-level backstop against exact double-inserts of the same play event
(same station_id + fingerprint + played_at instant) without rejecting
legitimate replays, which always have a different played_at.

Design notes:
  - This is a BACKSTOP. The primary dedup is application-level: the scheduler's
    _persist_result skips a play event whose fingerprint already exists within
    a 30-minute window (2x the Capital FM poll interval). That handles the
    "same song still playing across consecutive polls" case where played_at
    differs by the poll interval.
  - This index only catches identical (station, fingerprint, played_at) rows,
    e.g. from a retry or double-commit. A legitimate replay hours/days later
    has a different played_at and is unaffected.
  - NON-DESTRUCTIVE: existing duplicates are NOT deleted. They are flagged with
    is_duplicate = true (keeping the earliest row per group), preserving the
    full audit trail. The partial unique index applies only WHERE
    is_duplicate = false, so flagged historical rows never block index creation.
  - Columns are plain (no expression), so the index is immutable and valid on
    the timestamptz played_at column.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e2a1f9b8d7"
down_revision: str | None = "b3c9d1f04a2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_play_events_station_fp_playedat"


def upgrade() -> None:
    # 1. Flag existing exact duplicates (keep earliest per group, mark the rest).
    #    Non-destructive: no rows are deleted.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY station_id, fingerprint, played_at
                       ORDER BY created_at, id
                   ) AS rn
            FROM play_events
            WHERE fingerprint IS NOT NULL
        )
        UPDATE play_events AS pe
        SET is_duplicate = true
        FROM ranked
        WHERE pe.id = ranked.id
          AND ranked.rn > 1
          AND pe.is_duplicate = false
        """
    )

    # 2. Partial unique index — enforces uniqueness only among non-duplicate,
    #    fingerprinted rows. Historical flagged duplicates are excluded so the
    #    index always builds cleanly.
    op.execute(
        f"""
        CREATE UNIQUE INDEX {_INDEX_NAME}
        ON play_events (station_id, fingerprint, played_at)
        WHERE is_duplicate = false AND fingerprint IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drop only the structural change. The is_duplicate flags are left in place
    # because the original boolean state cannot be reconstructed reliably.
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
