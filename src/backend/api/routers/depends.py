"""API router dependencies package."""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from bootstrap.config import settings
from bootstrap.database import get_session
from bootstrap.exceptions import UnauthorizedException
from domain.services.token import (
    TokenDomainService,
    TokenInvalidError,
    create_token_service,
)


security = HTTPBearer(auto_error=False)


@lru_cache
def get_token_service() -> TokenDomainService:
    """Get token service instance."""
    return create_token_service(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user."""
    if not credentials:
        raise UnauthorizedException(detail="Not authenticated")

    token_service = get_token_service()
    try:
        payload = token_service.verify_token(credentials.credentials)
        return {
            "service": payload.service,
            "exp": payload.exp,
            "iat": payload.iat,
        }
    except TokenInvalidError:
        raise UnauthorizedException(detail="Invalid token")


DBSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[dict, Depends(get_current_user)]