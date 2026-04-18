from typing import AsyncGenerator

from sqlmodel import SQLModel
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine

from app.config import settings


def create_engine() -> AsyncEngine:
    """Create async database engine."""
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
        pool_pre_ping=True,
        poolclass=pool.AsyncAdaptedQueuePool,
    )


engine = create_engine()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db() -> None:
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)