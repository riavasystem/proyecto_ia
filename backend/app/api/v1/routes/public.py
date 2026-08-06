from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.api.v1.routes import chat, plugins_public, webhooks_public
from app.api.v1.routes._public_list import build_public_list_router
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.branch import Branch
from app.models.company import Company
from app.models.faq import FAQ
from app.models.product import Product
from app.models.promotion import Promotion
from app.models.schedule import BusinessHour, ScheduleException
from app.models.service import Service
from app.schemas.branch import BranchRead
from app.schemas.company import CompanyRead
from app.schemas.faq import FAQRead
from app.schemas.product import ProductRead
from app.schemas.promotion import PromotionRead
from app.schemas.public_schedule import PublicScheduleRead
from app.schemas.schedule import BusinessHourRead, ScheduleExceptionRead
from app.schemas.service import ServiceRead

router = APIRouter(prefix="/public", tags=["public"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health")
async def public_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/company",
    response_model=CompanyRead,
    dependencies=[Depends(require_scope("catalog:read")), Depends(enforce_rate_limit)],
)
async def get_public_company(company_id: CurrentCompanyId, db: DbSession) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Empresa no encontrada")
    return company


@router.get(
    "/schedule",
    response_model=PublicScheduleRead,
    dependencies=[Depends(require_scope("catalog:read")), Depends(enforce_rate_limit)],
)
async def get_public_schedule(company_id: CurrentCompanyId, db: DbSession) -> PublicScheduleRead:
    """Horarios de atención de todas las sucursales activas del tenant, más
    las excepciones (feriados, cambios puntuales) desde hoy en adelante — no
    tiene sentido devolver excepciones ya pasadas. No es un 'listado largo'
    (siempre son pocos registros), así que no lleva paginación por cursor."""
    branches = (
        (
            await db.execute(
                select(Branch).where(Branch.company_id == company_id, Branch.is_active.is_(True))
            )
        )
        .scalars()
        .all()
    )
    business_hours = (
        (
            await db.execute(
                select(BusinessHour)
                .where(BusinessHour.company_id == company_id)
                .order_by(BusinessHour.day_of_week)
            )
        )
        .scalars()
        .all()
    )
    upcoming_exceptions = (
        (
            await db.execute(
                select(ScheduleException)
                .where(
                    ScheduleException.company_id == company_id,
                    ScheduleException.exception_date >= date.today(),
                )
                .order_by(ScheduleException.exception_date)
            )
        )
        .scalars()
        .all()
    )
    return PublicScheduleRead(
        branches=[BranchRead.model_validate(b) for b in branches],
        business_hours=[BusinessHourRead.model_validate(h) for h in business_hours],
        upcoming_exceptions=[ScheduleExceptionRead.model_validate(e) for e in upcoming_exceptions],
    )


router.include_router(
    build_public_list_router(
        model=Service, read_schema=ServiceRead, prefix="/services", tags=["public"]
    )
)
router.include_router(
    build_public_list_router(
        model=Product, read_schema=ProductRead, prefix="/products", tags=["public"]
    )
)
router.include_router(
    build_public_list_router(
        model=Promotion, read_schema=PromotionRead, prefix="/promotions", tags=["public"]
    )
)
router.include_router(
    build_public_list_router(
        model=FAQ, read_schema=FAQRead, prefix="/faq", tags=["public"], active_only=False
    )
)
router.include_router(chat.router)
router.include_router(plugins_public.router)
router.include_router(webhooks_public.router)
