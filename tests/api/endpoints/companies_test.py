"""
Object-oriented pytest unit tests for the import_company_data endpoint.
"""

import csv
from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.companies import import_company_data
from app.models.company import Company
from app.schemas.company import CompanyCreate, ImportSummary


class TestImportCompanyData:
    """
    Test class for the import_company_data endpoint function.

    This class contains comprehensive unit tests covering various scenarios
    including file uploads, JSON imports, error handling, and edge cases.
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
    def sample_company_data(self):
        """Sample company data for testing."""
        return [
            CompanyCreate(
                name="TechCorp Inc",
                url="https://techcorp.com",
                founded_year=2010,
                total_employees=150,
                headquarters_city="San Francisco",
                employee_locations="San Francisco, New York",
                employee_growth_2y=0.25,
                employee_growth_1y=0.15,
                employee_growth_6m=0.08,
                description="A technology company focused on innovation",
                industry="Technology",
            ),
            CompanyCreate(
                name="DataSoft LLC",
                url="https://datasoft.com",
                founded_year=2015,
                total_employees=75,
                headquarters_city="Austin",
                employee_locations="Austin, Remote",
                employee_growth_2y=0.45,
                employee_growth_1y=0.30,
                employee_growth_6m=0.12,
                description="Data analytics and software solutions",
                industry="Software",
            ),
        ]

    @pytest.fixture
    def sample_csv_content(self, sample_company_data):
        """Create CSV content from sample company data."""
        from io import StringIO

        output = StringIO()
        fieldnames = [
            "company_name",
            "url",
            "founded_year",
            "total_employees",
            "headquarters_city",
            "employee_locations",
            "employee_rowth_2Y",
            "employee_growth_1Y",
            "employee_growth_6M",
            "description",
            "industry",
        ]

        writer = csv.DictWriter(
            output, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()

        for company in sample_company_data:
            writer.writerow(
                {
                    "company_name": company.name,
                    "url": company.url,
                    "founded_year": company.founded_year,
                    "total_employees": company.total_employees,
                    "headquarters_city": company.headquarters_city,
                    "employee_locations": company.employee_locations,
                    "employee_rowth_2Y": company.employee_growth_2y,
                    "employee_growth_1Y": company.employee_growth_1y,
                    "employee_growth_6M": company.employee_growth_6m,
                    "description": company.description,
                    "industry": company.industry,
                }
            )

        content = output.getvalue()
        output.close()
        return content

    @pytest.fixture
    def csv_upload_file(self, sample_csv_content):
        """Create an UploadFile object with CSV content."""
        file_like = BytesIO(sample_csv_content.encode("utf-8"))
        return UploadFile(filename="test_companies.csv", file=file_like)

    @pytest.fixture
    def existing_company(self):
        """Create a mock existing company for duplicate testing."""
        return Company(
            id=uuid4(),
            name="Existing Company",
            url="https://existing.com",
            founded_year=2020,
            total_employees=100,
            headquarters_city="Boston",
            employee_locations="Boston",
            description="An existing company",
            industry="Existing Industry",
        )

    @pytest.mark.asyncio
    async def test_successful_csv_import(
        self, mock_db, csv_upload_file, sample_company_data
    ):
        """Test successful import of company data from CSV file."""
        # Setup: No existing companies found
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Execute
        result = await import_company_data(
            file=csv_upload_file, json_data=None, db=mock_db
        )

        # Assert
        assert isinstance(result, ImportSummary)
        assert result.imported_records == 2
        assert result.skipped_duplicates == 0
        assert result.record_errors == 0
        assert result.errors == []

        # Verify database operations
        assert mock_db.execute.call_count == 2  # One check per company
        assert mock_db.add.call_count == 2  # One add per company
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_json_import(self, mock_db, sample_company_data):
        """Test successful import of company data from JSON payload."""
        # Setup: No existing companies found
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Execute
        result = await import_company_data(
            file=None, json_data=sample_company_data, db=mock_db
        )

        # Assert
        assert isinstance(result, ImportSummary)
        assert result.imported_records == 2
        assert result.skipped_duplicates == 0
        assert result.record_errors == 0
        assert result.errors == []

        # Verify database operations
        assert mock_db.execute.call_count == 2
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_data_provided_raises_exception(self, mock_db):
        """Test that HTTPException is raised when no data is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await import_company_data(file=None, json_data=None, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "No data provided" in str(exc_info.value.detail)

        # Verify no database operations occurred
        mock_db.execute.assert_not_called()
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_takes_precedence_over_json(
        self, mock_db, csv_upload_file, sample_company_data
    ):
        """
        Test that file data takes precedence when both file and JSON are
        provided.
        """
        # Setup: No existing companies found
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Execute with both file and JSON data
        result = await import_company_data(
            file=csv_upload_file, json_data=sample_company_data, db=mock_db
        )

        # Assert: Should process file data (2 companies)
        assert result.imported_records == 2
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_companies_skipped(
        self, mock_db, sample_company_data, existing_company
    ):
        """Test that duplicate companies are skipped based on URL."""
        # Setup: First company exists, second doesn't
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            existing_company,  # First company exists
            None,  # Second company doesn't exist
        ]

        # Execute
        result = await import_company_data(
            file=None, json_data=sample_company_data, db=mock_db
        )

        # Assert
        assert result.imported_records == 1
        assert result.skipped_duplicates == 1
        assert result.record_errors == 0
        assert result.errors == []

        # Verify database operations
        assert mock_db.execute.call_count == 2  # Checked both companies
        assert mock_db.add.call_count == 1  # Only added the non-duplicate
        mock_db.commit.assert_called_once()


class TestGetCompanies:
    """
    Test class for the get_companies endpoint function.

    This class contains unit tests covering various scenarios for retrieving
    companies with their processed features and metadata.
    """

    @pytest.fixture
    def mock_db(self):
        """Mock database session for testing."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        from app.models.user import User

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.user_name = "test_user"
        return user

    @pytest.fixture
    def mock_rule(self):
        """Create a mock rule for testing."""
        from app.models.rule import Rule

        rule = MagicMock(spec=Rule)
        rule.id = uuid4()
        rule.rule_name = "test_rule"
        return rule

    @pytest.fixture
    def mock_processed_feature(self, mock_user, mock_rule):
        """Create a mock processed feature for testing."""
        from app.models.processed_feature import ProcessedFeature

        pf = MagicMock(spec=ProcessedFeature)
        pf.id = uuid4()
        pf.feature_name = "employee_count"
        pf.value = 100
        pf.user = mock_user
        pf.rule = mock_rule
        return pf

    @pytest.fixture
    def mock_company(self, mock_processed_feature):
        """Create a mock company with processed features."""
        company = MagicMock(spec=Company)
        company.id = uuid4()
        company.name = "Test Company"
        company.url = "https://testcompany.com"
        company.founded_year = 2020
        company.total_employees = 100
        company.headquarters_city = "San Francisco"
        company.employee_locations = "San Francisco, Remote"
        company.employee_growth_2y = 0.15
        company.employee_growth_1y = 0.10
        company.employee_growth_6m = 0.05
        company.description = "A test company"
        company.industry = "Technology"
        company.imported_at = datetime.now()
        company.last_processed_at = datetime.now()
        company.processed_features = [mock_processed_feature]
        return company

    @pytest.mark.asyncio
    async def test_successful_get_companies_with_features(
        self, mock_db, mock_company
    ):
        """Test successful retrieval of companies with processed features."""
        # Setup: Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_company]
        mock_db.execute.return_value = mock_result

        # Mock the inspect function to return proper column attributes
        with patch("app.api.endpoints.companies.inspect") as mock_inspect:
            # Create mock column attributes
            mock_col_attrs = []
            attr_names = [
                "name",
                "url",
                "founded_year",
                "total_employees",
                "headquarters_city",
                "employee_locations",
                "employee_growth_2y",
                "employee_growth_1y",
                "employee_growth_6m",
                "description",
                "industry",
            ]
            for attr_name in attr_names:
                mock_attr = MagicMock()
                mock_attr.key = attr_name
                mock_col_attrs.append(mock_attr)

            mock_mapper = MagicMock()
            mock_mapper.column_attrs = mock_col_attrs
            mock_inspect.return_value.mapper = mock_mapper

            # Execute
            from app.api.endpoints.companies import get_companies

            result = await get_companies(db=mock_db)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1

        company_out = result[0]
        assert company_out.id == mock_company.id
        assert company_out.url == mock_company.url
        assert company_out.imported_at == mock_company.imported_at
        assert company_out.last_processed_at == mock_company.last_processed_at

        # Verify processed features
        assert len(company_out.processed_features) == 1
        pf_out = company_out.processed_features[0]
        assert pf_out.user_name == "test_user"
        assert pf_out.company_name == "Test Company"
        assert pf_out.feature_name == "employee_count"
        assert pf_out.value == 100

        # Verify database query was called correctly
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_companies_empty_result(self, mock_db):
        """Test get_companies when no companies exist."""
        # Setup: Mock empty database result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Execute
        from app.api.endpoints.companies import get_companies

        result = await get_companies(db=mock_db)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_companies_multiple_companies(self, mock_db):
        """Test get_companies with multiple companies."""
        # Setup: Create multiple mock companies
        companies = []
        for i in range(3):
            company = MagicMock(spec=Company)
            company.id = uuid4()
            company.name = f"Company {i+1}"
            company.url = f"https://company{i+1}.com"
            company.founded_year = 2020 + i
            company.total_employees = 50 * (i + 1)
            company.headquarters_city = f"City {i+1}"
            company.employee_locations = f"City {i+1}"
            company.employee_growth_2y = 0.1 * (i + 1)
            company.employee_growth_1y = 0.05 * (i + 1)
            company.employee_growth_6m = 0.02 * (i + 1)
            company.description = f"Description for company {i+1}"
            company.industry = "Technology"
            company.imported_at = datetime.now()
            company.last_processed_at = None
            company.processed_features = []
            companies.append(company)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = companies
        mock_db.execute.return_value = mock_result

        # Mock the inspect function
        with patch("app.api.endpoints.companies.inspect") as mock_inspect:
            mock_col_attrs = []
            attr_names = [
                "name",
                "url",
                "founded_year",
                "total_employees",
                "headquarters_city",
                "employee_locations",
                "employee_growth_2y",
                "employee_growth_1y",
                "employee_growth_6m",
                "description",
                "industry",
            ]
            for attr_name in attr_names:
                mock_attr = MagicMock()
                mock_attr.key = attr_name
                mock_col_attrs.append(mock_attr)

            mock_mapper = MagicMock()
            mock_mapper.column_attrs = mock_col_attrs
            mock_inspect.return_value.mapper = mock_mapper

            # Execute
            from app.api.endpoints.companies import get_companies

            result = await get_companies(db=mock_db)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3

        for i, company_out in enumerate(result):
            assert company_out.id == companies[i].id
            assert company_out.url == companies[i].url
            assert company_out.imported_at == companies[i].imported_at
            assert company_out.last_processed_at is None
            assert len(company_out.processed_features) == 0

    @pytest.mark.asyncio
    async def test_get_companies_with_multiple_processed_features(
        self, mock_db, mock_user, mock_rule
    ):
        """
        Test get_companies with a company having multiple processed features.
        """
        # Setup: Create company with multiple processed features
        company = MagicMock(spec=Company)
        company.id = uuid4()
        company.name = "Multi-Feature Company"
        company.url = "https://multifeature.com"
        company.founded_year = 2018
        company.total_employees = 200
        company.headquarters_city = "New York"
        company.employee_locations = "New York, London"
        company.employee_growth_2y = 0.30
        company.employee_growth_1y = 0.20
        company.employee_growth_6m = 0.10
        company.description = "A company with multiple features"
        company.industry = "Finance"
        company.imported_at = datetime.now()
        company.last_processed_at = datetime.now()

        # Create multiple processed features
        features = []
        feature_names = [
            "revenue_growth",
            "employee_satisfaction",
            "market_share",
        ]
        feature_values = [85, 92, 15]

        for name, value in zip(feature_names, feature_values):
            pf = MagicMock()
            pf.feature_name = name
            pf.value = value
            pf.user = mock_user
            pf.rule = mock_rule
            features.append(pf)

        company.processed_features = features

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [company]
        mock_db.execute.return_value = mock_result

        # Mock the inspect function
        with patch("app.api.endpoints.companies.inspect") as mock_inspect:
            mock_col_attrs = []
            attr_names = [
                "name",
                "url",
                "founded_year",
                "total_employees",
                "headquarters_city",
                "employee_locations",
                "employee_growth_2y",
                "employee_growth_1y",
                "employee_growth_6m",
                "description",
                "industry",
            ]
            for attr_name in attr_names:
                mock_attr = MagicMock()
                mock_attr.key = attr_name
                mock_col_attrs.append(mock_attr)

            mock_mapper = MagicMock()
            mock_mapper.column_attrs = mock_col_attrs
            mock_inspect.return_value.mapper = mock_mapper

            # Execute
            from app.api.endpoints.companies import get_companies

            result = await get_companies(db=mock_db)

        # Assert
        assert len(result) == 1
        company_out = result[0]
        assert len(company_out.processed_features) == 3

        # Verify all processed features are correctly transformed
        feature_dict = {
            pf.feature_name: pf.value for pf in company_out.processed_features
        }
        assert feature_dict["revenue_growth"] == 85
        assert feature_dict["employee_satisfaction"] == 92
        assert feature_dict["market_share"] == 15

        # Verify all features have correct user and company names
        for pf_out in company_out.processed_features:
            assert pf_out.user_name == "test_user"
            assert pf_out.company_name == "Multi-Feature Company"

    @pytest.mark.asyncio
    async def test_get_companies_database_error_handling(self, mock_db):
        """Test get_companies handles database errors gracefully."""
        # Setup: Mock database to raise an exception
        mock_db.execute.side_effect = Exception("Database connection error")

        # Execute and Assert: Should raise the database exception
        from app.api.endpoints.companies import get_companies

        with pytest.raises(Exception) as exc_info:
            await get_companies(db=mock_db)

        assert "Database connection error" in str(exc_info.value)
        mock_db.execute.assert_called_once()
