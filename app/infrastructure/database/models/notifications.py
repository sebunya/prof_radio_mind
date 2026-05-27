"""ORM models for email notification recipients and send audit log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class EmailRecipientDB(Base):
    """A person who receives scheduled email reports."""

    __tablename__ = "email_recipients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    # JSON array of frequencies: ["daily", "weekly", "monthly"]
    frequencies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EmailSendLogDB(Base):
    """Audit log of every email send attempt."""

    __tablename__ = "email_send_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # "daily" | "weekly" | "monthly" | "manual"
    frequency: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Comma-separated recipient addresses for this send
    recipients: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    # "sent" | "failed" | "dry_run"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="sent", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Snapshot of key stats included in the email (for log inspection)
    stats_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
