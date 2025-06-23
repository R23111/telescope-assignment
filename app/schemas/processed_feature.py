from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProcessedFeatureBase(BaseModel):
    company_id: UUID
    rule_id: UUID
    user_id: UUID
    feature_name: str
    value: int


class ProcessedFeatureCreate(ProcessedFeatureBase):
    pass


class ProcessedFeatureRead(ProcessedFeatureBase):
    id: UUID
    processed_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
        extra = "forbid"


class ProcessedFeatureOut(BaseModel):
    company_name: str | None = None
    feature_name: str | None = None
    user_name: str | None = None
    value: int

    class Config:
        extra = "forbid"
