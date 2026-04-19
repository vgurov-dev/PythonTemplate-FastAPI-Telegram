---
name: architecture-review
description: Architectural oversight combining developer practices and security analysis
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: review
---

# Architecture Review Skill

## Когда использовать

При review PR, создании новых модулей, добавлении endpoints или изменении бизнес-логики.

## Чеклист

### 1. DDD Compliance

- [ ] Бизнес-логика только в `domain/services/` или `application/actions/`
- [ ] API routers — только orchestration (вызов actions, возврат response)
- [ ] Валидация через `application/dto/`, не в domain
- [ ] Репозитории в `infrastructure/database/repositories/`

**ПРАВИЛЬНО:**
```python
# api/routers/auth.py
@router.post("/login")
async def login(data: LoginRequest, session: AsyncSession):
    action = LoginAction(session)
    return await action.execute(data)
```

**НЕПРАВИЛЬНО:**
```python
# api/routers/auth.py
@router.post("/login")
async def login(data: LoginRequest, session: AsyncSession):
    token = jwt.encode({"sub": data.username}, SECRET)  # логика в роутере!
    return {"token": token}
```

### 2. Security

- [ ] Все endpoints защищены `Depends(verify_service_token)` или JWT auth
- [ ] Нет хардкода секретов (только env + Pydantic `validation_alias`)
- [ ] `response_model` указан на всех endpoints
- [ ] Межсервисная коммуникация через service_token

**ПРАВИЛЬНО:**
```python
@router.post("/users", dependencies=[Depends(verify_service_token)])
async def create_user(data: UserCreate, ...) -> UserResponse:
    ...
```

**НЕПРАВИЛЬНО:**
```python
SECRET = "my_super_secret"  # хардкод!

@router.post("/users")  # нет auth!
async def create_user(data: dict, ...):  # нет response_model!
    ...
```

### 3. CORS / Rate Limiting

- [ ] CORS настроен whitelist-ом, не `allow_origins=["*"]`
- [ ] Rate limiting на публичных endpoints
- [ ] Приватные сервисы (bot, celery) не доступны извне

**ПРАВИЛЬНО:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)
```

**НЕПРАВИЛЬНО:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # открытый CORS!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Infrastructure

- [ ] Контейнеры запускаются не от root
- [ ] Staging использует образы из GHCR (не build из исходников)
- [ ] Health checks настроены на всех сервисах
- [ ] Сетевая изоляция: bot ↔ backend через API, не напрямую к БД

**ПРАВИЛЬНО:**
```yaml
# docker-compose.staging.yml
backend:
  image: ghcr.io/org/backend:1.2.0
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

**НЕПРАВИЛЬНО:**
```yaml
backend:
  build: ./src/backend  # staging не должен собирать из исходников
  # нет healthcheck
```

### 5. Bot-specific

- [ ] `callback.answer()` вызывается всегда
- [ ] Сообщение с keyboard удаляется после нажатия
- [ ] Импорты клавиатур из `bot.keyboards.*`, не из `bot.handlers.*`
- [ ] Межсервисные запросы используют service_token

**ПРАВИЛЬНО:**
```python
@router.callback_query()
async def handle_button(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Новое сообщение")
```

**НЕПРАВИЛЬНО:**
```python
@router.callback_query()
async def handle_button(callback: CallbackQuery):
    # нет answer() — часики зависнут
    await callback.message.edit_text("Ответ")  # edit вместо delete + new
```

### 6. Code Quality

- [ ] Python файлы: `snake_case.py`
- [ ] TypeScript файлы: `camelCase.ts`
- [ ] Зависимости через Poetry (группы: backend, bot, dev), не pip
- [ ] Коммиты: `feat(bot):`, `feat(backend):`, `fix:`, `refactor:`
- [ ] Все env-переменные в `.env.example` с описаниями

**ПРАВИЛЬНО:**
```toml
# pyproject.toml
[tool.poetry.group.backend.dependencies]
fastapi = "^0.104.0"
```

**НЕПРАВИЛЬНО:**
```txt
# requirements.txt — не используем!
fastapi==0.104.0
```

### 7. Async Patterns

- [ ] `async def` для всех I/O-операций (БД, HTTP, файлы)
- [ ] CPU-bound задачи — через `asyncio.to_thread` или `run_in_executor`
- [ ] AsyncSession через Depends, не ручное создание
- [ ] Не использовать `time.sleep` — только `asyncio.sleep`

**ПРАВИЛЬНО:**
```python
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    repo = UserRepository(session)
    users = await repo.get_all()  # async I/O
    return users

# CPU-bound задача
async def generate_report(data: ReportData):
    result = await asyncio.to_thread(heavy_computation, data)
    return result
```

**НЕПРАВИЛЬНО:**
```python
session = AsyncSession(engine)  # ручное создание, нет DI!

@router.get("/users")
def list_users():  # sync в async-фреймворке!
    time.sleep(1)  # блокирует event loop!
    users = repo.get_all()  # sync вызов к БД!
    return users
```

### 8. Dependency Injection

- [ ] Сессии БД, конфигурация, сервисы — через `Depends`
- [ ] Не инстанцировать сервисы вручную в роутерах
- [ ] Провайдеры в отдельном модуле `api/dependencies.py`
- [ ] Repository передаётся в Action через DI

**ПРАВИЛЬНО:**
```python
# api/dependencies.py
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

def get_user_service(session: AsyncSession = Depends(get_session)):
    return UserDomainService(UserRepository(session))

# api/routers/users.py
@router.get("/me")
async def get_me(service: UserDomainService = Depends(get_user_service)):
    return await service.get_current_user()
```

**НЕПРАВИЛЬНО:**
```python
# api/routers/users.py
@router.get("/me")
async def get_me():
    session = AsyncSession(engine)  # ручное создание!
    repo = UserRepository(session)
    service = UserDomainService(repo)  # ручная сборка в роутере!
    return await service.get_current_user()
```

### 9. Error Handling

- [ ] Доменные исключения (например, `TokenExpiredError`, `UserNotFoundError`)
- [ ] Exception handlers в FastAPI для маппинга в HTTP статусы
- [ ] Не утекать внутренними ошибками наружу (стектрейсы, SQL)
- [ ] Каждая ошибка имеет код и сообщение для клиента

**ПРАВИЛЬНО:**
```python
# domain/exceptions.py
class DomainError(Exception):
    pass

class UserNotFoundError(DomainError):
    pass

class TokenExpiredError(DomainError):
    pass

# app/exception_handlers.py
@app.exception_handler(UserNotFoundError)
async def user_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "User not found"})

@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

**НЕПРАВИЛЬНО:**
```python
@router.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(  # HTTP-детали в domain-логике!
            status_code=404,
            detail=f"User {user_id} not found in table users"  # утечка SQL!
        )
```

### 10. Type Safety & Pydantic

- [ ] DTO вместо `dict` в параметрах и возвратах
- [ ] Явные типы возврата в actions (`-> UserResponse`)
- [ ] `validation_alias` для env-переменных
- [ ] Не использовать `Any` без крайней необходимости

**ПРАВИЛЬНО:**
```python
# application/dto/auth.py
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# application/actions/auth/login.py
class LoginAction:
    async def execute(self, data: LoginRequest) -> LoginResponse:
        ...

# app/config.py
class Settings(BaseSettings):
    database_url: str
    secret_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        validation_alias=lambda k: k.upper(),
    )
```

**НЕПРАВИЛЬНО:**
```python
async def login(data: dict) -> dict:  # нет типизации!
    ...

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    # нет validation_alias, нет env_file
```

### 11. Database Patterns

- [ ] Repository pattern (интерфейс в domain, реализация в infrastructure)
- [ ] Коммит в action (unit of work), не в repository
- [ ] AsyncSession через DI, не через глобальную переменную
- [ ] Репозиторий возвращает domain-сущности, не SQLModel-модели
- [ ] ID — только `int` (auto-increment), НЕ UUID

**Правило:** UUID для первичных ключей не использовать. Усложняет поиск, индексы, дебаг.
Исключение — внешние идентификаторы (telegram_id и т.п.).

**ПРАВИЛЬНО:**
```python
# domain/entities/user.py
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True)  # внешний ID — int, не UUID
```

**НЕПРАВИЛЬНО:**
```python
# domain/entities/user.py
class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)  # лишняя сложность!
```

**ПРАВИЛЬНО:**
```python
# domain/repositories/user.py
class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: int) -> User | None: ...
    async def save(self, user: User) -> User: ...

# infrastructure/database/repositories/user.py
class SqlUserRepository(UserRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        obj = await self._session.get(UserModel, user_id)
        return obj.to_domain() if obj else None

# application/actions/user/create.py
class CreateUserAction:
    async def execute(self, data: CreateUserRequest) -> UserResponse:
        user = User(username=data.username)
        saved = await self.repo.save(user)
        await self.session.commit()  # commit в action (unit of work)
        return UserResponse.from_domain(saved)
```

**НЕПРАВИЛЬНО:**
```python
# infrastructure/database/repositories/user.py
class UserRepository:
    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()  # commit в repo — теряет контроль над транзакцией!
        return user

# нет протокола — привязка к конкретной реализации
```

### 12. Service Design

- [ ] Action = один use case (один метод `execute`)
- [ ] Domain service — stateless, бизнес-логика
- [ ] Нет god-классов с 10 методами
- [ ] Сервисы не зависят от HTTP-слоя

**ПРАВИЛЬНО:**
```python
# application/actions/user/create.py
class CreateUserAction:
    def __init__(self, repo: UserRepositoryProtocol, session: AsyncSession):
        self._repo = repo
        self._session = session

    async def execute(self, data: CreateUserRequest) -> UserResponse:
        user = User(username=data.username, email=data.email)
        saved = await self._repo.save(user)
        await self._session.commit()
        return UserResponse.from_domain(saved)

# domain/services/token.py
class TokenDomainService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm

    def create_token(self, user_id: int) -> str:
        payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(hours=24)}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
```

**НЕПРАВИЛЬНО:**
```python
class UserService:
    async def create_user(self, ...): ...
    async def delete_user(self, ...): ...
    async def update_user(self, ...): ...
    async def get_user(self, ...): ...
    async def list_users(self, ...): ...
    async def reset_password(self, ...): ...
    # god-class — слишком много ответственностей!

class AuthAction:
    def execute(self, request: Request):  # зависит от HTTP-слоя!
        token = request.headers.get("Authorization")  # HTTP-детали в domain!
```