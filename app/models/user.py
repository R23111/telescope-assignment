"""
Defines the SQLAlchemy ORM model for representing user data in the database.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.models.rule import Rule

from app.models.base import Base


class User(Base):
    """
    SQLAlchemy ORM model for representing a user in the database.

    This model defines the structure of the 'users' table and its relationship
    to rules.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_name: Mapped[str] = Column(
        String, unique=True, index=True, nullable=False
    )
    rules: Mapped[list[Rule]] = relationship(
        "Rule", back_populates="user", cascade="all, delete-orphan"
    )
    processed_features = relationship(
        "ProcessedFeature", back_populates="user", cascade="all, delete-orphan"
    )
