"""Basic bot handlers."""
from aiogram.types import Message


async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Добро пожаловать в бот."
    )


async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "Доступные команды:\n"
        "/start - Начать\n"
        "/help - Помощь\n"
    )


async def cmd_echo(message: Message) -> None:
    """Handle echo command."""
    await message.answer(message.text)