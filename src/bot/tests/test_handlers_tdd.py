"""TDD tests for bot handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.unit
@pytest.mark.tdd
class TestBotHandlers:
    """TDD tests for bot handlers."""

    @pytest.fixture
    def mock_message(self):
        """Mock message object."""
        message = MagicMock()
        message.message_id = 123
        message.from_user = MagicMock()
        message.from_user.id = 456
        message.from_user.first_name = "Test"
        message.from_user.username = "testuser"
        message.chat = MagicMock()
        message.chat.id = 789
        message.answer = AsyncMock()
        message.text = "/start"
        return message

    @pytest.mark.asyncio
    async def test_start_command_responds(self, mock_message):
        """TDD: /start command should respond with greeting."""
        from src.bot.handlers.basic import cmd_start

        await cmd_start(mock_message)

        mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command_responds(self, mock_message):
        """TDD: /help command should respond with help text."""
        from src.bot.handlers.basic import cmd_help

        await cmd_help(mock_message)

        mock_message.answer.assert_called_once()


@pytest.mark.unit
class TestBotKeyboards:
    """TDD tests for keyboards."""

    def test_main_keyboard_has_required_buttons(self):
        """TDD: Main keyboard should have required buttons."""
        from src.bot.keyboards.main import main_keyboard

        keyboard = main_keyboard()

        assert keyboard is not None
        assert len(keyboard.keyboard) > 0


@pytest.mark.unit
class TestBotServices:
    """TDD tests for bot services."""

    @pytest.mark.asyncio
    async def test_user_service_creates_user(self):
        """TDD: User service should create user."""
        from src.bot.services.user import UserService

        service = UserService()
        result = await service.create_user(
            telegram_id=123,
            username="testuser",
            first_name="Test"
        )

        assert result is not None