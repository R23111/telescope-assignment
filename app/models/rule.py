"""
Defines the SQLAlchemy ORM model for representing user data in the database.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User


class Condition(Base):
    """Represents a single condition belonging to a rule."""

    __tablename__ = "conditions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    operator: Mapped[str] = mapped_column(String, nullable=False)
    target_object: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE")
    )
    rule: Mapped["Rule"] = relationship("Rule", back_populates="conditions")


class Rule(Base):
    """
    Represents a rule belonging to a user, used for data processing logic.
    """

    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    input: Mapped[str] = mapped_column(String, nullable=False)
    boolean_operator: Mapped[str] = mapped_column(String, nullable=True)
    feature_name: Mapped[str] = mapped_column(String, nullable=False)
    match: Mapped[int] = mapped_column(Integer, nullable=False)
    default: Mapped[int] = mapped_column(Integer, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    user: Mapped[User] = relationship("User", back_populates="rules")

    conditions: Mapped[list["Condition"]] = relationship(
        "Condition", back_populates="rule", cascade="all, delete-orphan"
    )

    processed_features = relationship(
        "ProcessedFeature", back_populates="rule", cascade="all, delete-orphan"
    )
