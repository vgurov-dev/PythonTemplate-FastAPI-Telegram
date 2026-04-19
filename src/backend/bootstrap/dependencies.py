from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from bootstrap.database import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_session():
        yield session


async def get_redis() -> Redis:
    """Dependency for Redis client."""
    from bootstrap.cache import redis_client

    return redis_client


DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]