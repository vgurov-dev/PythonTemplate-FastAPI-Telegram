"""Sync tasks for bot-backend communication."""
import time
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


def get_service_token() -> str:
    """Get or refresh service token."""
    current_time = time.time()

    if (
        settings.service_token
        and current_time < settings.service_token_expires_at - 300
    ):  # refresh 5 minutes before expiry
        return settings.service_token

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.backend_url}/auth/login",
                json={
                    "service_key": settings.service_key,
                    "service_name": "bot",
                },
            )
            response.raise_for_status()
            data = response.json()

        settings.service_token = data["token"]
        settings.service_token_expires_at = data["expires_at"].timestamp()

        logger.info("service_token_refreshed")
        return settings.service_token

    except httpx.HTTPError as e:
        logger.error("token_refresh_failed", error=str(e))
        if settings.service_token:
            return settings.service_token
        raise


@celery.task(name="sync_telegram_user")
def sync_user_to_backend(
    telegram_id: int,
    username: Optional[str],
    first_name: str,
) -> dict:
    """Sync confirmed user to backend API."""
    try:
        token = get_service_token()

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.backend_url}/users/{telegram_id}/telegram",
                json={
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                },
                headers={
                    "Authorization": f"Bearer {token}",
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