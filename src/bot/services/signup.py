"""Signup service for bot."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.signup import Signup, SignupStatus
import structlog

logger = structlog.get_logger()


class SignupService:
    """Service for managing user signups."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_signup(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
    ) -> Signup:
        """Create new signup record."""
        signup = Signup(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            status=SignupStatus.NOT_CONFIRMED.value,
        )
        self.session.add(signup)
        await self.session.commit()
        await self.session.refresh(signup)

        logger.info(
            "signup_created",
            telegram_id=telegram_id,
            status=SignupStatus.NOT_CONFIRMED.value,
        )

        return signup

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Signup]:
        """Get signup by telegram ID."""
        statement = select(Signup).where(Signup.telegram_id == telegram_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        telegram_id: int,
        status: SignupStatus,
    ) -> bool:
        """Update signup status."""
        statement = (
            update(Signup)
            .where(Signup.telegram_id == telegram_id)
            .values(
                status=status.value,
                updated_at=datetime.utcnow(),
            )
            .returning(Signup.id)
        )
        result = await self.session.execute(statement)
        await self.session.commit()

        updated_id = result.scalar_one_or_none()
        if updated_id:
            logger.info(
                "signup_updated",
                telegram_id=telegram_id,
                status=status.value,
            )
            return True
        return False

    async def is_confirmed(self, telegram_id: int) -> bool:
        """Check if user is already confirmed."""
        signup = await self.get_by_telegram_id(telegram_id)
        if signup and signup.status == SignupStatus.CONFIRMED.value:
            return True
        return False