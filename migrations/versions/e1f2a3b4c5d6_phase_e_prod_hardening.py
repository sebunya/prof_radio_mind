"""phase_e_prod_hardening

Revision ID: e1f2a3b4c5d6
Revises: b3c9d1f04a2e
Create Date: 2026-05-27 00:00:00.000000

Phase E — production-hardening schema changes:
  1. webhook_subscriptions: new table for persisted webhook subscriptions
  2. collector_runs: add index on status column
  3. play_events: add unique index on (station_id, fingerprint) for dedup integrity
     Uses a partial unique index (WHERE fingerprint IS NOT NULL) since fingerprint is nullable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "b3c9d1f04a2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. webhook_subscriptions ─────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("event_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("secret", sa.String(512), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_subscriptions_is_active",
        "webhook_subscriptions",
        ["is_active"],
    )

    # ── 2. collector_runs.status index ───────────────────────────────────────
    op.create_index(
        "ix_collector_runs_status",
        "collector_runs",
        ["status"],
    )

    # ── 3. play_events partial unique index on (station_id, fingerprint) ─────
    # Partial (WHERE fingerprint IS NOT NULL) — fingerprint is nullable for legacy rows
    # where parsing failed. CONCURRENTLY is not supported inside a transaction block in
    # Alembic; use regular CREATE UNIQUE INDEX here (safe for initial data volumes).
    op.create_index(
        "uq_play_events_station_fingerprint",
        "play_events",
        ["station_id", "fingerprint"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_play_events_station_fingerprint", table_name="play_events")
    op.drop_index("ix_collector_runs_status", table_name="collector_runs")
    op.drop_index("ix_webhook_subscriptions_is_active", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")
