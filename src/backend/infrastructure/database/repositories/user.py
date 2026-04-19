"""User repository."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.repositories.user import UserRepositoryProtocol


class UserRepository(UserRepositoryProtocol):
    """User repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        statement = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
    ) -> User:
        """Create new user (no commit — call session.commit() in action)."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def exists(self, telegram_id: int) -> bool:
        """Check if user exists."""
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None