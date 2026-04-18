"""Bot database configuration."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from bot.app.config import settings


engine = create_async_engine(
    settings.bot_database_url,
    echo=settings.bot_debug,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Get bot database session."""
    async with async_session() as session:
        yield session


async def init_bot_db() -> None:
    """Initialize bot database tables."""
    from bot.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_bot_db() -> None:
    """Close bot database connection."""
    await engine.dispose()