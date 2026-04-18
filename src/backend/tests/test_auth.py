"""Tests for TokenDomainService and auth actions."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestTokenDomainService:
    """Unit tests for TokenDomainService."""

    @pytest.fixture
    def token_service(self):
        """Create token service for tests."""
        from domain.services.token import create_token_service
        return create_token_service(secret_key="test-secret", algorithm="HS256")

    def test_create_token_returns_string(self, token_service):
        """TDD: create_token should return JWT string."""
        token = token_service.create_token(service_name="test-service")

        assert isinstance(token, str)
        assert token.split(".").__len__() == 3

    def test_create_token_with_expiration(self, token_service):
        """TDD: create_token should accept expires_seconds."""
        expires_in = 3600
        token = token_service.create_token(
            service_name="test-service",
            expires_seconds=expires_in,
        )

        assert token is not None

    def test_verify_valid_token_returns_payload(self, token_service):
        """TDD: verify_token should return TokenPayload for valid token."""
        token = token_service.create_token(
            service_name="test-service",
            expires_seconds=3600,
        )

        payload = token_service.verify_token(token)

        assert payload.service == "test-service"
        assert payload.exp is not None
        assert payload.iat is not None

    def test_verify_invalid_token_raises_error(self, token_service):
        """TDD: verify_token should raise TokenInvalidError for invalid token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(Exception):
            token_service.verify_token(invalid_token)

    def test_verify_expired_token_raises_error(self, token_service):
        """TDD: verify_token should raise TokenExpiredError for expired token."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        exp_timestamp = int(expired_time.timestamp())
        iat_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())

        import jwt
        expired_token = jwt.encode(
            {"service": "test", "exp": exp_timestamp, "iat": iat_timestamp},
            "test-secret",
            algorithm="HS256",
        )

        with pytest.raises(Exception):
            token_service.verify_token(expired_token)

    def test_extract_service_name(self, token_service):
        """TDD: extract_service_name should return service name from token."""
        token = token_service.create_token(service_name="my-service")

        service_name = token_service.extract_service_name(token)

        assert service_name == "my-service"


@pytest.mark.unit
class TestLoginAction:
    """Unit tests for LoginAction."""

    @pytest.fixture
    def token_service(self):
        """Create mock token service."""
        from domain.services.token import create_token_service
        return create_token_service(secret_key="test-secret", algorithm="HS256")

    @pytest.fixture
    def login_action(self, token_service):
        """Create login action for tests."""
        from application.actions.auth.login import create_login_action
        return create_login_action(
            token_service=token_service,
            service_key="valid-key",
            token_expire_seconds=3600,
        )

    @pytest.mark.asyncio
    async def test_login_with_valid_key_returns_token(self, login_action):
        """TDD: login should return token with valid service_key."""
        from application.dto.auth import LoginRequest

        request = LoginRequest(service_key="valid-key", service_name="bot")
        response = await login_action.execute(request)

        assert response.token is not None
        assert response.service == "bot"
        assert response.expires_at is not None

    @pytest.mark.asyncio
    async def test_login_with_invalid_key_raises_error(self, login_action):
        """TDD: login should raise TokenInvalidError with invalid service_key."""
        from application.dto.auth import LoginRequest
        from domain.services.token import TokenInvalidError

        request = LoginRequest(service_key="wrong-key", service_name="bot")

        with pytest.raises(TokenInvalidError):
            await login_action.execute(request)

    @pytest.mark.asyncio
    async def test_login_uses_default_service_name(self, login_action, token_service):
        """TDD: login should use default service_name 'bot'."""
        from application.dto.auth import LoginRequest

        request = LoginRequest(service_key="valid-key")
        response = await login_action.execute(request)

        assert response.service == "bot"


@pytest.mark.unit
class TestRefreshTokenAction:
    """Unit tests for RefreshTokenAction."""

    @pytest.fixture
    def token_service(self):
        """Create token service for tests."""
        from domain.services.token import create_token_service
        return create_token_service(secret_key="test-secret", algorithm="HS256")

    @pytest.fixture
    def refresh_action(self, token_service):
        """Create refresh action for tests."""
        from application.actions.auth.refresh import create_refresh_action
        return create_refresh_action(
            token_service=token_service,
            token_expire_seconds=3600,
        )

    @pytest.mark.asyncio
    async def test_refresh_with_valid_token_returns_new_token(self, refresh_action, token_service):
        """TDD: refresh should return new token for valid old token."""
        from application.dto.auth import RefreshRequest

        old_token = token_service.create_token(service_name="test-service")
        request = RefreshRequest(token=old_token)
        response = await refresh_action.execute(request)

        assert response.token is not None
        assert response.token != old_token
        assert response.service == "test-service"

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_raises_error(self, refresh_action):
        """TDD: refresh should raise error for invalid token."""
        from application.dto.auth import RefreshRequest
        from domain.services.token import TokenInvalidError

        request = RefreshRequest(token="invalid.token")

        with pytest.raises(TokenInvalidError):
            await refresh_action.execute(request)


@pytest.mark.integration
class TestAuthAPI:
    """Integration tests for Auth API."""

    @pytest.fixture
    def valid_service_key(self):
        """Get valid service key from settings."""
        from app.config import settings
        return settings.service_key

    @pytest.mark.asyncio
    async def test_login_endpoint_returns_token(self, client, valid_service_key):
        """Test /auth/login endpoint returns token."""
        response = await client.post(
            "/auth/login",
            json={"service_key": valid_service_key, "service_name": "test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert data["service"] == "test"

    @pytest.mark.asyncio
    async def test_login_endpoint_with_invalid_key_returns_401(self, client):
        """Test /auth/login endpoint returns 401 for invalid key."""
        response = await client.post(
            "/auth/login",
            json={"service_key": "wrong-key", "service_name": "test"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_invalid_token_returns_401(self, client):
        """Test /auth/refresh endpoint returns 401 for invalid token."""
        response = await client.post(
            "/auth/refresh",
            json={"token": "invalid.token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_endpoint_returns_new_token(self, client, valid_service_key):
        """Test /auth/refresh endpoint returns new token."""
        import asyncio

        login_response = await client.post(
            "/auth/login",
            json={"service_key": valid_service_key, "service_name": "test"},
        )
        token = login_response.json()["token"]

        await asyncio.sleep(1.1)

        refresh_response = await client.post(
            "/auth/refresh",
            json={"token": token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "token" in data
        assert data["token"] != token
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_invalid_token_returns_401(self, client):
        """Test /auth/refresh endpoint returns 401 for invalid token."""
        response = await client.post(
            "/auth/refresh",
            json={"token": "invalid.token"},
        )

        assert response.status_code == 401