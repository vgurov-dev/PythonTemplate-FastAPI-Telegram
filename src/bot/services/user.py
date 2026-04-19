"""User service for bot."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TelegramUser:
    """Telegram user model."""

    id: int
    username: Optional[str]
    first_name: str
    created_at: datetime = datetime.now(timezone.utc)


class UserService:
    """User service for bot."""

    async def create_user(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
    ) -> TelegramUser:
        """Create new user."""
        return TelegramUser(
            id=telegram_id,
            username=username,
            first_name=first_name,
        )

    async def get_user(self, telegram_id: int) -> Optional[TelegramUser]:
        """Get user by telegram ID."""
        return None

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[TelegramUser]:
        """Update user."""
        return None