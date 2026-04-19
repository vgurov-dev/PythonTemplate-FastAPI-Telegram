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

**Файл:** `src/backend/infrastructure/database/repositories/user.py:37`

**Проблема:** `commit()` вызывается в репозитории — теряется контроль над транзакцией.

```python
# Сейчас
async def create(self, ...) -> User:
    user = User(...)
    self.session.add(user)
    await self.session.commit()  # ❌
    await self.session.refresh(user)
    return user
```

**Решение:** Убрать commit из репозитория, вызывать в Action.

**Шаги:**
1. Открыть `src/backend/infrastructure/database/repositories/user.py`
2. Изменить метод `create`:
   ```python
   async def create(
       self,
       telegram_id: int,
       username: Optional[str],
       first_name: str,
   ) -> User:
       """Create new user (no commit — call session.commit() in action)."""
       user = User(
           telegram_id=telegram_id,
           username=username,
           first_name=first_name,
       )
       self.session.add(user)
       await self.session.flush()  # Получаем ID без commit
       await self.session.refresh(user)
       return user
   ```

**Файлы:**
- `src/backend/infrastructure/database/repositories/user.py` — заменить `commit` на `flush`

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
   from uuid import UUID

   from pydantic import BaseModel, ConfigDict


   class CreateUserRequest(BaseModel):
       """Schema for creating user from Telegram."""

       telegram_id: int
       username: Optional[str] = None
       first_name: str


   class UserResponse(BaseModel):
       """User response schema."""

       model_config = ConfigDict(from_attributes=True)

       id: UUID
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

**Проблема:** Дублирование в `src/backend/api/routers/auth.py:54` и `src/backend/bootstrap/dependencies.py:23`.

**Решение:** Оставить только в `bootstrap/dependencies.py`, убрать из `auth.py`.

**Шаги:**
1. Открыть `src/backend/api/routers/auth.py`
2. Удалить функцию `verify_service_token` (строки 54-71)
3. Добавить импорт:
   ```python
   from bootstrap.dependencies import verify_service_token
   ```
4. Проверить что `users.py` уже импортирует из `bootstrap.dependencies` (да, строка 10)

**Файлы:**
- `src/backend/api/routers/auth.py` — удалить дубликат

---

## P2 — Средний приоритет

### 1.8 Создать domain exceptions

**Проблема:** `HTTPException` используется напрямую вместо доменных исключений.

**Шаги:**
1. Создать `src/backend/domain/exceptions.py`:
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
2. Обновить `src/backend/bootstrap/exceptions.py` — добавить маппинг:
   ```python
   from domain.exceptions import UserNotFoundError, DomainError

   # ... существующий код ...

   def setup_exception_handlers(app: FastAPI) -> None:
       """Register domain exception handlers."""

       @app.exception_handler(UserNotFoundError)
       async def user_not_found_handler(request, exc):
           return JSONResponse(
               status_code=404,
               content={"detail": str(exc)},
           )

       @app.exception_handler(DomainError)
       async def domain_error_handler(request, exc):
           return JSONResponse(
               status_code=400,
               content={"detail": str(exc)},
           )
   ```
3. Вызвать `setup_exception_handlers(app)` в `src/backend/bootstrap/main.py` после создания app

**Файлы:**
- `src/backend/domain/exceptions.py` — новый
- `src/backend/bootstrap/exceptions.py` — добавить handlers
- `src/backend/bootstrap/main.py` — вызвать setup

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

## P3 — Низкий приоритет (улучшения)

### 1.11 DI для Actions через Depends

**Решение:** Создать фабрику зависимостей.

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
- `src/backend/api/dependencies.py` — новый
- `src/backend/api/routers/users.py` — обновить Depends

---

## Checklist выполнения

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 1.1 | Исправить `username` в bot handler | P0 | ⬜ |
| 1.2 | Ограничить CORS | P0 | ⬜ |
| 1.3 | Создать CreateUserAction | P1 | ⬜ |
| 1.4 | Перенести commit из Repository | P1 | ⬜ |
| 1.5 | Перенести DTOs в `application/dto/` | P1 | ⬜ |
| 1.6 | Создать UserRepositoryProtocol | P1 | ⬜ |
| 1.7 | Унифицировать `verify_service_token` | P1 | ⬜ |
| 1.8 | Создать domain exceptions | P2 | ⬜ |
| 1.9 | Исправить deprecated `datetime.utcnow()` | P2 | ⬜ |
| 1.10 | Добавить healthchecks в dev docker-compose | P2 | ⬜ |
| 1.11 | DI для Actions через Depends | P3 | ⬜ |
| 1.12 | Замена UUID на int | P2 | ⬜ |

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
