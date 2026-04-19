"""API dependencies."""
from functools import lru_cache
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from bootstrap.config import settings
from bootstrap.database import get_session
from bootstrap.exceptions import UnauthorizedException
from domain.services.token import TokenDomainService, TokenInvalidError, create_token_service
from application.dto.auth import TokenPayloadDTO


security = HTTPBearer(auto_error=False)


@lru_cache
def get_token_service() -> TokenDomainService:
    """Get token service instance."""
    return create_token_service(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_service_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayloadDTO:
    """Verify JWT service token."""
    if not credentials:
        raise UnauthorizedException(detail="Service token required")
    token_service = get_token_service()
    try:
        payload = token_service.verify_token(credentials.credentials)
        return TokenPayloadDTO(
            service=payload.service,
            exp=payload.exp,
            iat=payload.iat,
        )
    except TokenInvalidError:
        raise UnauthorizedException(detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayloadDTO:
    """Get current authenticated user."""
    if not credentials:
        raise UnauthorizedException(detail="Not authenticated")
    token_service = get_token_service()
    try:
        payload = token_service.verify_token(credentials.credentials)
        return TokenPayloadDTO(
            service=payload.service,
            exp=payload.exp,
            iat=payload.iat,
        )
    except TokenInvalidError:
        raise UnauthorizedException(detail="Invalid token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[TokenPayloadDTO, Depends(get_current_user)]