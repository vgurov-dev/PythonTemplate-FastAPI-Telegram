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

    app_name: str = Field(default="my-service", validation_alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    app_reload: bool = Field(default=False, validation_alias="APP_RELOAD")
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")

    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/myservice",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    redis_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )
    redis_password: Optional[str] = Field(default=None, validation_alias="REDIS_PASSWORD")

    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", validation_alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", validation_alias="CELERY_RESULT_BACKEND"
    )

    jwt_secret_key: str = Field(
        default="your-secret-key-here", validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    service_key: str = Field(
        default="service-secret-key", validation_alias="SERVICE_KEY"
    )
    service_token_expire_hours: int = Field(
        default=24, validation_alias="SERVICE_TOKEN_EXPIRE_HOURS"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    alembic_config: str = Field(default="alembic.ini", validation_alias="ALEMBIC_CONFIG")


def setup_logging() -> None:
    """Configure structlog."""
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
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


settings = Settings()
setup_logging()