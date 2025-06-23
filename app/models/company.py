"""
Defines the SQLAlchemy ORM model for representing company data in the database.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Company(Base):
    """Represents a company entity in the database with various business
    attributes.

    This SQLAlchemy model defines the structure of the 'companies' table and
    its fields.
    """

    __tablename__ = "companies"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name = Column(String, nullable=False)
    url = Column(String)
    founded_year = mapped_column(Integer, nullable=False)
    total_employees = mapped_column(Integer, nullable=False)
    headquarters_city = mapped_column(String, nullable=False)
    employee_locations = mapped_column(String, nullable=False)
    employee_growth_2y = mapped_column(Float, nullable=True)
    employee_growth_1y = mapped_column(Float, nullable=True)
    employee_growth_6m = mapped_column(Float, nullable=True)
    description = mapped_column(Text, nullable=True)
    industry = mapped_column(String, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC).replace(tzinfo=None)
    )
    last_processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    processed_features = relationship(
        "ProcessedFeature",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    @property
    def headquarters_country(self) -> str | None:
        """
        Extracts the country from the city string. For example:
        "Paris (France)" → "France"
        "Berlin (Deutschland)" → "Deutschland"
        """
        if not self.headquarters_city:
            return None

        match = re.search(r"\((?P<country>[^)]+)\)", self.headquarters_city)
        return match["country"].strip() if match else None

    @property
    def company_age(self) -> int | None:
        """
        Calculate age based on foundation year.
        """
        return (
            datetime.now().year - self.founded_year
            if self.founded_year
            else None
        )
