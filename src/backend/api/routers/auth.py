"""Auth API router."""
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from application.dto.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from application.actions.auth.login import LoginAction, create_login_action
from application.actions.auth.refresh import RefreshTokenAction, create_refresh_action
from domain.services.token import (
    TokenDomainService,
    TokenInvalidError,
    create_token_service,
)


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@lru_cache
def get_token_service() -> TokenDomainService:
    """Get token service instance."""
    return create_token_service(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


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


def verify_service_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenDomainService:
    """Verify service token for inter-service communication."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token required",
        )

    token_service = get_token_service()
    try:
        return token_service.verify_token(credentials.credentials)
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
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