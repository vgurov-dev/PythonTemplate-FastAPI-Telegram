"""Users API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bootstrap.database import get_session
from api.dependencies import verify_service_token
from domain.exceptions import UserNotFoundError
from application.dto.users import CreateUserRequest, UserResponse
from application.actions.users.create import CreateUserAction, GetUserAction


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/{telegram_id}/telegram", response_model=UserResponse)
async def create_user_from_telegram(
    telegram_id: int,
    data: CreateUserRequest,
    _service_token: str = Depends(verify_service_token),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Create or update user from Telegram bot."""
    action = CreateUserAction(session)
    return await action.execute(telegram_id, data)


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    _service_token: str = Depends(verify_service_token),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get user by Telegram ID."""
    action = GetUserAction(session)
    try:
        return await action.execute(telegram_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )