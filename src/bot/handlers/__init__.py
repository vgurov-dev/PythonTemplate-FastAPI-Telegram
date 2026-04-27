"""Registration handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
import structlog

from bot.database import async_session
from bot.handlers.registration import CONSENT_TEXT
from bot.keyboards.registration import get_agreement_keyboard
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


@router.callback_query(F.data == "agree")
async def handle_agree(callback: CallbackQuery) -> None:
    """Handle agreement confirmation."""
    user = callback.from_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name

    await callback.answer()

    async with async_session() as session:
        service = SignupService(session)

        if await service.is_confirmed(telegram_id):
            await callback.message.delete()
            await callback.message.answer(
                f"Привет, {first_name}!\n\n"
                "Вы уже подтвердили согласие ранее.",
            )
            return

        await service.update_status(
            telegram_id=telegram_id,
            status=SignupStatus.CONFIRMED,
        )

    sync_user_to_backend.delay(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )

    logger.info("user_confirmed", telegram_id=telegram_id)

    await callback.message.delete()
    await callback.message.answer(
        f"✅ Спасибо, {first_name}!\n\n"
        "Вы успешно зарегистрированы.",
    )


@router.callback_query(F.data == "disagree")
async def handle_disagree(callback: CallbackQuery) -> None:
    """Handle disagreement."""
    await callback.answer()

    await callback.message.delete()
    await callback.message.answer(
        "❌ Нажмите /start повторно, когда будете согласны.",
    )