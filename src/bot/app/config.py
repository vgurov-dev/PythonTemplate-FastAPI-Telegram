import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(default="...", validation_alias="BOT_TOKEN")
    bot_debug: bool = Field(default=False, validation_alias="BOT_DEBUG")

    redis_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )

    bot_database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/botdb",
        validation_alias="BOT_DATABASE_URL",
    )

    backend_url: str = Field(
        default="http://backend:8000",
        validation_alias="BACKEND_URL",
    )

    service_key: str = Field(
        default="service-secret-key",
        validation_alias="SERVICE_KEY",
    )

    service_token: str = Field(default="")
    service_token_expires_at: float = Field(default=0)

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")


def setup_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


settings = Settings()
setup_logging()