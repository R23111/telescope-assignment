"""
Unit tests for the rule_processor service.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.company import Company
from app.models.rule import Condition, Rule
from app.services.rule_processor import (
    evaluate_condition,
    process_llm,
    process_rule,
)


class TestProcessLLM:
    """
    Test class for the process_llm function.

    This class contains unit tests covering LLM API integration scenarios
    including successful responses, API errors, and various response formats.
    """

    @pytest.fixture
    def mock_httpx_response(self):
        """Create a mock httpx response."""
        response = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"text": "true"}}]
        }
        return response

    @pytest.mark.asyncio
    async def test_process_llm_returns_true(self, mock_httpx_response):
        """Test process_llm returns True for 'true' response."""
        mock_httpx_response.json.return_value = {
            "choices": [{"message": {"text": "true"}}]
        }

        with patch("httpx.post", return_value=mock_httpx_response):
            result = await process_llm(
                "Is this a tech company?", "Industry: Technology"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_process_llm_returns_false(self, mock_httpx_response):
        """Test process_llm returns False for 'false' response."""
        mock_httpx_response.json.return_value = {
            "choices": [{"message": {"text": "false"}}]
        }

        with patch("httpx.post", return_value=mock_httpx_response):
            result = await process_llm(
                "Is this a retail company?", "Industry: Technology"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_process_llm_case_insensitive(self, mock_httpx_response):
        """Test process_llm handles case-insensitive responses."""
        mock_httpx_response.json.return_value = {
            "choices": [{"message": {"text": "TRUE"}}]
        }

        with patch("httpx.post", return_value=mock_httpx_response):
            result = await process_llm("Test question", "Test context")

            assert result is True

    @pytest.mark.asyncio
    async def test_process_llm_with_whitespace(self, mock_httpx_response):
        """Test process_llm handles responses with whitespace."""
        mock_httpx_response.json.return_value = {
            "choices": [{"message": {"text": "  true  "}}]
        }

        with patch("httpx.post", return_value=mock_httpx_response):
            result = await process_llm("Test question", "Test context")

            assert result is True

    @pytest.mark.asyncio
    async def test_process_llm_malformed_response(self, mock_httpx_response):
        """Test process_llm handles malformed API responses."""
        mock_httpx_response.json.return_value = {"choices": []}

        with patch("httpx.post", return_value=mock_httpx_response):
            result = await process_llm("Test question", "Test context")

            assert result is False


class TestEvaluateCondition:
    """
    Test class for the evaluate_condition function.

    This class contains unit tests covering all supported condition operators
    and various value types and edge cases.
    """

    @pytest.fixture
    def sample_condition(self):
        """Create a sample condition for testing."""
        condition = MagicMock(spec=Condition)
        condition.operator = "EQUALS"
        condition.value = "100"
        condition.target_object = "total_employees"
        return condition

    @pytest.mark.asyncio
    async def test_evaluate_condition_equals_true(self, sample_condition):
        """Test EQUALS operator returns True for matching values."""
        sample_condition.operator = "EQUALS"
        sample_condition.value = "Technology"

        result = await evaluate_condition(sample_condition, "Technology")

        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_condition_equals_false(self, sample_condition):
        """Test EQUALS operator returns False for non-matching values."""
        sample_condition.operator = "EQUALS"
        sample_condition.value = "Technology"

        result = await evaluate_condition(sample_condition, "Retail")

        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_condition_greater_than(self, sample_condition):
        """Test GREATER_THAN operator with numeric values."""
        sample_condition.operator = "GREATER_THAN"
        sample_condition.value = "100"

        result = await evaluate_condition(sample_condition, 150)

        assert result is True

        result = await evaluate_condition(sample_condition, 50)

        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_condition_contains(self, sample_condition):
        """Test CONTAINS operator works correctly."""
        sample_condition.operator = "CONTAINS"
        sample_condition.value = "Tech"

        result = await evaluate_condition(
            sample_condition, "Technology Company"
        )

        assert result is True

        result = await evaluate_condition(sample_condition, "Finance Company")

        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_condition_llm(self, sample_condition):
        """Test LLM operator calls process_llm function."""
        sample_condition.operator = "LLM"
        sample_condition.value = "Is this a tech company?"
        sample_condition.target_object = "industry"

        with patch(
            "app.services.rule_processor.process_llm"
        ) as mock_process_llm:
            mock_process_llm.return_value = True

            result = await evaluate_condition(sample_condition, "Technology")

            assert result is True
            mock_process_llm.assert_called_once_with(
                "Is this a tech company?", "industry: Technology"
            )


class TestProcessRule:
    """
    Test class for the process_rule function.

    This class contains unit tests covering rule processing with single
    conditions, multiple conditions with AND/OR operators, and error handling.
    """

    @pytest.fixture
    def sample_company(self):
        """Create a sample company for testing."""
        company = MagicMock(spec=Company)
        company.name = "TechCorp Inc"
        company.total_employees = 150
        company.industry = "Technology"
        company.founded_year = 2015
        company.headquarters_city = "San Francisco"
        return company

    @pytest.fixture
    def single_condition_rule(self):
        """Create a rule with a single condition."""
        rule = MagicMock(spec=Rule)
        rule.boolean_operator = None

        condition = MagicMock(spec=Condition)
        condition.operator = "GREATER_THAN"
        condition.target_object = "total_employees"
        condition.value = "100"

        rule.conditions = [condition]
        return rule

    @pytest.fixture
    def and_rule(self):
        """Create a rule with AND boolean operator."""
        rule = MagicMock(spec=Rule)
        rule.boolean_operator = "AND"

        condition1 = MagicMock(spec=Condition)
        condition1.operator = "EQUALS"
        condition1.target_object = "industry"
        condition1.value = "Technology"

        condition2 = MagicMock(spec=Condition)
        condition2.operator = "GREATER_THAN"
        condition2.target_object = "total_employees"
        condition2.value = "100"

        rule.conditions = [condition1, condition2]
        return rule

    @pytest.fixture
    def or_rule(self):
        """Create a rule with OR boolean operator."""
        rule = MagicMock(spec=Rule)
        rule.boolean_operator = "OR"

        condition1 = MagicMock(spec=Condition)
        condition1.operator = "EQUALS"
        condition1.target_object = "industry"
        condition1.value = "Finance"

        condition2 = MagicMock(spec=Condition)
        condition2.operator = "GREATER_THAN"
        condition2.target_object = "total_employees"
        condition2.value = "100"

        rule.conditions = [condition1, condition2]
        return rule

    @pytest.mark.asyncio
    async def test_process_rule_single_condition_success(
        self, single_condition_rule, sample_company
    ):
        """Test processing rule with single condition that matches."""
        result = await process_rule(single_condition_rule, sample_company)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_rule_single_condition_failure(
        self, single_condition_rule, sample_company
    ):
        """Test processing rule with single condition that doesn't match."""
        # Modify the condition to fail
        single_condition_rule.conditions[0].value = "200"

        result = await process_rule(single_condition_rule, sample_company)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_rule_and_operator_all_match(
        self, and_rule, sample_company
    ):
        """Test AND rule where all conditions match."""
        result = await process_rule(and_rule, sample_company)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_rule_and_operator_partial_match(
        self, and_rule, sample_company
    ):
        """Test AND rule where only some conditions match."""
        # Modify one condition to fail
        and_rule.conditions[0].value = "Finance"

        result = await process_rule(and_rule, sample_company)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_rule_unsupported_boolean_operator(
        self, sample_company
    ):
        """Test error handling for unsupported boolean operators."""
        rule = MagicMock(spec=Rule)
        rule.boolean_operator = "XOR"  # Unsupported operator

        condition = MagicMock(spec=Condition)
        condition.operator = "EQUALS"
        condition.target_object = "industry"
        condition.value = "Technology"

        rule.conditions = [condition, condition]  # Multiple conditions

        with pytest.raises(ValueError) as exc_info:
            await process_rule(rule, sample_company)

        assert "Unsupported boolean operator: XOR" in str(exc_info.value)
