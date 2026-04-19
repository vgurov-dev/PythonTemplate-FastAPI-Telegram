"""Auth API router."""
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bootstrap.config import settings
from application.dto.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from application.actions.auth.login import LoginAction, create_login_action
from application.actions.auth.refresh import RefreshTokenAction, create_refresh_action
from domain.exceptions import TokenInvalidError
from api.dependencies import get_token_service


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_login_action() -> LoginAction:
    """Get login action instance."""
    token_service = get_token_service()
    return create_login_action(
        token_service=token_service,
        service_key=settings.service_key,
        token_expire_seconds=settings.service_token_expire_seconds,
    )


def get_refresh_action() -> RefreshTokenAction:
    """Get refresh action instance."""
    token_service = get_token_service()
    return create_refresh_action(
        token_service=token_service,
        token_expire_seconds=settings.service_token_expire_seconds,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    action: LoginAction = Depends(get_login_action),
) -> TokenResponse:
    """Login endpoint - get JWT token."""
    try:
        return await action.execute(request)
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service_key",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    action: RefreshTokenAction = Depends(get_refresh_action),
) -> TokenResponse:
    """Refresh endpoint - refresh JWT token."""
    try:
        return await action.execute(request)
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )