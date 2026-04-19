# Architecture Review — Implementation Plan

> Дата: 2026-04-19
> Статус: Draft
> Ревьюер: opencode

---

## P0 — Критичные (ломают prod)

### 1.1 Исправить `username` в bot handler

**Файл:** `src/bot/handlers/__init__.py:90`

**Проблема:** Переменная `username` не определена в области видимости `handle_agreement`.

```python
# Сейчас (БАГ)
sync_user_to_backend.delay(
    telegram_id=telegram_id,
    username=username,  # NameError!
    first_name=first_name,
)
```

**Решение:** Добавить `username` из `callback.from_user`.

**Шаги:**
1. Открыть `src/bot/handlers/__init__.py`
2. В функции `handle_agreement` добавить строку после `first_name = user.first_name`:
   ```python
   username = user.username
   ```
3. Проверить: запустить бот, нажать "Согласен", убедиться что task отправляется без ошибок

**Файлы:**
- `src/bot/handlers/__init__.py` — 1 строка

**Тест:** Ручной — нажать "Согласен" в боте, проверить логи Celery worker

---

### 1.2 Ограничить CORS

**Файл:** `src/backend/bootstrap/main.py:34-40`

**Проблема:** `allow_origins=["*"]` — любой домен может делать запросы.

```python
# Сейчас
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Решение:** Вынести origins в конфиг, использовать whitelist.

**Шаги:**
1. Открыть `src/backend/bootstrap/config.py`
2. Добавить поле:
   ```python
   cors_origins: list[str] = Field(
       default=["http://localhost:3000"],
       validation_alias="CORS_ORIGINS",
   )
   ```
3. Открыть `src/backend/bootstrap/main.py`
4. Заменить:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.cors_origins,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```
5. Открыть `.env.example`, добавить:
   ```
   CORS_ORIGINS=["http://localhost:3000","https://app.example.com"]
   ```

**Файлы:**
- `src/backend/bootstrap/config.py` — добавить поле
- `src/backend/bootstrap/main.py` — заменить middleware
- `.env.example` — добавить переменную

**Тест:** `curl -H "Origin: http://evil.com" -I http://localhost:8000/users/123` — должен получить CORS rejection

---

## P1 — Высокий приоритет (DDD violations)

### 1.3 Создать CreateUserAction

**Проблема:** Бизнес-логика создания пользователя в роутере `src/backend/api/routers/users.py:44-56`.

**Решение:** Вынести в `application/actions/users/create.py`.

**Шаги:**

1. Создать директорию `src/backend/application/actions/users/`
2. Создать `src/backend/application/actions/users/__init__.py`:
   ```python
   """Users actions package."""
   ```
3. Создать `src/backend/application/actions/users/create.py`:
   ```python
   """Create user action."""
   from sqlalchemy.ext.asyncio import AsyncSession

   from domain.entities.user import User
   from infrastructure.database.repositories.user import UserRepository
   from application.dto.users import CreateUserRequest, UserResponse


   class CreateUserAction:
       """Create or get existing user from Telegram."""

       def __init__(self, session: AsyncSession):
           self._repo = UserRepository(session)
           self._session = session

       async def execute(self, telegram_id: int, data: CreateUserRequest) -> UserResponse:
           """Execute create user action."""
           existing = await self._repo.get_by_telegram_id(telegram_id)
           if existing:
               return UserResponse.model_validate(existing)

           user = await self._repo.create(
               telegram_id=data.telegram_id,
               username=data.username,
               first_name=data.first_name,
           )
           await self._session.commit()
           return UserResponse.model_validate(user)
   ```
4. Создать `src/backend/application/actions/users/get.py`:
   ```python
   """Get user action."""
   from sqlalchemy.ext.asyncio import AsyncSession

   from infrastructure.database.repositories.user import UserRepository
   from application.dto.users import UserResponse
   from domain.exceptions import UserNotFoundError


   class GetUserAction:
       """Get user by Telegram ID."""

       def __init__(self, session: AsyncSession):
           self._repo = UserRepository(session)

       async def execute(self, telegram_id: int) -> UserResponse:
           """Execute get user action."""
           user = await self._repo.get_by_telegram_id(telegram_id)
           if not user:
               raise UserNotFoundError(f"User with telegram_id={telegram_id} not found")
           return UserResponse.model_validate(user)
   ```

5. Изменить `src/backend/api/routers/users.py`:
   ```python
   """Users API router."""
   from uuid import UUID

   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession

   from bootstrap.database import get_session
   from bootstrap.dependencies import verify_service_token
   from application.dto.users import CreateUserRequest, UserResponse
   from application.actions.users.create import CreateUserAction
   from application.actions.users.get import GetUserAction

   router = APIRouter(prefix="/users", tags=["users"])


   @router.post("/{telegram_id}/telegram", response_model=UserResponse)
   async def create_user_from_telegram(
       telegram_id: int,
       data: CreateUserRequest,
       _service_token: str = Depends(verify_service_token),
       session: AsyncSession = Depends(get_session),
   ) -> UserResponse:
       """Create or update user from Telegram bot."""
       action = CreateUserAction(session)
       return await action.execute(telegram_id, data)


   @router.get("/{telegram_id}", response_model=UserResponse)
   async def get_user(
       telegram_id: int,
       _service_token: str = Depends(verify_service_token),
       session: AsyncSession = Depends(get_session),
   ) -> UserResponse:
       """Get user by Telegram ID."""
       action = GetUserAction(session)
       return await action.execute(telegram_id)
   ```

**Файлы:**
- `src/backend/application/actions/users/__init__.py` — новый
- `src/backend/application/actions/users/create.py` — новый
- `src/backend/application/actions/users/get.py` — новый
- `src/backend/api/routers/users.py` — рефакторинг

---

### 1.4 Перенести commit из Repository в Action

**Проблема:** `commit()` вызывается в репозиториях — теряется контроль над транзакцией.

Затронутые файлы:
- `src/backend/infrastructure/database/repositories/user.py:37`
- `src/backend/infrastructure/database/repositories/__init__.py:35,41,50` (BaseRepository)

**Решение:** Убрать commit из всех репозиториев, вызывать в Action.

**Шаги:**

1. `src/backend/infrastructure/database/repositories/user.py` — заменить `commit` на `flush`:
   ```python
   async def create(self, telegram_id: int, username: Optional[str], first_name: str) -> User:
       user = User(telegram_id=telegram_id, username=username, first_name=first_name)
       self.session.add(user)
       await self.session.flush()
       await self.session.refresh(user)
       return user
   ```

2. `src/backend/infrastructure/database/repositories/__init__.py` — заменить `commit` на `flush` в BaseRepository:
   ```python
   async def create(self, entity: ModelType) -> ModelType:
       self.session.add(entity)
       await self.session.flush()
       await self.session.refresh(entity)
       return entity

   async def update(self, entity: ModelType) -> ModelType:
       await self.session.flush()
       await self.session.refresh(entity)
       return entity

   async def delete(self, id: int) -> bool:
       entity = await self.get(id)
       if entity:
           await self.session.delete(entity)
           await self.session.flush()
           return True
       return False
   ```

**Файлы:**
- `src/backend/infrastructure/database/repositories/user.py` — `commit` → `flush`
- `src/backend/infrastructure/database/repositories/__init__.py` — `commit` → `flush`

**Тест:** Интеграционный тест — создать пользователя, откатить транзакцию, проверить что в БД пусто

---

### 1.5 Перенести DTOs в `application/dto/`

**Файл:** `src/backend/api/routers/users.py:16-33`

**Проблема:** Схемы `UserCreateSchema` и `UserResponse` определены в роутере.

**Решение:** Создать `src/backend/application/dto/users.py`.

**Шаги:**
1. Создать `src/backend/application/dto/users.py`:
   ```python
   """Users DTO."""
   from typing import Optional

   from pydantic import BaseModel, ConfigDict


   class CreateUserRequest(BaseModel):
       """Schema for creating user from Telegram."""

       telegram_id: int
       username: Optional[str] = None
       first_name: str


   class UserResponse(BaseModel):
       """User response schema."""

       model_config = ConfigDict(from_attributes=True)

        id: int
        telegram_id: int
        username: Optional[str]
        first_name: str
        is_active: bool
    ```
2. Удалить `UserCreateSchema` и `UserResponse` из `src/backend/api/routers/users.py`
3. Обновить импорты в роутере (см. шаг 1.3)

**Файлы:**
- `src/backend/application/dto/users.py` — новый
- `src/backend/api/routers/users.py` — удалить inline схемы

---

### 1.6 Создать UserRepositoryProtocol в domain

**Проблема:** Репозиторий в infrastructure, но нет протокола в domain.

**Шаги:**
1. Создать `src/backend/domain/repositories/__init__.py`:
   ```python
   """Domain repositories package."""
   ```
2. Создать `src/backend/domain/repositories/user.py`:
   ```python
   """User repository protocol."""
   from typing import Protocol, Optional

   from domain.entities.user import User


   class UserRepositoryProtocol(Protocol):
       """Protocol for user repository."""

       async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]: ...

       async def create(
           self,
           telegram_id: int,
           username: Optional[str],
           first_name: str,
       ) -> User: ...

       async def exists(self, telegram_id: int) -> bool: ...
   ```
3. Обновить `src/backend/infrastructure/database/repositories/user.py` — добавить наследование:
   ```python
   from domain.repositories.user import UserRepositoryProtocol

   class UserRepository(UserRepositoryProtocol):
       ...
   ```

**Файлы:**
- `src/backend/domain/repositories/__init__.py` — новый
- `src/backend/domain/repositories/user.py` — новый
- `src/backend/infrastructure/database/repositories/user.py` — добавить наследование

---

### 1.7 Унифицировать `verify_service_token`

**Перенесено в шаг 1.13** — объединение всех зависимостей в `api/dependencies.py`.

Для справки — текущая проблема:
- `src/backend/api/routers/auth.py:54` — JWT-проверка
- `src/backend/bootstrap/dependencies.py:23` — простое сравнение строки

Логика несовместима. Решение описано в 1.13.

---

## P2 — Средний приоритет

### 1.8 Создать domain exceptions (и убрать дубликаты)

**Проблема:**
1. `HTTPException` используется напрямую вместо доменных исключений
2. `TokenExpiredError` и `TokenInvalidError` определены дважды:
   - `src/backend/domain/services/token.py:11-17` (наследуют `Exception`)
   - `src/backend/domain/exceptions.py` — если существует, дублирует

**Решение:** Единые доменные исключения в `domain/exceptions.py`, импорт оттуда.

**Шаги:**
1. Создать/обновить `src/backend/domain/exceptions.py`:
   ```python
   """Domain exceptions."""


   class DomainError(Exception):
       """Base domain exception."""
       pass


   class UserNotFoundError(DomainError):
       """User not found."""
       pass


   class TokenExpiredError(DomainError):
       """Token expired."""
       pass


   class TokenInvalidError(DomainError):
       """Token invalid."""
       pass
   ```

2. Удалить `TokenExpiredError` и `TokenInvalidError` из `src/backend/domain/services/token.py`, заменить импортом:
   ```python
   from domain.exceptions import TokenExpiredError, TokenInvalidError
   ```

3. Обновить `src/backend/bootstrap/exceptions.py` — добавить exception handlers:
   ```python
   from fastapi import FastAPI
   from fastapi.responses import JSONResponse
   from domain.exceptions import UserNotFoundError, DomainError

   def setup_exception_handlers(app: FastAPI) -> None:
       """Register domain exception handlers."""

       @app.exception_handler(UserNotFoundError)
       async def user_not_found_handler(request, exc):
           return JSONResponse(status_code=404, content={"detail": str(exc)})

       @app.exception_handler(DomainError)
       async def domain_error_handler(request, exc):
           return JSONResponse(status_code=400, content={"detail": str(exc)})
   ```

4. Вызвать `setup_exception_handlers(app)` в `src/backend/bootstrap/main.py` после создания app

5. Обновить импорты в `src/backend/application/actions/auth/refresh.py` — импортировать из `domain.exceptions`:
   ```python
   from domain.exceptions import TokenDomainService, TokenInvalidError, TokenExpiredError
   ```

**Файлы:**
- `src/backend/domain/exceptions.py` — создать/обновить
- `src/backend/domain/services/token.py` — удалить дубликаты, добавить импорт
- `src/backend/bootstrap/exceptions.py` — добавить handlers
- `src/backend/bootstrap/main.py` — вызвать setup
- `src/backend/application/actions/auth/refresh.py` — обновить импорт

---

### 1.9 Исправить deprecated `datetime.utcnow()`

**Проблема:** Используется deprecated `datetime.utcnow()`.

**Файлы для исправления:**

1. `src/bot/services/user.py:14`:
   ```python
   # Было
   created_at: datetime = datetime.utcnow()
   # Стало
   created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
   ```

2. `src/bot/models/signup.py:42`:
   ```python
   # Было
   default=datetime.utcnow,
   # Стало
   default=lambda: datetime.now(timezone.utc),
   ```

**Файлы:**
- `src/bot/services/user.py` — заменить
- `src/bot/models/signup.py` — заменить

---

### 1.10 Добавить healthchecks в dev docker-compose

**Файл:** `docker-compose.yml`

**Шаги:** Добавить healthcheck к postgres и redis:

```yaml
postgres:
  # ... существующий код ...
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U user -d myservice"]
    interval: 10s
    timeout: 5s
    retries: 5

redis:
  # ... существующий код ...
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Файлы:**
- `docker-compose.yml` — добавить healthchecks

---

### 1.12 Замена UUID на int

**Проблема:** Использование UUID для первичных ключей усложняет поиск, индексацию, дебаг. Для внутренних PK достаточно `int` с auto-increment.

**Правило:** НЕ использовать UUID как PK. Только `int` (SERIAL/BIGSERIAL). Исключение — внешние ID (telegram_id и т.п.).

**Файлы и изменения:**

1. `src/backend/domain/entities/user.py:16-20`:
   ```python
   # Было
   from uuid import UUID, uuid4
   id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)

   # Стало
   id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
   ```
   Удалить импорт `from uuid import UUID, uuid4`.

2. `src/backend/infrastructure/database/repositories/__init__.py:20,45`:
   ```python
   # Было
   from uuid import UUID
   async def get(self, id: UUID) -> Optional[ModelType]: ...
   async def delete(self, id: UUID) -> bool: ...

   # Стало
   async def get(self, id: int) -> Optional[ModelType]: ...
   async def delete(self, id: int) -> bool: ...
   ```
   Удалить импорт `from uuid import UUID`.

3. `src/bot/models/signup.py:24-28`:
   ```python
   # Было
   from uuid import UUID, uuid4
   from sqlalchemy.dialects.postgresql import BIGINT, UUID as PG_UUID
   id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

   # Стало
   from sqlalchemy import BigInteger
   id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
   ```
   Удалить импорты `UUID`, `uuid4`, `PG_UUID`.

4. `src/bot/services/signup.py:4`:
   ```python
   # Удалить unused import
   from uuid import UUID  # удалить
   ```

5. `src/backend/application/dto/users.py` (создаётся в шаге 1.5):
   ```python
   id: int  # не UUID
   ```

6. `src/kit/utils/__init__.py` — `generate_uuid()` нигде не вызывается. Удалить файл или оставить как утилиту.

7. `src/backend/tests/test_entity_tdd.py` — поправить тест, убрать `uuid4()`.

**Файлы:**
- `src/backend/domain/entities/user.py` — заменить UUID → int
- `src/backend/infrastructure/database/repositories/__init__.py` — заменить UUID → int
- `src/bot/models/signup.py` — заменить UUID → int
- `src/bot/services/signup.py` — удалить unused import
- `src/backend/application/dto/users.py` — id: int (шаг 1.5)
- `src/kit/utils/__init__.py` — удалить
- `src/backend/tests/test_entity_tdd.py` — поправить тест

**Миграция БД:**
```sql
-- backend
ALTER TABLE users DROP COLUMN id;
ALTER TABLE users ADD COLUMN id SERIAL PRIMARY KEY;

-- bot
ALTER TABLE signups DROP COLUMN id;
ALTER TABLE signups ADD COLUMN id BIGSERIAL PRIMARY KEY;
```

**Тест:** `pytest`, проверить что CRUD работает с int ID.

---

### 1.13 Объединить `verify_service_token` и зависимости в `api/dependencies.py`

**Проблема:** Зависимости разбросаны:
- `src/backend/api/routers/auth.py:54` — свой `verify_service_token` (JWT)
- `src/backend/bootstrap/dependencies.py:23` — другой `verify_service_token` (header)
- `src/backend/api/routers/depends.py` — ещё один набор зависимостей

Логика несовместима: `auth.py` проверяет JWT, `bootstrap/dependencies.py` сравнивает строку.

**Решение:** Один модуль `api/dependencies.py` с единой логикой JWT-верификации.

**Шаги:**

1. Переписать `src/backend/api/dependencies.py` — объединить всё:
   ```python
   """API dependencies."""
   from functools import lru_cache
   from typing import Annotated, AsyncGenerator

   from fastapi import Depends, Header
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
   from sqlalchemy.ext.asyncio import AsyncSession

   from bootstrap.config import settings
   from bootstrap.database import get_session
   from bootstrap.exceptions import UnauthorizedException
   from domain.services.token import TokenDomainService, TokenInvalidError, create_token_service

   security = HTTPBearer(auto_error=False)


   @lru_cache
   def get_token_service() -> TokenDomainService:
       """Get token service instance."""
       return create_token_service(
           secret_key=settings.jwt_secret_key,
           algorithm=settings.jwt_algorithm,
       )


   def verify_service_token(
       credentials: HTTPAuthorizationCredentials = Depends(security),
   ) -> TokenDomainService:
       """Verify JWT service token."""
       if not credentials:
           raise UnauthorizedException(detail="Service token required")
       token_service = get_token_service()
       try:
           return token_service.verify_token(credentials.credentials)
       except TokenInvalidError:
           raise UnauthorizedException(detail="Invalid token")


   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       """Dependency for database session."""
       async for session in get_session():
           yield session


   DBSession = Annotated[AsyncSession, Depends(get_db)]
   ```

2. Удалить `src/backend/api/routers/depends.py` — перенести нужные импорты

3. Удалить `verify_service_token` из `src/backend/api/routers/auth.py` (строки 54-71), использовать импорт:
   ```python
   from api.dependencies import verify_service_token, get_token_service
   ```

4. Удалить `verify_service_token` из `src/backend/bootstrap/dependencies.py`

5. Обновить импорт в `src/backend/api/routers/users.py`:
   ```python
   from api.dependencies import verify_service_token
   ```

**Файлы:**
- `src/backend/api/dependencies.py` — переписать
- `src/backend/api/routers/depends.py` — удалить
- `src/backend/api/routers/auth.py` — удалить дубликат, обновить импорт
- `src/backend/bootstrap/dependencies.py` — удалить `verify_service_token`
- `src/backend/api/routers/users.py` — обновить импорт

---

### 1.14 DI для Bot через aiogram Depends

**Проблема:** Bot handlers создают сессию вручную:
```python
# src/bot/handlers/__init__.py:29
async with async_session() as session:
    service = SignupService(session)
```

Нарушает: «Не инстанцировать сервисы вручную в роутерах».

**Решение:** Использовать aiogram Depends для инъекции сессии.

**Шаги:**

1. Создать `src/bot/app/dependencies.py`:
   ```python
   """Bot dependencies."""
   from typing import AsyncGenerator

   from aiogram import Router
   from sqlalchemy.ext.asyncio import AsyncSession

   from bot.database import async_session
   from bot.services.signup import SignupService


   async def get_bot_session() -> AsyncGenerator[AsyncSession, None]:
       """Get bot database session."""
       async with async_session() as session:
           yield session


   def get_signup_service(session: AsyncSession = Depends(get_bot_session)) -> SignupService:
       """Get signup service."""
       return SignupService(session)
   ```

2. Обновить `src/bot/handlers/__init__.py` — использовать Depends:
   ```python
   from aiogram import Router, F
   from aiogram.types import CallbackQuery, Message
   from aiogram.fsm.context import FSMContext

   from bot.app.dependencies import get_signup_service
   from bot.models.signup import SignupStatus

   router = Router()


   @router.message()
   async def cmd_start(
       message: Message,
       service: SignupService = Depends(get_signup_service),
   ) -> None:
       telegram_id = message.from_user.id
       username = message.from_user.username
       first_name = message.from_user.first_name

       existing = await service.get_by_telegram_id(telegram_id)
       if existing and existing.status == SignupStatus.CONFIRMED.value:
           await message.answer(f"Привет, {first_name}! Вы уже подтвердили.")
           return

       await service.create_signup(telegram_id=telegram_id, username=username, first_name=first_name)
       await message.answer(f"Привет, {first_name}!\n\n{CONSENT_TEXT}", reply_markup=get_agreement_keyboard())


   @router.callback_query(F.data == "agree")
   async def handle_agree(
       callback: CallbackQuery,
       service: SignupService = Depends(get_signup_service),
   ) -> None:
       telegram_id = callback.from_user.id
       first_name = callback.from_user.first_name
       username = callback.from_user.username

       await callback.answer()

       if await service.is_confirmed(telegram_id):
           await callback.message.delete()
           await callback.message.answer(f"Привет, {first_name}! Вы уже подтвердили.")
           return

       await service.update_status(telegram_id=telegram_id, status=SignupStatus.CONFIRMED)
       sync_user_to_backend.delay(telegram_id=telegram_id, username=username, first_name=first_name)

       await callback.message.delete()
       await callback.message.answer(f"Спасибо, {first_name}! Вы успешно зарегистрированы.")
   ```

**Файлы:**
- `src/bot/app/dependencies.py` — новый
- `src/bot/handlers/__init__.py` — рефакторинг

---

### 1.15 `get_current_user` — возвращать DTO вместо dict

**Проблема:** `src/backend/api/routers/depends.py:31` возвращает `dict`.

**Решение:** Создать Pydantic модель и использовать её.

**Шаги:**

1. Добавить в `src/backend/application/dto/auth.py`:
   ```python
   class TokenPayloadDTO(BaseModel):
       """Token payload DTO."""
       service: str
       exp: int
       iat: int
   ```

2. Обновить `get_current_user` в `src/backend/api/dependencies.py`:
   ```python
   from application.dto.auth import TokenPayloadDTO

   async def get_current_user(
       credentials: HTTPAuthorizationCredentials = Depends(security),
   ) -> TokenPayloadDTO:
       """Get current authenticated user."""
       if not credentials:
           raise UnauthorizedException(detail="Not authenticated")
       token_service = get_token_service()
       try:
           payload = token_service.verify_token(credentials.credentials)
           return TokenPayloadDTO(
               service=payload.service,
               exp=payload.exp,
               iat=payload.iat,
           )
       except TokenInvalidError:
           raise UnauthorizedException(detail="Invalid token")


   CurrentUser = Annotated[TokenPayloadDTO, Depends(get_current_user)]
   ```

**Файлы:**
- `src/backend/application/dto/auth.py` — добавить `TokenPayloadDTO`
- `src/backend/api/dependencies.py` — обновить возвращаемый тип

---

## P3 — Низкий приоритет (улучшения)

### 1.11 DI для Actions через Depends (после 1.13)

**Предусловие:** Шаг 1.13 создал `api/dependencies.py` с базовыми зависимостями.

**Решение:** Добавить фабрики Actions в существующий `api/dependencies.py`.

**Шаги:**
1. Создать `src/backend/api/dependencies.py`:
   ```python
   """API dependencies."""
   from sqlalchemy.ext.asyncio import AsyncSession
   from fastapi import Depends

   from bootstrap.database import get_session
   from application.actions.users.create import CreateUserAction
   from application.actions.users.get import GetUserAction


   def get_create_user_action(
       session: AsyncSession = Depends(get_session),
   ) -> CreateUserAction:
       """Get create user action."""
       return CreateUserAction(session)


   def get_get_user_action(
       session: AsyncSession = Depends(get_session),
   ) -> GetUserAction:
       """Get get user action."""
       return GetUserAction(session)
   ```
2. Обновить роутер:
   ```python
   @router.post("/{telegram_id}/telegram", response_model=UserResponse)
   async def create_user_from_telegram(
       telegram_id: int,
       data: CreateUserRequest,
       _service_token: str = Depends(verify_service_token),
       action: CreateUserAction = Depends(get_create_user_action),
   ) -> UserResponse:
       return await action.execute(telegram_id, data)
   ```

**Файлы:**
- `src/backend/api/dependencies.py` — добавить фабрики
- `src/backend/api/routers/users.py` — обновить Depends

---

## Checklist выполнения

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 1.1 | Исправить `username` в bot handler | P0 | ⬜ |
| 1.2 | Ограничить CORS | P0 | ⬜ |
| 1.3 | Создать CreateUserAction | P1 | ⬜ |
| 1.4 | Перенести commit из Repository (включая BaseRepository) | P1 | ⬜ |
| 1.5 | Перенести DTOs в `application/dto/` | P1 | ⬜ |
| 1.6 | Создать UserRepositoryProtocol | P1 | ⬜ |
| 1.7 | Унифицировать `verify_service_token` | P1 | ⬜ |
| 1.8 | Domain exceptions + убрать дубликаты Token*Error | P1 | ⬜ |
| 1.9 | Исправить deprecated `datetime.utcnow()` | P2 | ⬜ |
| 1.10 | Добавить healthchecks в dev docker-compose | P2 | ⬜ |
| 1.11 | DI для Actions через Depends | P3 | ⬜ |
| 1.12 | Замена UUID на int | P2 | ⬜ |
| 1.13 | Объединить зависимости в `api/dependencies.py` | P1 | ⬜ |
| 1.14 | DI для Bot через aiogram Depends | P2 | ⬜ |
| 1.15 | `get_current_user` — DTO вместо dict | P2 | ⬜ |

---

## Verification

После всех изменений выполнить:

```bash
# Lint
cd src/backend && ruff check .
cd src/bot && ruff check .

# Typecheck
cd src/backend && mypy .
cd src/bot && mypy .

# Tests
cd src/backend && pytest
cd src/bot && pytest

# Smoke test
docker-compose up -d
curl http://localhost:8000/health
```
