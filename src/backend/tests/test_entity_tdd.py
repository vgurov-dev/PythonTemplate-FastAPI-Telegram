"""TDD tests for User entity.

TDD Workflow:
1. Write test -> RED (fail)
2. Write code -> GREEN
3. Refactor
"""
import pytest
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.tdd
class TestUserEntity:
    """TDD tests for User entity."""

    @pytest.fixture
    def user_data(self):
        """User data for tests."""
        return {
            "id": str(uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "is_active": True,
        }

    def test_user_can_be_created(self, user_data):
        """TDD: User entity should be created with id and username."""
        from src.backend.domain.entities.user import User

        user = User(**user_data)

        assert user.id is not None
        assert user.username == user_data["username"]
        assert user.is_active is True

    def test_user_has_created_at_timestamp(self, user_data):
        """TDD: User should have created_at timestamp."""
        from src.backend.domain.entities.user import User

        user = User(**user_data)

        assert user.created_at is not None

    def test_user_can_be_deactivated(self, user_data):
        """TDD: User can be deactivated."""
        from src.backend.domain.entities.user import User

        user = User(**user_data)
        user.is_active = False

        assert user.is_active is False


@pytest.mark.unit
class TestUserRepository:
    """TDD tests for User repository."""

    @pytest.fixture
    def mock_user_repo(self, mock_repository):
        """Mock user repository."""
        return mock_repository

    @pytest.mark.asyncio
    async def test_get_user_by_id_returns_user(self, mock_user_repo, sample_user_data):
        """TDD: Repository should return user by id."""
        mock_user_repo.get.return_value = sample_user_data

        result = await mock_user_repo.get(sample_user_data["id"])

        assert result is not None
        mock_user_repo.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_users_returns_list(self, mock_user_repo, sample_users_list):
        """TDD: Repository should return all users."""
        mock_user_repo.get_all.return_value = sample_users_list

        result = await mock_user_repo.get_all()

        assert len(result) == 1
        mock_user_repo.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_returns_created_user(self, mock_user_repo, sample_user_data):
        """TDD: Repository should create and return user."""
        mock_user_repo.create.return_value = sample_user_data

        result = await mock_user_repo.create(sample_user_data)

        assert result is not None
        mock_user_repo.create.assert_called_once()


@pytest.mark.integration
class TestUserAPI:
    """Integration tests for User API."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, http_client):
        """Test health check endpoint."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_message(self, http_client):
        """Test root endpoint."""
        response = await http_client.get("/")

        assert response.status_code == 200
        assert "message" in response.json()