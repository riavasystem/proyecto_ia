from fastapi import APIRouter

from app.api.v1.routes._crud import build_crud_router
from app.models.schedule import BusinessHour, ScheduleException
from app.schemas.schedule import (
    BusinessHourCreate,
    BusinessHourRead,
    BusinessHourUpdate,
    ScheduleExceptionCreate,
    ScheduleExceptionRead,
    ScheduleExceptionUpdate,
)

router = APIRouter()
router.include_router(
    build_crud_router(
        model=BusinessHour,
        create_schema=BusinessHourCreate,
        update_schema=BusinessHourUpdate,
        read_schema=BusinessHourRead,
        prefix="/business-hours",
        tags=["schedule"],
    )
)
router.include_router(
    build_crud_router(
        model=ScheduleException,
        create_schema=ScheduleExceptionCreate,
        update_schema=ScheduleExceptionUpdate,
        read_schema=ScheduleExceptionRead,
        prefix="/schedule-exceptions",
        tags=["schedule"],
    )
)
