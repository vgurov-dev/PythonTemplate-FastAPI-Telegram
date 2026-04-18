import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command

from bot.app.config import settings
from bot.database import init_bot_db, close_bot_db
from bot.handlers import router as registration_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(dp: Dispatcher):
    """Bot lifespan handler."""
    logger.info("bot_starting", debug=settings.bot_debug)
    await init_bot_db()
    yield
    logger.info("bot_shutting_down")
    await close_bot_db()


async def main():
    """Run bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(bot=bot, storage=storage, lifespan=lifespan)

    dp.include_router(registration_router)

    logger.info("bot_started", debug=settings.bot_debug)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())