"""
Unit tests for the rules endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.rules import create_rule, process_companies
from app.models.company import Company
from app.models.processed_feature import ProcessedFeature
from app.models.rule import Rule
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleOut


class TestCreateRule:
    """
    Test class for the create_rule endpoint function.

    This class contains unit tests covering various scenarios for rule creation
    including user creation, rule validation, and error handling.
    """

    @pytest.fixture
    def mock_db(self):
        """Mock database session for testing."""
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def sample_rule_payload(self):
        """Sample rule creation payload."""
        return RuleCreate(
            user_name="test_user",
            rules=[
                {
                    "input": "employee_count",
                    "feature_name": "is_large_company",
                    "match": 1,
                    "default": 0,
                    "operation": {
                        "operator": "gt",
                        "target_object": "total_employees",
                        "value": 100,
                    },
                }
            ],
        )

    @pytest.fixture
    def sample_and_rule_payload(self):
        """Sample rule with AND operation."""
        return RuleCreate(
            user_name="test_user",
            rules=[
                {
                    "input": "multi_condition",
                    "feature_name": "is_tech_startup",
                    "match": 1,
                    "default": 0,
                    "operation": {
                        "AND": [
                            {
                                "operator": "eq",
                                "target_object": "industry",
                                "value": "Technology",
                            },
                            {
                                "operator": "lt",
                                "target_object": "founded_year",
                                "value": 2020,
                            },
                        ]
                    },
                }
            ],
        )

    @pytest.fixture
    def existing_user(self):
        """Create a mock existing user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.user_name = "test_user"
        return user

    @pytest.mark.asyncio
    async def test_create_rule_with_new_user(
        self, mock_db, sample_rule_payload
    ):
        """Test creating a rule when user doesn't exist."""
        # Setup: No existing user found
        mock_db.execute.return_value.scalars.return_value.first.side_effect = [
            None,  # User not found
            None,  # Rule not found (for duplicate check)
        ]

        result = await create_rule(payload=sample_rule_payload, db=mock_db)

        assert isinstance(result, RuleOut)
        assert result.success is True
        assert result.message == "Rule created successfully"
        assert result.rule["user_name"] == "test_user"
        assert len(result.rule["rules"]) == 1

        # Verify user was created
        user_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], User)
        ]
        assert len(user_add_calls) == 1

        # Verify rule was created
        rule_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], Rule)
        ]
        assert len(rule_add_calls) == 1

        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rule_with_existing_user(
        self, mock_db, sample_rule_payload, existing_user
    ):
        """Test creating a rule when user already exists."""
        mock_db.execute.return_value.scalars.return_value.first.side_effect = [
            existing_user,  # User found
            None,  # Rule not found (for duplicate check)
        ]

        result = await create_rule(payload=sample_rule_payload, db=mock_db)

        assert isinstance(result, RuleOut)
        assert result.success is True

        # Verify user was NOT created (should not be in add calls)
        user_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], User)
        ]
        assert not user_add_calls

        # Verify rule was created
        rule_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], Rule)
        ]
        assert len(rule_add_calls) == 1

        mock_db.flush.assert_not_called()  # Only called when creating user
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rule_with_and_operation(
        self, mock_db, sample_and_rule_payload, existing_user
    ):
        """Test creating a rule with AND boolean operation."""
        mock_db.execute.return_value.scalars.return_value.first.side_effect = [
            existing_user,  # User found
            None,  # Rule not found (for duplicate check)
        ]

        result = await create_rule(payload=sample_and_rule_payload, db=mock_db)

        assert isinstance(result, RuleOut)
        assert result.success is True
        assert result.rule["rules"][0]["boolean_operator"] == "AND"
        assert len(result.rule["rules"][0]["conditions"]) == 2

        # Verify rule was created with correct boolean operator
        rule_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], Rule)
        ]
        assert len(rule_add_calls) == 1
        created_rule = rule_add_calls[0][0][0]
        assert created_rule.boolean_operator == "AND"

    @pytest.mark.asyncio
    async def test_create_rule_duplicate_skipped(
        self, mock_db, sample_rule_payload, existing_user
    ):
        """Test that duplicate rules are skipped."""
        existing_rule = MagicMock(spec=Rule)
        mock_db.execute.return_value.scalars.return_value.first.side_effect = [
            existing_user,  # User found
            existing_rule,  # Duplicate rule found
        ]

        result = await create_rule(payload=sample_rule_payload, db=mock_db)

        assert isinstance(result, RuleOut)
        assert result.success is True
        assert (
            len(result.rule["rules"]) == 0
        )  # No rules created due to duplicate

        # Verify no rule was added
        rule_add_calls = [
            call
            for call in mock_db.add.call_args_list
            if isinstance(call[0][0], Rule)
        ]
        assert not rule_add_calls

    @pytest.mark.asyncio
    async def test_create_rule_missing_data_error(self, mock_db):
        """Test error handling when required data is missing."""
        # Test missing user_name
        payload_no_user = RuleCreate(user_name="", rules=[{"test": "rule"}])

        with pytest.raises(HTTPException) as exc_info:
            await create_rule(payload=payload_no_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Missing user_name or rules" in str(exc_info.value.detail)

        # Test missing rules
        payload_no_rules = RuleCreate(user_name="test_user", rules=[])

        with pytest.raises(HTTPException) as exc_info:
            await create_rule(payload=payload_no_rules, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Missing user_name or rules" in str(exc_info.value.detail)


class TestProcessCompanies:
    """
    Test class for the process_companies endpoint function.

    This class contains unit tests covering various scenarios for processing
    companies against user rules.
    """

    @pytest.fixture
    def mock_db(self):
        """Mock database session for testing."""
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = MagicMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def sample_user(self):
        """Create a mock user with rules."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.user_name = "test_user"
        return user

    @pytest.fixture
    def sample_company(self):
        """Create a mock company."""
        company = MagicMock(spec=Company)
        company.id = uuid4()
        company.name = "Test Company"
        company.url = "https://testcompany.com"
        company.total_employees = 150
        company.industry = "Technology"
        company.founded_year = 2015
        return company

    @pytest.fixture
    def sample_rule(self, sample_user):
        """Create a mock rule."""
        rule = MagicMock(spec=Rule)
        rule.id = uuid4()
        rule.feature_name = "is_large_company"
        rule.match = 1
        rule.default = 0
        rule.user_id = sample_user.id
        rule.conditions = []
        return rule

    @pytest.fixture
    def sample_payload(self):
        """Sample payload for processing companies."""
        return {
            "user_name": "test_user",
            "urls": ["https://testcompany.com", "https://anothercompany.com"],
        }

    @pytest.mark.asyncio
    async def test_process_companies_success(
        self, mock_db, sample_payload, sample_user, sample_company, sample_rule
    ):
        """Test successful processing of companies."""
        mock_db.execute.return_value.scalars.side_effect = [
            MagicMock(first=MagicMock(return_value=sample_user)),  # User query
            MagicMock(
                all=MagicMock(return_value=[sample_company])
            ),  # Companies query
            MagicMock(
                all=MagicMock(return_value=[sample_rule])
            ),  # Rules query
        ]

        # Mock the rule processor
        with patch(
            "app.api.endpoints.rules.process_rule"
        ) as mock_process_rule:
            mock_process_rule.return_value = True  # Rule matches

            # Execute
            result = await process_companies(
                payload=sample_payload, db=mock_db
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["company"] == "Test Company"
            assert result[0]["is_large_company"] == 1  # Should be match value

            # Verify ProcessedFeature was added
            processed_feature_adds = [
                call
                for call in mock_db.add.call_args_list
                if isinstance(call[0][0], ProcessedFeature)
            ]
            assert len(processed_feature_adds) == 1

            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_companies_rule_no_match(
        self, mock_db, sample_payload, sample_user, sample_company, sample_rule
    ):
        """Test processing when rule doesn't match."""
        mock_db.execute.return_value.scalars.side_effect = [
            MagicMock(first=MagicMock(return_value=sample_user)),  # User query
            MagicMock(
                all=MagicMock(return_value=[sample_company])
            ),  # Companies query
            MagicMock(
                all=MagicMock(return_value=[sample_rule])
            ),  # Rules query
        ]

        with patch(
            "app.api.endpoints.rules.process_rule"
        ) as mock_process_rule:
            mock_process_rule.return_value = False  # Rule doesn't match

            # Execute
            result = await process_companies(
                payload=sample_payload, db=mock_db
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["company"] == "Test Company"
            assert (
                result[0]["is_large_company"] == 0
            )  # Should be default value

    @pytest.mark.asyncio
    async def test_process_companies_user_not_found(
        self, mock_db, sample_payload
    ):
        """Test error when user is not found."""
        # Setup: User not found
        (mock_db
         .execute
         .return_value
         .scalars
         .return_value
         .first
         .return_value) = None

        with pytest.raises(HTTPException) as exc_info:
            await process_companies(payload=sample_payload, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_companies_no_companies_found(
        self, mock_db, sample_payload, sample_user
    ):
        """Test error when no companies are found."""
        # Setup: User found but no companies
        mock_db.execute.return_value.scalars.side_effect = [
            MagicMock(first=MagicMock(return_value=sample_user)),  # User query
            MagicMock(all=MagicMock(return_value=[])),  # No companies found
        ]

        with pytest.raises(HTTPException) as exc_info:
            await process_companies(payload=sample_payload, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "No companies found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_companies_missing_payload_data(self, mock_db):
        """Test error handling for missing payload data."""
        # Test missing user_name
        payload_no_user = {"urls": ["https://test.com"]}

        with pytest.raises(HTTPException) as exc_info:
            await process_companies(payload=payload_no_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Missing user_name or urls" in str(exc_info.value.detail)

        # Test missing urls
        payload_no_urls = {"user_name": "test_user"}

        with pytest.raises(HTTPException) as exc_info:
            await process_companies(payload=payload_no_urls, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Missing user_name or urls" in str(exc_info.value.detail)
