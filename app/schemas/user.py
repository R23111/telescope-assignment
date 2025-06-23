"""
Schemas for user-related operations.
"""
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    user_name: str = Field(..., example="master_user")


class UserOut(BaseModel):
    """Schema for returning user info."""
    id: UUID
    user_name: str

    class Config:
        orm_mode = True
