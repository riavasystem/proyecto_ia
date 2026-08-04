from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.api.v1.routes import chat, plugins_public
from app.api.v1.routes._public_list import build_public_list_router
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.company import Company
from app.models.faq import FAQ
from app.models.product import Product
from app.models.promotion import Promotion
from app.models.service import Service
from app.schemas.company import CompanyRead
from app.schemas.faq import FAQRead
from app.schemas.product import ProductRead
from app.schemas.promotion import PromotionRead
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
