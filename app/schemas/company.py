"""
Pydantic schema definitions for the Company model.

These models are used to validate input data and serialize output
for the /import_company_data endpoint.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.processed_feature import ProcessedFeatureOut
from app.utils.parsing import number_or_none


class CompanyCreate(BaseModel):
    """
    Schema for creating a company record.

    This model validates input data from a JSON request when importing
    companies. Field names match the CSV header or JSON keys.
    """

    name: str
    url: str
    founded_year: int
    total_employees: int
    headquarters_city: str
    employee_locations: str
    employee_growth_2y: float | None
    employee_growth_1y: float | None
    employee_growth_6m: float | None
    description: str
    industry: str

    @classmethod
    def from_csv_row(cls, row: dict) -> "CompanyCreate":
        """
        Creates a CompanyCreate instance from a CSV row dictionary.

        This method parses and cleans data from a CSV row to populate the
        CompanyCreate schema.

        Args:
            row (dict): A dictionary representing a row from the CSV file.

        Returns:
            CompanyCreate: An instance of CompanyCreate populated with the row
            data.
        """
        return cls(
            name=row.get("company_name", "").strip(),
            url=row.get("url", "").strip(),
            founded_year=number_or_none(row.get("founded_year"), int),
            total_employees=number_or_none(row.get("total_employees"), int),
            headquarters_city=row.get("headquarters_city", "").strip(),
            employee_locations=row.get("employee_locations", "").strip(),
            employee_growth_2y=number_or_none(row.get("employee_rowth_2Y")),
            employee_growth_1y=number_or_none(row.get("employee_growth_1Y")),
            employee_growth_6m=number_or_none(row.get("employee_growth_6M")),
            description=(row.get("description") or "").strip(),
            industry=(row.get("industry") or "").strip(),
        )


class ImportSummary(BaseModel):
    """
    Response schema for the /import_company_data endpoint.

    Summarizes the results of the data import process.
    """

    imported_records: int
    skipped_duplicates: int
    record_errors: int
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "List of error messages for any records that failed to import."
        ),
    )


class CompanyOut(BaseModel):
    id: UUID
    url: str
    data: dict | None = None
    processed_features: list[ProcessedFeatureOut]
    imported_at: datetime
    last_processed_at: datetime | None = None

    class Config:
        from_attributes = True
        orm_mode = True
