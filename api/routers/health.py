"""Health check router."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"ready": True}