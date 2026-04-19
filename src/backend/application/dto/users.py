"""Users DTO."""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CreateUserRequest(BaseModel):
    """Schema for creating user from Telegram."""

    telegram_id: int
    username: Optional[str] = None
    first_name: str


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    is_active: bool