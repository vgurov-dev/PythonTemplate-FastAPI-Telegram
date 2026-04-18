from redis.asyncio import Redis, from_url

from app.config import settings


async def get_redis_client() -> Redis:
    """Create Redis client."""
    return from_url(
        settings.redis_url,
        password=settings.redis_password,
        encoding="utf-8",
        decode_responses=True,
    )


redis_client: Redis = None


async def init_redis() -> None:
    """Initialize Redis client."""
    global redis_client
    redis_client = await get_redis_client()


async def close_redis() -> None:
    """Close Redis connection."""
    if redis_client:
        await redis_client.close()