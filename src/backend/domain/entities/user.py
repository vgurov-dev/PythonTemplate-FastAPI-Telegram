"""User entity for backend."""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User entity."""

    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
    )
    telegram_id: int = Field(unique=True, nullable=False)
    username: Optional[str] = Field(max_length=255, nullable=True)
    first_name: str = Field(max_length=255, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
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