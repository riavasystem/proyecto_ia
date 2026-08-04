from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]


def build_public_list_router(
    *,
    model: type[Any],
    read_schema: type[BaseModel],
    prefix: str,
    tags: Sequence[str],
    active_only: bool = True,
) -> APIRouter:
    """Endpoint público de solo lectura (list), autenticado por API key con
    scope catalog:read y sujeto a rate limit. Ver _crud.py para el porqué de
    los `type: ignore` puntuales (tipos paramétricos en runtime)."""

    router = APIRouter(prefix=prefix, tags=list(tags))

    @router.get(
        "",
        response_model=list[read_schema],  # type: ignore[valid-type]
        dependencies=[Depends(require_scope("catalog:read")), Depends(enforce_rate_limit)],
    )
    async def list_items(company_id: CurrentCompanyId, db: DbSession) -> list[Any]:
        query = select(model).where(model.company_id == company_id)
        if active_only:
            query = query.where(model.is_active.is_(True))
        result = await db.execute(query.order_by(model.created_at))
        return list(result.scalars().all())

    return router
