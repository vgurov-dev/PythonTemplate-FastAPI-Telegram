"""Registration keyboard."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_agreement_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with agreement buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Согласен", callback_data="agree"),
                InlineKeyboardButton(text="❌ Не согласен", callback_data="disagree"),
            ],
        ]
    )