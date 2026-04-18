"""Service-to-service authentication with JWT."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


security = HTTPBearer(auto_error=False)


def create_service_token(service_name: str, expires_seconds: int = 86400) -> str:
    """Create JWT token for service."""
    payload = {
        "service": service_name,
        "exp": datetime.now(timezone.utc).timestamp() + expires_seconds,
        "iat": datetime.now(timezone.utc).timestamp(),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_service_token(token: str) -> dict:
    """Verify JWT service token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        exp = payload.get("exp")
        if exp and exp < datetime.now(timezone.utc).timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        service = payload.get("service")
        if not service:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return payload

    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
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

    return verify_service_token(credentials.credentials)