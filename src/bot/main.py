import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from bot.app.config import settings


logger = structlog.get_logger()


async def main():
    """Run bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(bot=bot, storage=storage)

    logger.info("bot_started", debug=settings.bot_debug)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())