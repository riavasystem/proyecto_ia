from datetime import date, time
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ReadBase


class BusinessHourCreate(BaseModel):
    branch_id: UUID
    day_of_week: int
    opens_at: time
    closes_at: time


class BusinessHourUpdate(BaseModel):
    day_of_week: int | None = None
    opens_at: time | None = None
    closes_at: time | None = None


class BusinessHourRead(ReadBase):
    branch_id: UUID
    day_of_week: int
    opens_at: time
    closes_at: time


class ScheduleExceptionCreate(BaseModel):
    branch_id: UUID
    exception_date: date
    is_closed: bool = True
    opens_at: time | None = None
    closes_at: time | None = None
    reason: str | None = None


class ScheduleExceptionUpdate(BaseModel):
    exception_date: date | None = None
    is_closed: bool | None = None
    opens_at: time | None = None
    closes_at: time | None = None
    reason: str | None = None


class ScheduleExceptionRead(ReadBase):
    branch_id: UUID
    exception_date: date
    is_closed: bool
    opens_at: time | None
    closes_at: time | None
    reason: str | None
