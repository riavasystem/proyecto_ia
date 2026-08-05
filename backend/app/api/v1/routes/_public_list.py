from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.pagination import CursorPage, CursorParams, apply_cursor, build_page, cursor_params
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
    scope catalog:read, paginado por cursor (sección 10.7 del CLAUDE.md) y
    sujeto a rate limit. Ver _crud.py para el porqué de los `type: ignore`
    puntuales (tipos paramétricos en runtime)."""

    router = APIRouter(prefix=prefix, tags=list(tags))

    @router.get(
        "",
        response_model=CursorPage[read_schema],  # type: ignore[valid-type]
        dependencies=[Depends(require_scope("catalog:read")), Depends(enforce_rate_limit)],
    )
    async def list_items(
        company_id: CurrentCompanyId,
        db: DbSession,
        params: Annotated[CursorParams, Depends(cursor_params)],
    ) -> CursorPage[Any]:
        query = select(model).where(model.company_id == company_id)
        if active_only:
            query = query.where(model.is_active.is_(True))
        query = apply_cursor(query, model, params)
        result = await db.execute(query)
        items, next_cursor = build_page(list(result.scalars().all()), params)
        return CursorPage(data=items, next_cursor=next_cursor)

    return router
