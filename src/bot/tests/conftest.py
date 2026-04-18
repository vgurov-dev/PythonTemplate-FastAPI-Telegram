"""Pytest configuration for bot tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_bot():
    """Create mock aiogram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer = AsyncMock()
    return bot


@pytest.fixture
def mock_dispatcher():
    """Create mock dispatcher."""
    dp = MagicMock()
    dp.message = MagicMock()
    dp.callback_query = MagicMock()
    return dp


@pytest.fixture
def sample_message():
    """Create sample message object."""
    message = MagicMock()
    message.message_id = 123
    message.from_user.id = 456
    message.from_user.first_name = "Test"
    message.from_user.username = "testuser"
    message.text = "/start"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def sample_callback():
    """Create sample callback query."""
    callback = MagicMock()
    callback.id = " callback_123"
    callback.from_user.id = 456
    callback.data = "test_action"
    callback.message = MagicMock()
    callback.answer = AsyncMock()
    return callback