"""Registration keyboards."""
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


CONSENT_TEXT = """
📋 Для продолжения необходимо ваше согласие на обработку персональных данных.

Нажимая "Согласен", вы даёте согласие на обработку ваших данных в соответствии с политикой конфиденциальности.

❌ Нажмите /start повторно, когда будете согласны.
"""