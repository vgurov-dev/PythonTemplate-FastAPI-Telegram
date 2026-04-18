"""Auth API router."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.service_auth import create_service_token, verify_service_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request schema."""

    service_key: Optional[str] = None
    service_name: Optional[str] = "bot"


class RefreshRequest(BaseModel):
    """Refresh token request schema."""

    token: str


class TokenResponse(BaseModel):
    """Token response schema."""

    token: str
    expires_at: datetime
    service: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login endpoint - get JWT token."""
    if not request.service_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_key required",
        )

    if request.service_key != settings.service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service_key",
        )

    service_name = request.service_name or "bot"
    token = create_service_token(
        service_name,
        expires_seconds=settings.service_token_expire_seconds,
    )

    payload = verify_service_token(token)
    exp = datetime.fromtimestamp(payload.get("exp"))

    return TokenResponse(
        token=token,
        expires_at=exp,
        service=service_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    """Refresh endpoint - refresh JWT token."""
    try:
        old_payload = verify_service_token(request.token)
        service_name = old_payload.get("service")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    token = create_service_token(
        service_name,
        expires_seconds=settings.service_token_expire_seconds,
    )

    new_payload = verify_service_token(token)
    exp = datetime.fromtimestamp(new_payload.get("exp"))

    return TokenResponse(
        token=token,
        expires_at=exp,
        service=service_name,
    )