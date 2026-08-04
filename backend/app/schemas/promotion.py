from datetime import date

from pydantic import BaseModel

from app.schemas.common import ReadBase


class PromotionCreate(BaseModel):
    name: str
    description: str | None = None
    conditions: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool = True


class PromotionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    conditions: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool | None = None


class PromotionRead(ReadBase):
    name: str
    description: str | None
    conditions: str | None
    starts_on: date | None
    ends_on: date | None
    is_active: bool
