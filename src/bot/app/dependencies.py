"""Bot dependencies."""
from typing import AsyncGenerator

from aiogram import Router
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import async_session
from bot.services.signup import SignupService


async def get_bot_session() -> AsyncGenerator[AsyncSession, None]:
    """Get bot database session."""
    async with async_session() as session:
        yield session


def get_signup_service(session: AsyncSession) -> SignupService:
    """Get signup service."""
    return SignupService(session)