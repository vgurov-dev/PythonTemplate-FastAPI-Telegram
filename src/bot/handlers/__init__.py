"""Registration handlers."""
from datetime import datetime

from aiogram import Router
from aiogram.types import CallbackQuery, Message
import structlog

from bot.app.config import settings
from bot.database import async_session
from bot.handlers.registration import get_agreement_keyboard, CONSENT_TEXT
from bot.models.signup import SignupStatus
from bot.services.signup import SignupService
from bot.tasks.sync import sync_user_to_backend

logger = structlog.get_logger()

router = Router()


@router.message()
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    user = message.from_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name

    async with async_session() as session:
        service = SignupService(session)

        existing = await service.get_by_telegram_id(telegram_id)
        if existing and existing.status == SignupStatus.CONFIRMED.value:
            await message.answer(
                f"Привет, {first_name}!\n\n"
                "Вы уже подтвердили согласие на обработку данных.",
            )
            return

        await service.create_signup(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

    await message.answer(
        f"Привет, {first_name}!\n\n{CONSENT_TEXT}",
        reply_markup=get_agreement_keyboard(),
    )


@router.callback_query()
async def handle_agreement(callback: CallbackQuery) -> None:
    """Handle agreement buttons."""
    user = callback.from_user
    telegram_id = user.id
    first_name = user.first_name
    data = callback.data

    await callback.answer()

    if data == "disagree":
        await callback.message.answer(
            "❌ Нажмите /start повторно, когда будете согласны.",
        )
        return

    if data != "agree":
        return

    async with async_session() as session:
        service = SignupService(session)

        if await service.is_confirmed(telegram_id):
            await callback.message.answer(
                f"Привет, {first_name}!\n\n"
                "Вы уже подтвердили согласие ранее.",
            )
            return

        await service.update_status(
            telegram_id=telegram_id,
            status=SignupStatus.CONFIRMED,
        )

        signup = await service.get_by_telegram_id(telegram_id)

    sync_user_to_backend.delay(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )

    logger.info("user_confirmed", telegram_id=telegram_id)

    await callback.message.answer(
        f"✅ Спасибо, {first_name}!\n\n"
        "Вы успешно зарегистрированы.",
    )