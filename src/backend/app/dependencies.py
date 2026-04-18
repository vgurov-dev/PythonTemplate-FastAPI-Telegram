from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.database import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_session():
        yield session


async def get_redis() -> Redis:
    """Dependency for Redis client."""
    from app.cache import redis_client

    return redis_client


async def verify_service_token(
    x_service_token: str = Header(...),
) -> str:
    """Verify service token for inter-service auth."""
    from app.config import settings
    from app.exceptions import UnauthorizedException

    if x_service_token != settings.service_key:
        raise UnauthorizedException(detail="Invalid service token")
    return x_service_token


DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]