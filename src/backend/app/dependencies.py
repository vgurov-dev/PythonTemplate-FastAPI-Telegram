from typing import Annotated

from fastapi import Depends
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


DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]