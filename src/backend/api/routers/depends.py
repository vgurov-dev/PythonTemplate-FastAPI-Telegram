"""API router dependencies package."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError as JWTInvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user."""
    from app.exceptions import UnauthorizedException

    if not credentials:
        raise UnauthorizedException(detail="Not authenticated")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTInvalidTokenError:
        raise UnauthorizedException(detail="Invalid token")


DBSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[dict, Depends(get_current_user)]