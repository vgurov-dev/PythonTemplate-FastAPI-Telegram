"""Sync tasks for bot-backend communication."""
from typing import Optional

import httpx
from celery import Celery
import structlog

from bot.app.config import settings

logger = structlog.get_logger()

celery = Celery(
    "bot",
    broker=settings.redis_url,
)

celery.conf.update(
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery.task(name="sync_telegram_user")
def sync_user_to_backend(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
) -> dict:
    """Sync confirmed user to backend API."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.backend_url}/users/{telegram_id}/telegram",
                json={
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                },
                headers={
                    "Authorization": f"Bearer {settings.service_token}",
                },
            )
            response.raise_for_status()

        logger.info(
            "user_synced_to_backend",
            telegram_id=telegram_id,
            status_code=response.status_code,
        )

        return {"status": "success", "telegram_id": telegram_id}

    except httpx.HTTPError as e:
        logger.error(
            "sync_failed",
            telegram_id=telegram_id,
            error=str(e),
        )
        raise