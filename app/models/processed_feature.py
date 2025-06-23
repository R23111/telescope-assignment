from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProcessedFeature(Base):
    __tablename__ = "processed_features"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("rules.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    feature_name: Mapped[str]
    value: Mapped[int]

    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC).replace(tzinfo=None)
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id"), nullable=False
    )
    company = relationship("Company", back_populates="processed_features")
    rule = relationship("Rule", back_populates="processed_features")
    user = relationship("User", back_populates="processed_features")
