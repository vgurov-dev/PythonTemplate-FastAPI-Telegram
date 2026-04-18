"""Pytest configuration with TDD fixtures."""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
def anyio_memory_db_pool():
    """Create async in-memory SQL database for TDD tests."""
    return "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session(anyio_memory_db_pool) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    engine = create_async_engine(anyio_memory_db_pool, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client for API testing."""
    from bootstrap.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def client(http_client):
    """Alias for http_client."""
    return http_client


@pytest.fixture
def mock_session():
    """Create mock database session for TDD."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def mock_repository():
    """Create mock repository for TDD."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.get_all = AsyncMock(return_value=[])
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def sample_user_data():
    """Sample user data for TDD tests."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
    }


@pytest.fixture
def sample_users_list(sample_user_data):
    """List of sample users for testing."""
    return [sample_user_data]