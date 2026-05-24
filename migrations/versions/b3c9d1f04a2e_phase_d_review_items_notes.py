"""phase_d_review_items_notes

Revision ID: b3c9d1f04a2e
Revises: 45770ddee81b
Create Date: 2026-05-24 00:00:00.000000

Phase D changes:
  - review_items: add notes column
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3c9d1f04a2e"
down_revision: str | None = "45770ddee81b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("review_items", sa.Column("notes", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("review_items", "notes")
