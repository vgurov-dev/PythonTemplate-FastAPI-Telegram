"""Signup model for bot database."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import BIGINT, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class SignupStatus(str, Enum):
    NOT_CONFIRMED = "NOT_CONFIRMED"
    CONFIRMED = "CONFIRMED"


class Signup(Base):
    """User signup model."""

    __tablename__ = "signups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    telegram_id: Mapped[int] = mapped_column(
        BIGINT,
        unique=True,
        nullable=False,
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=SignupStatus.NOT_CONFIRMED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        default=None,
        nullable=True,
    )