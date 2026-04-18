"""Auth API router."""
from fastapi import APIRouter, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from application.dto.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from application.actions.auth.login import create_login_action
from application.actions.auth.refresh import create_refresh_action
from domain.services.token import (
    create_token_service,
    InvalidTokenError,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

token_service = create_token_service(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
)

login_action = create_login_action(
    token_service=token_service,
    service_key=settings.service_key,
    token_expire_seconds=settings.service_token_expire_seconds,
)

refresh_action = create_refresh_action(
    token_service=token_service,
    token_expire_seconds=settings.service_token_expire_seconds,
)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login endpoint - get JWT token."""
    try:
        return await login_action.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service_key",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    """Refresh endpoint - refresh JWT token."""
    try:
        return await refresh_action.execute(request)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def verify_service(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify service token for inter-service communication."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token required",
        )

    try:
        return token_service.verify_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )