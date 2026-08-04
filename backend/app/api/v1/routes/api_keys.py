from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId
from app.core.exceptions import NotFoundError
from app.core.security import api_key_display_prefix, generate_api_key, hash_api_key
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _to_read(api_key: ApiKey) -> ApiKeyRead:
    return ApiKeyRead(
        id=api_key.id,
        company_id=api_key.company_id,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        environment=api_key.environment,
        scopes=api_key.scopes_list,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
    )


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate, company_id: CurrentCompanyId, db: DbSession
) -> ApiKeyCreated:
    plaintext = generate_api_key(payload.environment)
    api_key = ApiKey(
        company_id=company_id,
        name=payload.name,
        key_prefix=api_key_display_prefix(plaintext),
        key_hash=hash_api_key(plaintext),
        environment=payload.environment,
        scopes=",".join(payload.scopes),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreated(**_to_read(api_key).model_dump(), key=plaintext)


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(company_id: CurrentCompanyId, db: DbSession) -> list[ApiKeyRead]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.company_id == company_id).order_by(ApiKey.created_at)
    )
    return [_to_read(k) for k in result.scalars().all()]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: UUID, company_id: CurrentCompanyId, db: DbSession) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None or api_key.company_id != company_id:
        raise NotFoundError("Recurso no encontrado")
    api_key.is_active = False
    await db.commit()
