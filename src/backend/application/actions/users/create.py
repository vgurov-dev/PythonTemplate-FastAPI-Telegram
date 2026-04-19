"""Create user action."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.exceptions import UserNotFoundError
from infrastructure.database.repositories.user import UserRepository
from application.dto.users import CreateUserRequest, UserResponse


class CreateUserAction:
    """Create or get existing user from Telegram."""

    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)
        self._session = session

    async def execute(self, telegram_id: int, data: CreateUserRequest) -> UserResponse:
        """Execute create user action."""
        existing = await self._repo.get_by_telegram_id(telegram_id)
        if existing:
            return UserResponse.model_validate(existing)

        user = await self._repo.create(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name,
        )
        await self._session.commit()
        return UserResponse.model_validate(user)


class GetUserAction:
    """Get user by Telegram ID."""

    def __init__(self, session: AsyncSession):
        self._repo = UserRepository(session)

    async def execute(self, telegram_id: int) -> UserResponse:
        """Execute get user action."""
        user = await self._repo.get_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User with telegram_id={telegram_id} not found")
        return UserResponse.model_validate(user)