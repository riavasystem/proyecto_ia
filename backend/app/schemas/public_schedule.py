from pydantic import BaseModel

from app.schemas.branch import BranchRead
from app.schemas.schedule import BusinessHourRead, ScheduleExceptionRead


class PublicScheduleRead(BaseModel):
    branches: list[BranchRead]
    business_hours: list[BusinessHourRead]
    upcoming_exceptions: list[ScheduleExceptionRead]
