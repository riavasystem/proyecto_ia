from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId
from app.core.exceptions import NotFoundError
from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_owned_or_404(
    db: AsyncSession, model: type[Any], item_id: UUID, company_id: UUID
) -> Any:
    obj = await db.get(model, item_id)
    if obj is None or obj.company_id != company_id:
        raise NotFoundError("Recurso no encontrado")
    return obj


def build_crud_router(
    *,
    model: type[Any],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    prefix: str,
    tags: Sequence[str],
) -> APIRouter:
    """Genera un CRUD completo (list/create/get/update/delete) para una entidad
    de negocio del tenant, filtrando siempre por company_id.

    Los tipos Pydantic/SQLAlchemy se resuelven en tiempo de ejecución (parametrizados
    por el llamador), por lo que mypy no puede verificarlos estáticamente aquí —
    de ahí los `type: ignore` puntuales en este módulo.
    """

    router = APIRouter(prefix=prefix, tags=list(tags))

    @router.get("", response_model=list[read_schema])  # type: ignore[valid-type]
    async def list_items(company_id: CurrentCompanyId, db: DbSession) -> list[Any]:
        result = await db.execute(
            select(model).where(model.company_id == company_id).order_by(model.created_at)
        )
        return list(result.scalars().all())

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    async def create_item(
        payload: create_schema, company_id: CurrentCompanyId, db: DbSession  # type: ignore[valid-type]
    ) -> Any:
        obj = model(company_id=company_id, **payload.model_dump())  # type: ignore[attr-defined]
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @router.get("/{item_id}", response_model=read_schema)
    async def get_item(item_id: UUID, company_id: CurrentCompanyId, db: DbSession) -> Any:
        return await _get_owned_or_404(db, model, item_id, company_id)

    @router.patch("/{item_id}", response_model=read_schema)
    async def update_item(
        item_id: UUID, payload: update_schema, company_id: CurrentCompanyId, db: DbSession  # type: ignore[valid-type]
    ) -> Any:
        obj = await _get_owned_or_404(db, model, item_id, company_id)
        for field, value in payload.model_dump(exclude_unset=True).items():  # type: ignore[attr-defined]
            setattr(obj, field, value)
        await db.commit()
        await db.refresh(obj)
        return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: UUID, company_id: CurrentCompanyId, db: DbSession) -> None:
        obj = await _get_owned_or_404(db, model, item_id, company_id)
        await db.delete(obj)
        await db.commit()

    return router
