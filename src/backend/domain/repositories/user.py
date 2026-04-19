"""User repository protocol."""
from typing import Protocol, Optional

from domain.entities.user import User


class UserRepositoryProtocol(Protocol):
    """Protocol for user repository."""

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]: ...

    async def create(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
    ) -> User: ...

    async def exists(self, telegram_id: int) -> bool: ...