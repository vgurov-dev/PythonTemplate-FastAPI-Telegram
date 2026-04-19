---
name: service-communication
description: Inter-service communication patterns - bot to backend HTTP, Celery tasks, auth flows
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers, bot-developers
  workflow: architecture
---

# Service Communication Skill

## Role

Developer working with inter-service communication. This skill covers how services (bot, backend, celery) communicate securely and reliably.

## Principles

### 1. Never bypass the API

- ❌ Bot must NOT access PostgreSQL directly
- ✅ Bot → Backend API → Database
- ❌ Backend must NOT access bot's database
- ✅ Backend → Celery → Bot notification

### 2. Always authenticate

- ✅ Every HTTP call includes service_token or JWT
- ❌ No bare HTTP calls without auth headers

### 3. Prepare for failure

- ✅ Retry with backoff for transient failures
- ❌ No "fire and forget" without monitoring

## How Services Communicate

```
┌─────────┐         HTTP + service_token          ┌───────────┐
│   Bot   │ ─────────────────────────────────────► │  Backend  │
└─────────┘                                        └───────────┘
       │                                                   │
       │ Celery task                                       │ PostgreSQL
       ▼                                                   ▼
┌─────────────┐                                    ┌───────────┐
│   Redis     │                                    │ PostgreSQL │
│  (broker)   │                                    └───────────┘
└─────────────┘
```

### Bot → Backend

Bot communicates with backend ONLY through HTTP REST API:

```python
# bot/services/signup.py
import httpx
from bot.app.config import settings

class SignupService:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.backend_url,
            timeout=10.0,
        )

    async def confirm_signup(self, telegram_id: int, username: str) -> dict:
        """Confirm signup via backend API."""
        response = await self._client.post(
            "/api/auth/confirm-signup",
            json={
                "telegram_id": telegram_id,
                "username": username,
            },
            headers={
                "Authorization": f"Bearer {settings.service_token}",
            },
        )
        response.raise_for_status()
        return response.json()
```

### Backend → Bot (Celery)

Backend sends async tasks to bot via Celery:

```python
# backend/infrastructure/tasks/notify.py
from celery import Celery

celery = Celery("backend")

@celery.task(name="bot.notify_signup")
def notify_signup(telegram_id: int, username: str):
    """Notify bot about confirmed signup."""
    # This task is consumed by celery_worker which shares code with bot
    from bot.tasks.sync import send_welcome_message
    send_welcome_message.delay(telegram_id, username)
```

## Auth Patterns

### Service Token (bot → backend)

```python
# backend/api/routers/depends.py
from fastapi import Depends, HTTPException, Header

async def verify_service_token(
    authorization: str = Header(..., description="Bearer token"),
) -> str:
    """Verify service token for inter-service communication."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]  # Remove "Bearer " prefix
    if token != settings.service_key:
        raise HTTPException(status_code=401, detail="Invalid service token")

    return token


# backend/api/routers/bot_sync.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/bot", tags=["bot"])

@router.post("/confirm-signup")
async def confirm_signup(
    data: SignupConfirmRequest,
    token: str = Depends(verify_service_token),
):
    """Endpoint for bot to confirm user signup."""
    action = ConfirmSignupAction(...)
    return await action.execute(data)
```

### JWT Token (user authentication)

```python
# backend/domain/services/token.py
class TokenDomainService:
    def create_token(self, service_name: str, expires_seconds: int = 86400) -> str:
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "service": service_name,
            "exp": now + expires_seconds,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
```

## HTTP Client Patterns

### Async HTTP with httpx

```python
# bot/services/http_client.py
import httpx
from typing import Optional

class BackendClient:
    """Async HTTP client for backend communication."""

    def __init__(
        self,
        base_url: str,
        service_token: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        self._base_url = base_url
        self._service_token = service_token
        self._timeout = timeout
        self._max_retries = max_retries

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._service_token}",
            "Content-Type": "application/json",
        }

    async def post(self, path: str, json: dict) -> dict:
        """POST with retry and timeout."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    response = await client.post(
                        f"{self._base_url}{path}",
                        json=json,
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == self._max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def get(self, path: str) -> dict:
        """GET with retry and timeout."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    response = await client.get(
                        f"{self._base_url}{path}",
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == self._max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
```

### Circuit Breaker Pattern

```python
# bot/services/circuit_breaker.py
import asyncio
from enum import Enum
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time: Optional[float] = None

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return False
        return (asyncio.get_event_loop().time() - self._last_failure_time) >= self._recovery_timeout

    def _on_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = asyncio.get_event_loop().time()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
```

## Celery Task Patterns

### Task Structure

```python
# backend/infrastructure/tasks/user_tasks.py
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

celery = Celery("backend")

@celery.task(
    bind=True,
    name="backend.sync_user",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_jitter=True,
)
def sync_user_task(self, telegram_id: int, username: str):
    """Sync user from bot to backend."""
    try:
        action = SyncUserAction(...)
        action.execute(telegram_id, username)
    except MaxRetriesExceededError:
        # Log to monitoring, move to dead letter queue
        logger.error("sync_user_failed", telegram_id=telegram_id)
        raise
```

### Async Bridge (Celery → Async Code)

```python
# bot/tasks/sync.py
import asyncio
from celery import Celery

celery = Celery("bot")

@celery.task(name="bot.send_welcome")
def send_welcome_message(telegram_id: int, username: str):
    """Sync task that sends welcome message via bot."""
    # Need to run async code from sync Celery task
    asyncio.run(_send_welcome_async(telegram_id, username))

async def _send_welcome_async(telegram_id: int, username: str):
    """Actually send the welcome message."""
    from bot.main import bot
    from bot.keyboards.main import main_keyboard

    await bot.send_message(
        chat_id=telegram_id,
        text=f"Добро пожаловать, {username}!",
        reply_markup=main_keyboard(),
    )
```

## Error Propagation

### How errors travel between services

```python
# bot/services/http_client.py
class BackendError(Exception):
    """Base exception for backend errors."""
    pass

class BackendServiceUnavailable(BackendError):
    """Backend is unavailable."""
    pass

class BackendUnauthorized(BackendError):
    """Invalid service token."""
    pass

async def call_backend_with_error_mapping(self, path: str, json: dict) -> dict:
    """Map HTTP errors to domain exceptions."""
    try:
        return await self.post(path, json)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise BackendUnauthorized("Invalid service token")
        elif e.response.status_code >= 500:
            raise BackendServiceUnavailable("Backend unavailable")
        else:
            raise BackendError(f"Backend error: {e.response.status_code}")
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| Bot directly to PostgreSQL | Violates network isolation, tight coupling | Use Backend API |
| No retry on HTTP calls | Transient failures break flow | httpx with retry + backoff |
| Fire-and-forget Celery task | No monitoring, lost tasks | Use result backend, monitor |
| Hardcoded service URLs | Inflexible | Use environment variables |
| No timeout on HTTP calls | Hanging forever | Always set timeout |
| Service token in code | Leaked in commits | Use environment variables |
| Direct celery.call() without retry | Lost tasks | autoretry_for, max_retries |
| Sync HTTP in async context | Event loop blocking | Always use httpx.AsyncClient |

## Configuration

```python
# bot/app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    backend_url: str = Field(
        default="http://backend:8000",
        validation_alias="BACKEND_URL",
    )
    service_token: str = Field(
        default="service-secret-key",
        validation_alias="SERVICE_TOKEN",
    )
    http_timeout: float = Field(default=10.0, validation_alias="HTTP_TIMEOUT")
    http_max_retries: int = Field(default=3, validation_alias="HTTP_MAX_RETRIES")
```

## Environment Variables

```bash
# Backend side (.env)
SERVICE_KEY=your-service-secret-key
SERVICE_TOKEN_EXPIRE_SECONDS=86400
BACKEND_URL=http://backend:8000

# Bot side (.env)
BACKEND_URL=http://backend:8000
SERVICE_TOKEN=your-service-secret-key
HTTP_TIMEOUT=10.0
HTTP_MAX_RETRIES=3
```

## Testing

```python
# tests/unit/test_http_client.py
import pytest
from unittest.mock import AsyncMock, patch

from bot.services.http_client import BackendClient, BackendUnauthorized

@pytest.fixture
def client():
    return BackendClient(
        base_url="http://backend:8000",
        service_token="test-token",
    )

@pytest.mark.asyncio
async def test_successful_post(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        result = await client.post("/api/test", {"key": "value"})

        assert result == {"status": "ok"}
        mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_unauthorized_raises_custom_error(client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 401

        error = httpx.HTTPStatusError(
            "Unauthorized",
            request=AsyncMock(),
            response=mock_response,
        )
        mock_client.return_value.__aenter__.return_value.post.side_effect = error

        with pytest.raises(BackendUnauthorized):
            await client.post("/api/test", {"key": "value"})
```

## Checklist

Before implementing inter-service communication:

- [ ] Bot uses BackendClient, not direct HTTP
- [ ] All HTTP calls have timeout
- [ ] Transient failures have retry with backoff
- [ ] Service token is in environment, not code
- [ ] Backend endpoints are protected with verify_service_token
- [ ] Celery tasks have autoretry_for configured
- [ ] Errors are mapped to domain exceptions
- [ ] No direct database access between services
