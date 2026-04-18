"""Domain entities package."""
from abc import ABC
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class BaseEntity(SQLModel, ABC):
    """Base entity with common fields."""

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
    )

    class Config:
        from_attributes = True