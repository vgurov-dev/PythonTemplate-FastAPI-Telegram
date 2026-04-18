"""Main keyboard."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_keyboard() -> InlineKeyboardMarkup:
    """Create main keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Меню", callback_data="menu"),
                InlineKeyboardButton(text="Профиль", callback_data="profile"),
            ],
        ]
    )
    return keyboard