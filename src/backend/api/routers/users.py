"""Users API router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.service_auth import verify_service_token
from infrastructure.database.repositories.user import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateSchema(BaseModel):
    """Schema for creating user from Telegram."""

    telegram_id: int
    username: Optional[str] = None
    first_name: str


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    telegram_id: int
    username: Optional[str]
    first_name: str
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/{telegram_id}/telegram", response_model=UserResponse)
async def create_user_from_telegram(
    telegram_id: int,
    data: UserCreateSchema,
    _service_token: str = Depends(verify_service_token),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Create or update user from Telegram bot."""
    repo = UserRepository(session)

    existing = await repo.get_by_telegram_id(telegram_id)
    if existing:
        return existing

    user = await repo.create(
        telegram_id=data.telegram_id,
        username=data.username,
        first_name=data.first_name,
    )

    return user


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    _service_token: str = Depends(verify_service_token),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get user by Telegram ID."""
    repo = UserRepository(session)

    user = await repo.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user