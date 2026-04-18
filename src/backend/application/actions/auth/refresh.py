"""Refresh token action - refresh JWT token."""
from datetime import datetime, timezone

from application.dto.auth import RefreshRequest, TokenResponse
from domain.services.token import (
    TokenDomainService,
    InvalidTokenError,
    TokenExpiredError,
)


class RefreshTokenAction:
    """Action for refreshing JWT token."""

    def __init__(
        self,
        token_service: TokenDomainService,
        token_expire_seconds: int,
    ):
        self._token_service = token_service
        self._token_expire_seconds = token_expire_seconds

    async def execute(self, request: RefreshRequest) -> TokenResponse:
        """Execute refresh token action."""
        try:
            old_payload = self._token_service.verify_token(request.token)
            service_name = old_payload.service
        except (InvalidTokenError, TokenExpiredError):
            raise InvalidTokenError("Invalid or expired token")

        token = self._token_service.create_token(
            service_name,
            expires_seconds=self._token_expire_seconds,
        )

        new_payload = self._token_service.verify_token(token)
        exp = datetime.fromtimestamp(new_payload.exp, tz=timezone.utc)

        return TokenResponse(
            token=token,
            expires_at=exp,
            service=service_name,
        )


def create_refresh_action(
    token_service: TokenDomainService,
    token_expire_seconds: int,
) -> RefreshTokenAction:
    """Factory function to create refresh action."""
    return RefreshTokenAction(
        token_service=token_service,
        token_expire_seconds=token_expire_seconds,
    )