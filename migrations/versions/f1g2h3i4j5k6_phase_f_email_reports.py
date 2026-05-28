"""phase_f_email_reports

Revision ID: f1g2h3i4j5k6
Revises: e1f2a3b4c5d6
Create Date: 2026-05-27 00:00:00.000000

Phase F — email reporting tables:
  - email_recipients: persisted recipient list with frequency subscriptions
  - email_send_log: audit log of every send attempt
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1g2h3i4j5k6"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── email_recipients ─────────────────────────────────────────────────────
    op.create_table(
        "email_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(512), nullable=False),
        sa.Column(
            "frequencies",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_email_recipients_email"),
    )
    op.create_index("ix_email_recipients_email", "email_recipients", ["email"])
    op.create_index("ix_email_recipients_is_active", "email_recipients", ["is_active"])

    # ── email_send_log ────────────────────────────────────────────────────────
    op.create_table(
        "email_send_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frequency", sa.String(32), nullable=False),
        sa.Column("recipients", sa.Text, nullable=False),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'sent'"),
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("stats_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_send_log_frequency", "email_send_log", ["frequency"])
    op.create_index("ix_email_send_log_status", "email_send_log", ["status"])
    op.create_index("ix_email_send_log_sent_at", "email_send_log", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_email_send_log_sent_at", table_name="email_send_log")
    op.drop_index("ix_email_send_log_status", table_name="email_send_log")
    op.drop_index("ix_email_send_log_frequency", table_name="email_send_log")
    op.drop_table("email_send_log")
    op.drop_index("ix_email_recipients_is_active", table_name="email_recipients")
    op.drop_index("ix_email_recipients_email", table_name="email_recipients")
    op.drop_table("email_recipients")
