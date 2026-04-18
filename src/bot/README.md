# Bot

Telegram бот на aiogram 3.

## Стек

- **aiogram 3** — Telegram Bot API
- **Redis** — FSM storage

## Структура

```
bot/
├── app/            # Конфигурация
├── handlers/      # Обработчики сообщений
├── keyboards/     # Inline клавиатуры
└── services/     # Бизнес-логика
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Token от @BotFather |
| `REDIS_URL` | URL Redis |
| `BOT_DEBUG` | Режим отладки |

## Запуск

```bash
poetry install --with bot
poetry run python -m bot.main
```

## Примеры команд

```python
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message

bot = Bot(token="BOT_TOKEN")
dp = Dispatcher(bot)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет!")

dp.run_polling(bot)
```