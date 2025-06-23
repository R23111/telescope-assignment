from uuid import UUID

from pydantic import BaseModel, Field


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    user_name: str = Field(..., example="master_user")
    rules: list[dict] = Field(...)


class RuleOut(BaseModel):
    """Schema for returning rule information."""

    success: bool = Field(..., example=True)
    message: str = Field(..., example="Rule created successfully")
    rule: dict = Field(...)


class Condition(BaseModel):
    """Schema for a condition used in rule definitions.

    This model represents a condition with its type, operator, value, and
    boolean operator for logical combinations.
    """

    operation: str
    value: str
    rule_id: UUID
