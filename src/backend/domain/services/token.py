"""Domain service for JWT token management."""
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as JWTInvalidTokenError


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
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).timestamp()
        payload = {
            "service": service_name,
            "exp": now + expires_seconds,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            service = payload.get("service")
            if not service:
                raise InvalidTokenError()

            return payload

        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTInvalidTokenError:
            raise InvalidTokenError()

    def get_service_name(self, token: str) -> str:
        """Extract service name from token."""
        payload = self.verify_token(token)
        return payload.get("service")


def create_token_service(
    secret_key: str,
    algorithm: str = "HS256",
) -> TokenDomainService:
    """Factory function to create token service."""
    return TokenDomainService(secret_key, algorithm)