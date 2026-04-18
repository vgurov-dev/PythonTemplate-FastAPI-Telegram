from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.database import init_db
from app.metrics import setup_metrics
from app.tracing import setup_tracing
from api.routers import auth, users

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_starting", app=settings.app_name)
    await init_db()
    setup_tracing()
    yield
    logger.info("application_shutdown", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

setup_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": f"{settings.app_name} is running"}


celery = None


def create_celery() -> None:
    """Create Celery application."""
    global celery
    from celery import Celery

    celery = Celery(
        "my-service",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    celery.conf.update(
        broker_connection_retry_on_startup=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )


create_celery()