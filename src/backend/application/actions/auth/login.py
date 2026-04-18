"""Login action - authenticate service and return JWT token."""
from datetime import datetime, timezone

from application.dto.auth import LoginRequest, TokenResponse
from domain.services.token import TokenDomainService, InvalidTokenError


class LoginAction:
    """Action for service login."""

    def __init__(
        self,
        token_service: TokenDomainService,
        service_key: str,
        token_expire_seconds: int,
    ):
        self._token_service = token_service
        self._service_key = service_key
        self._token_expire_seconds = token_expire_seconds

    async def execute(self, request: LoginRequest) -> TokenResponse:
        """Execute login action."""
        if not request.service_key:
            raise ValueError("service_key is required")

        if request.service_key != self._service_key:
            raise InvalidTokenError("Invalid service_key")

        service_name = request.service_name or "bot"
        token = self._token_service.create_token(
            service_name,
            expires_seconds=self._token_expire_seconds,
        )

        payload = self._token_service.verify_token(token)
        exp = datetime.fromtimestamp(payload.exp, tz=timezone.utc)

        return TokenResponse(
            token=token,
            expires_at=exp,
            service=service_name,
        )


def create_login_action(
    token_service: TokenDomainService,
    service_key: str,
    token_expire_seconds: int,
) -> LoginAction:
    """Factory function to create login action."""
    return LoginAction(
        token_service=token_service,
        service_key=service_key,
        token_expire_seconds=token_expire_seconds,
    )