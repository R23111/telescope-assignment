"""
Unit tests for the users endpoint.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.users import create_user
from app.models.user import User
from app.schemas.user import UserCreate


class TestCreateUser:
    """
    Test class for the create_user endpoint function.

    This class contains unit tests covering various scenarios for user creation
    including new user creation, existing user handling, and error scenarios.
    """

    @pytest.fixture
    def mock_db(self):
        """Mock database session for testing."""
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def sample_user_data(self):
        """Sample user creation data."""
        return UserCreate(user_name="test_user")

    @pytest.fixture
    def existing_user(self):
        """Create a mock existing user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.user_name = "test_user"
        return user

    @pytest.mark.asyncio
    async def test_create_user_new_user_success(
        self, mock_db, sample_user_data
    ):
        """Test creating a new user when user doesn't exist."""
        (mock_db
         .execute
         .return_value
         .scalars
         .return_value
         .first
         .return_value) = None

        new_user_mock = MagicMock(spec=User)
        new_user_mock.id = uuid4()
        new_user_mock.user_name = "test_user"
        mock_db.refresh.side_effect = lambda user: setattr(
            user, "id", new_user_mock.id
        )

        result = await create_user(user_data=sample_user_data, db=mock_db)

        assert result is not None

        mock_db.execute.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        added_user = mock_db.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.user_name == "test_user"

    @pytest.mark.asyncio
    async def test_create_user_existing_user_returned(
        self, mock_db, sample_user_data, existing_user
    ):
        """Test returning existing user when user already exists."""
        (mock_db
         .execute
         .return_value
         .scalars
         .return_value
         .first
         .return_value) = existing_user

        result = await create_user(user_data=sample_user_data, db=mock_db)

        assert result == existing_user
        assert result.user_name == "test_user"

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_different_usernames(self, mock_db):
        """Test creating users with different usernames."""
        (mock_db
         .execute
         .return_value
         .scalars
         .return_value
         .first
         .return_value) = None

        user_data = UserCreate(user_name="different_user")

        result = await create_user(user_data=user_data, db=mock_db)

        assert result is not None

        added_user = mock_db.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.user_name == "different_user"

        mock_db.execute.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_database_commit_error(
        self, mock_db, sample_user_data
    ):
        """Test handling of database commit errors."""
        (mock_db
         .execute
         .return_value
         .scalars
         .return_value
         .first
         .return_value) = None
        mock_db.commit.side_effect = Exception("Database commit failed")

        with pytest.raises(Exception) as exc_info:
            await create_user(user_data=sample_user_data, db=mock_db)

        assert "Database commit failed" in str(exc_info.value)

        mock_db.execute.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_database_query_error(
        self, mock_db, sample_user_data
    ):
        """Test handling of database query errors."""
        mock_db.execute.side_effect = Exception("Database query failed")

        with pytest.raises(Exception) as exc_info:
            await create_user(user_data=sample_user_data, db=mock_db)

        assert "Database query failed" in str(exc_info.value)

        mock_db.execute.assert_called_once()
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()
