from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.company import Company
from app.schemas.company import CompanyRead, CompanyUpdate

router = APIRouter(prefix="/company", tags=["company"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=CompanyRead)
async def get_company(company_id: CurrentCompanyId, db: DbSession) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Empresa no encontrada")
    return company


@router.patch("", response_model=CompanyRead)
async def update_company(
    payload: CompanyUpdate, company_id: CurrentCompanyId, db: DbSession
) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Empresa no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.commit()
    await db.refresh(company)
    return company
