"""User entity."""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=False):
    """User entity."""

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
    )
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=100, unique=True)
    password_hash: str = Field()
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        from_attributes = True