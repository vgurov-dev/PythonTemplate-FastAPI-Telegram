"""Cache infrastructure package."""
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

import json

from redis.asyncio import Redis


T = TypeVar("T")


class CacheService(Generic[T], ABC):
    """Base cache service."""

    def __init__(self, redis: Redis, prefix: str = "cache"):
        self.redis = redis
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        value = await self.redis.get(self._make_key(key))
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: T, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        await self.redis.setex(
            self._make_key(key),
            ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        await self.redis.delete(self._make_key(key))

    async def clear(self) -> None:
        """Clear all keys with prefix."""
        pattern = f"{self.prefix}:*"
        async for key in self.redis.scan_iter(pattern):
            await self.redis.delete(key)