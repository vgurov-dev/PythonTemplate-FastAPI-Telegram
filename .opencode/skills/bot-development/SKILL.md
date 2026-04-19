---
name: bot-development
description: Comprehensive bot development with aiogram 3 - FSM, handlers, middleware, filters, error handling, Celery integration
license: MIT
compatibility: opencode
metadata:
  audience: bot-developers
  workflow: bot
---

# Bot Development Skill

## Role

Developer building Telegram bots with aiogram 3. This skill covers the full bot development lifecycle including FSM, handlers, middleware, filters, webhook/polling, error handling, and integration with backend services.

## Project Structure

```
src/bot/
├── app/
│   ├── __init__.py
│   └── config.py          # Bot configuration
├── handlers/
│   ├── __init__.py
│   ├── basic.py            # Basic commands (start, help)
│   ├── registration.py     # Registration flow
│   └── callback.py         # Callback query handlers
├── keyboards/
│   ├── __init__.py
│   ├── registration.py     # Registration keyboards
│   └── main.py             # Main menu keyboard
├── services/
│   ├── __init__.py
│   ├── signup.py           # Signup service (HTTP to backend)
│   └── user.py             # User service
├── tasks/
│   ├── __init__.py
│   └── sync.py             # Celery tasks for async operations
├── models/
│   ├── __init__.py
│   ├── base.py             # Base model
│   └── signup.py           # Signup model
├── database.py             # Database connection
├── main.py                 # Bot entry point
└── tests/
    ├── __init__.py
    ├── unit/
    └── integration/
```

## Bot Entry Point

### main.py

```python
# src/bot/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command
from aiogram.filters.state import StateFilter

from bot.app.config import settings
from bot.database import init_bot_db, close_bot_db
from bot.handlers import router as main_router
from bot.middleware.logging import LoggingMiddleware
from bot.middleware.throttling import ThrottlingMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(dp: Dispatcher):
    """Bot lifespan handler."""
    logger.info("bot_starting", debug=settings.bot_debug)

    # Initialize database
    await init_bot_db()

    # Setup middleware
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware(rate_limit=10, interval=60))
    dp.callback_query.middleware(LoggingMiddleware())

    yield

    logger.info("bot_shutting_down")
    await close_bot_db()


async def main():
    """Run bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Initialize bot
    bot = Bot(token=settings.bot_token)

    # Initialize Redis storage for FSM
    storage = RedisStorage.from_url(
        settings.redis_url,
        state_ttl=settings.fsm_state_ttl,
        data_ttl=settings.fsm_data_ttl,
    )

    # Create dispatcher with lifespan
    dp = Dispatcher(
        bot=bot,
        storage=storage,
        lifespan=lifespan,
    )

    # Include routers
    dp.include_router(main_router)

    # Start polling
    logger.info("bot_started", debug=settings.bot_debug)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, close_bot_session=True)


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### app/config.py

```python
# src/bot/app/config.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Bot
    bot_token: str = Field(
        validation_alias="BOT_TOKEN",
    )
    bot_debug: bool = Field(
        default=False,
        validation_alias="BOT_DEBUG",
    )

    # Redis for FSM
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    redis_password: Optional[str] = Field(
        default=None,
        validation_alias="REDIS_PASSWORD",
    )

    # FSM TTL (in seconds)
    fsm_state_ttl: int = Field(
        default=86400,  # 24 hours
        validation_alias="FSM_STATE_TTL",
    )
    fsm_data_ttl: int = Field(
        default=86400,
        validation_alias="FSM_DATA_TTL",
    )

    # Backend communication
    backend_url: str = Field(
        default="http://backend:8000",
        validation_alias="BACKEND_URL",
    )
    service_token: str = Field(
        validation_alias="SERVICE_TOKEN",
    )

    # HTTP client
    http_timeout: float = Field(
        default=10.0,
        validation_alias="HTTP_TIMEOUT",
    )


settings = Settings()
```

## Inline Keyboard (from bot-handlers)

### Keyboard Creation

```python
# src/bot/keyboards/registration.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def registration_start_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for registration start."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📝 Начать регистрацию",
            callback_data="registration:start",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="registration:help",
        )
    )
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for confirmation."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data="registration:confirm",
        ),
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="registration:cancel",
        ),
    )
    return builder.as_markup()
```

### Main Menu Keyboard

```python
# src/bot/keyboards/main.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu reply keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="⚙️ Настройки"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📞 Поддержка"),
    )
    return builder.as_markup(resize_keyboard=True)
```

## Handlers

### Basic Handlers

```python
# src/bot/handlers/basic.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import structlog

router = Router()
logger = structlog.get_logger()


class MainStates(StatesGroup):
    """Main bot states."""
    idle = State()
    in_menu = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    logger.info("start_command", user_id=message.from_user.id)

    await message.answer(
        "Добро пожаловать! 👋\n\n"
        "Используйте меню ниже для навигации.",
        reply_markup=main_keyboard(),
    )
    await state.set_state(MainStates.in_menu)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = (
        "📖 <b>Справка</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/profile - Ваш профиль\n\n"
        "Для регистрации нажмите кнопку в меню."
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "👤 Профиль")
async def handle_profile(message: Message, state: FSMContext):
    """Handle profile button."""
    current_state = await state.get_state()
    logger.info("profile_request", user_id=message.from_user.id, state=current_state)

    await message.answer(
        "👤 <b>Ваш профиль</b>\n\n"
        "Загружается...",
        parse_mode="HTML",
    )
```

### Registration Flow with FSM

```python
# src/bot/handlers/registration.py
from aiogram import Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import structlog

from bot.keyboards.registration import registration_start_keyboard, confirm_keyboard
from bot.services.signup import SignupService

router = Router()
logger = structlog.get_logger()


class RegistrationStates(StatesGroup):
    """Registration FSM states."""
    waiting_for_username = State()
    waiting_for_confirm = State()
    completed = State()


@router.message(Command("register"))
@router.callback_query(F.data == "registration:start")
async def registration_start(
    event: Message | CallbackQuery,
    state: FSMContext,
):
    """Start registration flow."""
    user = event.from_user
    logger.info(
        "registration_started",
        user_id=user.id,
        username=user.username,
    )

    await state.set_state(RegistrationStates.waiting_for_username)

    message_text = (
        "📝 <b>Регистрация</b>\n\n"
        f"Привет, {user.first_name}!\n\n"
        "Пожалуйста, введите ваше имя пользователя.\n"
        "Оно будет отображаться в системе."
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard(),
        )
    else:
        await event.answer(message_text, parse_mode="HTML")


@router.message(StateFilter(RegistrationStates.waiting_for_username))
async def process_username(
    message: Message,
    state: FSMContext,
):
    """Process username input."""
    username = message.text.strip()

    if len(username) < 3:
        await message.answer(
            "❌ Имя пользователя должно быть минимум 3 символа.\n"
            "Попробуйте ещё раз:"
        )
        return

    if len(username) > 30:
        await message.answer(
            "❌ Имя пользователя слишком длинное (максимум 30 символов).\n"
            "Попробуйте ещё раз:"
        )
        return

    # Save to FSM
    await state.update_data(username=username)

    await state.set_state(RegistrationStates.waiting_for_confirm)

    await message.answer(
        f"✅ <b>Имя сохранено:</b> {username}\n\n"
        "Нажмите 'Подтвердить' для завершения регистрации.",
        parse_mode="HTML",
        reply_markup=confirm_keyboard(),
    )


@router.callback_query(F.data == "registration:confirm", StateFilter(RegistrationStates.waiting_for_confirm))
async def confirm_registration(
    callback: CallbackQuery,
    state: FSMContext,
    dp: Dispatcher,
):
    """Confirm registration."""
    await callback.answer()  # IMPORTANT: Always answer callback!

    user_data = await state.get_data()
    username = user_data.get("username")

    try:
        signup_service = SignupService()
        result = await signup_service.register(
            telegram_id=callback.from_user.id,
            username=username,
            first_name=callback.from_user.first_name,
        )

        logger.info(
            "registration_completed",
            user_id=callback.from_user.id,
            username=username,
        )

        # Delete keyboard message
        await callback.message.delete()

        await callback.message.answer(
            f"🎉 <b>Регистрация завершена!</b>\n\n"
            f"Добро пожаловать, {username}!",
            parse_mode="HTML",
        )

    except SignupServiceError as e:
        logger.error(
            "registration_failed",
            user_id=callback.from_user.id,
            error=str(e),
        )
        await callback.message.answer(
            f"❌ Ошибка регистрации: {e}\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )

    finally:
        await state.clear()


@router.callback_query(F.data == "registration:cancel")
async def cancel_registration(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Cancel registration."""
    await callback.answer()
    await callback.message.delete()
    await state.clear()

    await callback.message.answer(
        "❌ Регистрация отменена.\n\n"
        "Используйте /register для начала новой регистрации.",
    )
```

## Middleware

### Logging Middleware

```python
# src/bot/middleware/logging.py
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Update
import structlog

logger = structlog.get_logger()


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all updates."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        start_time = time.time()

        # Get user info if available
        user: User | None = data.get("event_from_user")
        user_id = user.id if user else None
        username = user.username if user else None

        # Log incoming update
        update: Update = data.get("update")
        update_type = self._get_update_type(update)

        logger.debug(
            "update_received",
            update_type=update_type,
            user_id=user_id,
            username=username,
        )

        try:
            result = await handler(event, data)

            duration = time.time() - start_time
            logger.info(
                "update_processed",
                update_type=update_type,
                user_id=user_id,
                duration_ms=round(duration * 1000, 2),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "update_failed",
                update_type=update_type,
                user_id=user_id,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise

    def _get_update_type(self, update: Update) -> str:
        """Determine update type."""
        if update.message:
            return "message"
        elif update.callback_query:
            return "callback_query"
        elif update.edited_message:
            return "edited_message"
        elif update.inline_query:
            return "inline_query"
        return "unknown"
```

### Throttling Middleware

```python
# src/bot/middleware/throttling.py
import time
from typing import Any, Awaitable, Callable, Dict
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import structlog

logger = structlog.get_logger()


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting."""

    def __init__(self, rate_limit: int = 10, interval: int = 60):
        self.rate_limit = rate_limit
        self.interval = interval
        self.user_requests: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id
        now = time.time()

        # Clean old requests
        self.user_requests[user_id] = [
            ts for ts in self.user_requests[user_id]
            if now - ts < self.interval
        ]

        # Check rate limit
        if len(self.user_requests[user_id]) >= self.rate_limit:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                requests=len(self.user_requests[user_id]),
            )
            # Let the handler process but could send warning
            # return # Uncomment to block

        # Record request
        self.user_requests[user_id].append(now)

        return await handler(event, data)
```

## Filters

### Custom Filters

```python
# src/bot/filters/is_registered.py
from typing import Optional
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import structlog

logger = structlog.get_logger()


class IsRegisteredFilter(BaseFilter):
    """Filter to check if user is registered."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        # In real implementation, check against database
        # For now, check FSM state
        state: Optional[FSMContext] = event.choose("fsm_state" if isinstance(event, Message) else "fsm_state")

        if state:
            current_state = await state.get_state()
            return current_state != "RegistrationStates:waiting_for_username"

        return True


class AdminFilter(BaseFilter):
    """Filter to check if user is admin."""

    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in self.admin_ids
```

## Bot Service (HTTP to Backend)

### Signup Service

```python
# src/bot/services/signup.py
import httpx
from typing import Optional
import structlog

from bot.app.config import settings

logger = structlog.get_logger()


class SignupServiceError(Exception):
    """Base exception for signup service."""
    pass


class SignupServiceUnavailable(SignupServiceError):
    """Backend is unavailable."""
    pass


class SignupServiceUnauthorized(SignupServiceError):
    """Invalid service token."""
    pass


class SignupService:
    """Service for handling signup via backend API."""

    def __init__(
        self,
        backend_url: str = settings.backend_url,
        service_token: str = settings.service_token,
        timeout: float = settings.http_timeout,
    ):
        self._backend_url = backend_url
        self._service_token = service_token
        self._timeout = timeout

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._service_token}",
            "Content-Type": "application/json",
        }

    async def register(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
    ) -> dict:
        """Register user via backend API."""
        logger.info(
            "signup_request",
            telegram_id=telegram_id,
            username=username,
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._backend_url}/api/bot/signup",
                    json={
                        "telegram_id": telegram_id,
                        "username": username,
                        "first_name": first_name,
                    },
                    headers=self._get_headers(),
                )

                if response.status_code == 401:
                    logger.error("signup_unauthorized")
                    raise SignupServiceUnauthorized("Invalid service token")

                if response.status_code >= 500:
                    logger.error("signup_backend_error", status=response.status_code)
                    raise SignupServiceUnavailable("Backend unavailable")

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                logger.error("signup_timeout")
                raise SignupServiceUnavailable("Request timeout")

            except httpx.NetworkError as e:
                logger.error("signup_network_error", error=str(e))
                raise SignupServiceUnavailable("Network error")
```

## Celery Integration

```python
# src/bot/tasks/sync.py
import asyncio
from celery import Celery
import structlog

logger = structlog.get_logger()

celery = Celery("bot")


def run_async(coro):
    """Run async coroutine from sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery.task(
    bind=True,
    name="bot.send_welcome",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_welcome_message(self, telegram_id: int, username: str):
    """Send welcome message to new user."""
    logger.info("send_welcome_started", telegram_id=telegram_id)

    async def _send():
        from bot.main import bot
        from bot.keyboards.main import main_keyboard

        await bot.send_message(
            chat_id=telegram_id,
            text=f"Добро пожаловать, {username}! 👋\n\n"
                 f"Рады видеть вас в нашем сервисе!",
            reply_markup=main_keyboard(),
        )

    try:
        run_async(_send())
        logger.info("send_welcome_completed", telegram_id=telegram_id)

    except Exception as exc:
        logger.warning(
            "send_welcome_retry",
            telegram_id=telegram_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)
```

## Error Handling

### Global Error Handler

```python
# src/bot/handlers/errors.py
from aiogram import Router, Dispatcher
from aiogram.types import Update
from aiogram.filters import ExceptionTypeFilter
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
import structlog

logger = structlog.get_logger()
router = Router()


@router.errors(ExceptionTypeFilter(TelegramNetworkError))
async def handle_network_error(event: Update, exception: TelegramNetworkError):
    """Handle Telegram network errors."""
    logger.error(
        "telegram_network_error",
        error=str(exception),
        update_id=event.update_id,
    )
    # Telegram will retry automatically


@router.errors(ExceptionTypeFilter(TelegramAPIError))
async def handle_api_error(event: Update, exception: TelegramAPIError):
    """Handle Telegram API errors."""
    logger.error(
        "telegram_api_error",
        error=str(exception),
        update_id=event.update_id,
    )
    # Log and potentially notify admin


@router.errors()
async def handle_unknown_error(event: Update, exception: Exception):
    """Handle unknown errors."""
    logger.critical(
        "unknown_error",
        error=str(exception),
        update_id=event.update_id,
        traceback=traceback.format_exc(),
    )
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| No `callback.answer()` | "Loading..." indefinitely | Always answer callbacks |
| `edit_text` instead of `delete` + `answer` | Keyboard persists | Delete + send new |
| `time.sleep()` in handlers | Bot unresponsive | Use async sleep or FSM timers |
| Sync HTTP calls | Event loop blocking | Use httpx.AsyncClient |
| `print()` instead of structlog | No structured logs | Use structlog |
| No FSM timeout | State persists forever | Set FSM TTL |
| Handle in message handler instead of callback | No ack, multiple handling | Use callback_query |
| Catch all exceptions silently | Silent failures | Log and re-raise |
| No rate limiting | Bot can be spammed | Add throttling middleware |

## Testing

```python
# src/bot/tests/unit/test_handlers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User, Chat, CallbackQuery

from bot.handlers.registration import (
    registration_start,
    process_username,
    confirm_registration,
)


@pytest.fixture
def mock_message():
    """Create mock message."""
    user = User(id=123, is_bot=False, first_name="Test")
    chat = Chat(id=123, type="private")
    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.text = "testuser"
    return message


@pytest.fixture
def mock_state():
    """Create mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=None)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={"username": "testuser"})
    state.clear = AsyncMock()
    return state


@pytest.mark.asyncio
async def test_registration_start(mock_message, mock_state):
    """Test registration start."""
    mock_message.answer = AsyncMock()

    await registration_start(mock_message, mock_state)

    mock_message.answer.assert_called_once()
    mock_state.set_state.assert_called_once()


@pytest.mark.asyncio
async def test_process_username_too_short(mock_message, mock_state):
    """Test username too short."""
    mock_message.text = "ab"
    mock_message.answer = AsyncMock()

    await process_username(mock_message, mock_state)

    # Should ask to retry
    mock_message.answer.assert_called_once()
    assert "3 символа" in mock_message.answer.call_args[0][0]
```

## Checklist

Before deploying bot:

- [ ] All callback queries have `.answer()`
- [ ] Keyboards deleted and new message sent
- [ ] FSM states properly set and cleared
- [ ] Rate limiting middleware configured
- [ ] Logging middleware captures all updates
- [ ] HTTP errors mapped to domain exceptions
- [ ] Celery tasks have retry policies
- [ ] Bot token in environment, not code
- [ ] Backend URL configured via environment
- [ ] Health check configured
- [ ] Unit tests cover handlers
