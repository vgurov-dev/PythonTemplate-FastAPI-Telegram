"""Domain service for JWT token management."""
from datetime import datetime, timezone

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as JWTInvalidTokenError
from pydantic import ValidationError

from application.dto.token import TokenPayload
from domain.exceptions import TokenExpiredError, TokenInvalidError


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
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "service": service_name,
            "exp": now + expires_seconds,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def _decode_raw_payload(self, token: str) -> dict:
        """Decode token with full validation."""
        return jwt.decode(
            token,
            self._secret_key,
            algorithms=[self._algorithm],
        )

    def _validate_payload(self, raw_payload: dict) -> TokenPayload:
        """Validate raw payload against schema."""
        return TokenPayload.model_validate(raw_payload)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify JWT token and return validated payload."""
        try:
            raw_payload = self._decode_raw_payload(token)
            return self._validate_payload(raw_payload)
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except (JWTInvalidTokenError, ValidationError):
            raise TokenInvalidError()

    def extract_service_name(self, token: str) -> str:
        """Extract service name from token without full validation."""
        try:
            payload = self.verify_token(token)
            return payload.service
        except (TokenExpiredError, TokenInvalidError):
            raise TokenInvalidError("Invalid token")


def create_token_service(
    secret_key: str,
    algorithm: str = "HS256",
) -> TokenDomainService:
    """Factory function to create token service."""
    return TokenDomainService(secret_key, algorithm)