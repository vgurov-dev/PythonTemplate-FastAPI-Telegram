"""Domain service for JWT token management."""
from datetime import datetime, timezone

import jwt
from jwt.exceptions import ExpiredSignatureError, JWTInvalidTokenError
from pydantic import ValidationError

from application.dto.token import TokenPayload


class TokenExpiredError(Exception):
    """Raised when token is expired."""
    pass


class InvalidTokenError(Exception):
    """Raised when token is invalid."""
    pass


class TokenDomainService:
    """Domain service for creating and verifying JWT tokens."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm

    def create_token(
        self,
        service_name: str,
        expires_seconds: int = 86400,
    ) -> str:
        """Create JWT token for service."""
        now = datetime.now(timezone.utc).timestamp()
        payload = {
            "service": service_name,
            "exp": now + expires_seconds,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify JWT token and return validated payload."""
        try:
            raw_payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return TokenPayload.model_validate(raw_payload)

        except ExpiredSignatureError:
            raise TokenExpiredError()
        except (JWTInvalidTokenError, ValidationError):
            raise InvalidTokenError()

    def get_service_name(self, token: str) -> str:
        """Extract service name from token."""
        payload = self.verify_token(token)
        return payload.service


def create_token_service(
    secret_key: str,
    algorithm: str = "HS256",
) -> TokenDomainService:
    """Factory function to create token service."""
    return TokenDomainService(secret_key, algorithm)