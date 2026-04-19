---
name: celery-tasks
description: Celery tasks - async tasks, retry policies, beat scheduling, error handling, monitoring
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers, bot-developers
  workflow: backend
---

# Celery Tasks Skill

## Role

Developer working with Celery for asynchronous task processing. Covers task structure, retry policies, beat scheduling, and monitoring.

## Project Structure

```
src/backend/infrastructure/tasks/
├── __init__.py           # Celery app instance
├── user_tasks.py         # User-related tasks
├── notify_tasks.py        # Notification tasks
└── periodic_tasks.py     # Beat schedule definitions
```

## Celery Setup

### Basic Celery Configuration

```python
# backend/bootstrap/main.py (part of it)
from celery import Celery

def create_celery() -> Celery:
    """Create Celery application."""
    celery = Celery(
        "my-service",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    celery.conf.update(
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=10,

        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        task_track_started=True,
        task_time_limit=300,  # 5 minutes hard limit
        task_soft_time_limit=240,  # 4 minutes soft limit

        worker_prefetch_multiplier=4,
        worker_concurrency=4,
    )

    return celery

celery = create_celery()
```

### Docker Compose Configuration

```yaml
# docker-compose.yml (dev)
services:
  celery_worker:
    build:
      context: .
      dockerfile: src/backend/Dockerfile
    env_file:
      - .env
    depends_on:
      - redis
      - postgres
    volumes:
      - ./src/backend:/app
    command: poetry run celery -A app.main.celery worker --loglevel=info

  celery_beat:
    build:
      context: .
      dockerfile: src/backend/Dockerfile
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - ./src/backend:/app
    command: poetry run celery -A app.main.celery beat --loglevel=info
```

```yaml
# docker-compose.staging.yml (prod)
services:
  celery_worker:
    image: ghcr.io/org/backend:${TAG:-latest}
    restart: unless-stopped
    env_file:
      - .env
    command: celery -A app.main.celery worker --loglevel=info --concurrency=8
    networks:
      - app-network

  celery_beat:
    image: ghcr.io/org/backend:${TAG:-latest}
    restart: unless-stopped
    env_file:
      - .env
    command: celery -A app.main.celery beat --loglevel=info
    networks:
      - app-network
```

## Task Structure

### Basic Task

```python
# backend/infrastructure/tasks/notify_tasks.py
from celery import Celery
import structlog

logger = structlog.get_logger()

celery = Celery("backend")


@celery.task(name="backend.notify_signup")
def notify_signup(telegram_id: int, username: str) -> dict:
    """
    Notify user about successful signup.

    Args:
        telegram_id: Telegram user ID
        username: Username

    Returns:
        Dict with notification status
    """
    logger.info("notify_signup_started", telegram_id=telegram_id)

    # Import here to avoid circular imports
    from bot.tasks.sync import send_welcome_message

    send_welcome_message.delay(telegram_id, username)

    return {
        "status": "sent",
        "telegram_id": telegram_id,
    }
```

### Task with bind and retry

```python
# backend/infrastructure/tasks/user_tasks.py
from celery import Celery
from celery.exceptions import MaxRetriesExceededError
from celery.states import FAILURE, SUCCESS

from bot.app.config import settings

logger = structlog.get_logger()


@celery.task(
    bind=True,
    name="backend.sync_user",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    track_started=True,
)
def sync_user(self, telegram_id: int, username: str, email: str | None = None) -> dict:
    """
    Sync user from bot to backend database.

    Uses exponential backoff for retries.
    """
    logger.info(
        "sync_user_started",
        telegram_id=telegram_id,
        attempt=self.request.retries,
    )

    try:
        # Import here to avoid circular imports
        from application.actions.user.sync import SyncUserAction
        from infrastructure.database.repositories.user import UserRepository
        from bootstrap.database import async_session_factory

        async def _sync():
            async with async_session_factory() as session:
                repo = UserRepository(session)
                action = SyncUserAction(repo, session)
                await action.execute(
                    telegram_id=telegram_id,
                    username=username,
                    email=email,
                )

        import asyncio
        asyncio.run(_sync())

        logger.info("sync_user_completed", telegram_id=telegram_id)
        return {"status": "synced", "telegram_id": telegram_id}

    except (ConnectionError, TimeoutError) as exc:
        logger.warning(
            "sync_user_retry",
            telegram_id=telegram_id,
            attempt=self.request.retries,
            error=str(exc),
        )
        raise self.retry(exc=exc)

    except MaxRetriesExceededError:
        logger.error(
            "sync_user_failed",
            telegram_id=telegram_id,
        )
        # Move to dead letter queue or alert
        return {"status": "failed", "telegram_id": telegram_id}
```

## Retry Policies

### Exponential Backoff

```python
@celery.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,  # First retry after 1 minute
    retry_backoff=True,     # Exponential backoff
    retry_backoff_max=3600, # Max 1 hour between retries
    retry_jitter=True,       # Add random jitter to prevent thundering herd
)
def task_with_exponential_backoff(self):
    """Retry with exponential backoff: 1m, 2m, 4m, 8m, 16m (+ jitter)"""
    pass
```

### Custom Retry Delay

```python
@celery.task(bind=True)
def task_with_custom_delay(self):
    """Custom retry with specific delays."""
    if self.request.retries == 0:
        delay = 30  # 30 seconds
    elif self.request.retries == 1:
        delay = 120  # 2 minutes
    else:
        delay = 600  # 10 minutes

    raise self.retry(countdown=delay)
```

### Retry on Specific Exceptions

```python
from requests.exceptions import RequestException

@celery.task(
    bind=True,
    autoretry_for=(RequestException, ConnectionError),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
)
def task_with_specific_exceptions(self):
    """Only retry on network-related errors."""
    response = requests.get("http://external-api.com/data")
    response.raise_for_status()
    return response.json()
```

## Periodic Tasks (Beat)

### Beat Schedule Configuration

```python
# backend/infrastructure/tasks/periodic_tasks.py
from celery.schedules import crontab

# Beat schedule definition
beat_schedule = {
    "cleanup-expired-sessions": {
        "task": "backend.cleanup_expired_sessions",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "send-daily-digest": {
        "task": "backend.send_daily_digest",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
    },
    "sync-user-stats": {
        "task": "backend.sync_user_stats",
        "schedule": 3600.0,  # Every hour
    },
    "retry-failed-tasks": {
        "task": "backend.retry_failed_tasks",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
}
```

### Periodic Task Implementation

```python
# backend/infrastructure/tasks/maintenance_tasks.py
from celery import Celery
from celery.states import FAILURE
import structlog

logger = structlog.get_logger()


@celery.task(name="backend.cleanup_expired_sessions")
def cleanup_expired_sessions() -> dict:
    """Clean up expired user sessions daily."""
    logger.info("cleanup_expired_sessions_started")

    from infrastructure.cache.redis import redis_client

    # Find and delete expired sessions
    keys = redis_client.scan_iter("session:*:expires")
    deleted = 0
    for key in keys:
        if redis_client.get(key) == "expired":
            redis_client.delete(key)
            deleted += 1

    logger.info("cleanup_expired_sessions_completed", deleted=deleted)
    return {"deleted": deleted}


@celery.task(name="backend.send_daily_digest")
def send_daily_digest() -> dict:
    """Send daily digest to active users."""
    logger.info("send_daily_digest_started")

    # Implementation here
    sent = 0
    # ...

    logger.info("send_daily_digest_completed", sent=sent)
    return {"sent": sent}
```

## Error Handling

### Task Error Handler

```python
# backend/infrastructure/tasks/error_handlers.py
from celery import Celery
from celery.signals import task_failure, worker_ready
import structlog

logger = structlog.get_logger()

celery = Celery("backend")


@celery.task
def on_task_failure(request, exc, traceback, **kwargs):
    """Handle task failure."""
    logger.error(
        "celery_task_failed",
        task_name=request.name,
        task_id=request.id,
        exception=str(exc),
        traceback=str(traceback),
        retries=request.retries,
    )

    # Here you could:
    # - Send alert to monitoring
    # - Move to dead letter queue
    # - Create issue in tracker


@celery.task
def on_task_retry(request, exc, traceback, **kwargs):
    """Handle task retry."""
    logger.warning(
        "celery_task_retry",
        task_name=request.name,
        task_id=request.id,
        exception=str(exc),
        attempt=request.retries,
    )


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Worker is ready."""
    logger.info("celery_worker_ready")
```

### Dead Letter Queue Pattern

```python
# backend/infrastructure/tasks/dead_letter.py
from celery import Celery
from celery.states import FAILURE, PENDING, SUCCESS

celery = Celery("backend")


@celery.task(
    name="backend.dead_letter_handler",
    ignore_result=True,
)
def dead_letter_handler(task_name: str, task_id: str, error: str):
    """Handle failed tasks that exceeded max retries."""
    logger.error(
        "dead_letter_task",
        original_task=task_name,
        task_id=task_id,
        error=error,
    )

    # Alert monitoring
    # Create ticket
    # Store for manual retry


@celery.task(bind=True, max_retries=3)
def task_with_dead_letter(self, data: dict):
    """Task that sends to dead letter on final failure."""
    try:
        process_data(data)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            dead_letter_handler.delay(
                task_name=self.name,
                task_id=self.request.id,
                error=str(exc),
            )
            logger.error("task_sent_to_dlq", task_name=self.name)
        raise
```

## Monitoring

### Flower (Celery Monitor)

```yaml
# docker-compose.yml
services:
  flower:
    build:
      context: .
      dockerfile: src/backend/Dockerfile
    ports:
      - "5555:5555"
    env_file:
      - .env
    command: poetry run celery -A app.main.celery flower
    depends_on:
      - redis
```

### Inspect Commands

```bash
# List active tasks
docker compose exec celery_worker celery -A app.main.celery inspect active

# List registered tasks
docker compose exec celery_worker celery -A app.main.celery inspect registered

# Show statistics
docker compose exec celery_worker celery -A app.main.celery inspect stats

# Revoke task
docker compose exec celery_worker celery -A app.main.celery revoke <task_id>

# Purge all tasks
docker compose exec celery_worker celery -A app.main.celery purge
```

### Logging Configuration

```python
# backend/bootstrap/config.py
import structlog

def setup_celery_logging():
    """Configure structured logging for Celery."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

## Async Bridge (Celery → Async)

```python
# bot/tasks/sync.py
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
            # Create new loop if current is running
            return asyncio.run(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(coro)


@celery.task(name="bot.send_welcome", bind=True, max_retries=3)
def send_welcome_message(self, telegram_id: int, username: str):
    """Send welcome message to new user."""
    logger.info("send_welcome_started", telegram_id=telegram_id)

    async def _send():
        from bot.main import bot
        from bot.keyboards.main import main_keyboard

        await bot.send_message(
            chat_id=telegram_id,
            text=f"Добро пожаловать, {username}! 👋",
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

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| No retry policy | Lost tasks on failure | Configure max_retries + autoretry_for |
| time.sleep() in task | Blocks worker | Use retry with countdown |
| Global state in task | Race conditions | Pass all data as arguments |
| Sync HTTP in task | Blocks event loop | Use async HTTP client or run in thread |
| No task timeout | Zombie tasks | Set time_limit and soft_time_limit |
| Don't track results | No visibility | Configure result_backend |
| Heavy computation in task | Worker starvation | Use worker_pool='prefork' + asyncio.to_thread |
| No monitoring | Silent failures | Add logging + error handler |

## Testing Tasks

```python
# backend/tests/unit/test_tasks.py
import pytest
from unittest.mock import patch, MagicMock
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

from infrastructure.tasks.user_tasks import sync_user


class MockTaskRequest:
    retries = 0
    id = "test-task-id"


@pytest.fixture
def celery_config():
    """Configure Celery for testing."""
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,  # Execute tasks synchronously
        "task_eager_propagates": True,
    }


@pytest.mark.unit
class TestSyncUserTask:
    """Tests for sync_user task."""

    @pytest.fixture
    def mock_action(self):
        with patch("infrastructure.tasks.user_tasks.SyncUserAction") as mock:
            yield mock

    def test_sync_user_success(self, mock_action):
        """Test successful user sync."""
        mock_action.return_value.execute = MagicMock()

        result = sync_user(
            telegram_id=123,
            username="testuser",
            email="test@example.com",
        )

        assert result["status"] == "synced"
        assert result["telegram_id"] == 123
        mock_action.return_value.execute.assert_called_once()

    def test_sync_user_retry_on_connection_error(self, mock_action):
        """Test task retries on connection error."""
        mock_action.side_effect = ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            sync_user(telegram_id=123, username="testuser")

        assert mock_action.call_count == 1  # First attempt
```

## Checklist

Before deploying Celery tasks:

- [ ] Tasks have max_retries configured
- [ ] autoretry_for set for expected exceptions
- [ ] retry_backoff enabled for exponential backoff
- [ ] time_limit and soft_time_limit set
- [ ] Tasks log start/complete/failure
- [ ] Dead letter handler for failed tasks
- [ ] Beat schedule documented
- [ ] Monitoring (Flower or celery inspect) available
- [ ] Result backend configured
- [ ] Worker concurrency appropriate for task types
