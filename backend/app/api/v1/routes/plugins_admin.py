from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.installed_plugin import InstalledPlugin
from app.plugins_runtime.manager import manager
from app.plugins_runtime.registry import registry
from app.schemas.plugin import (
    InstalledPluginRead,
    PluginConfigureRequest,
    PluginListItem,
    PluginManifestRead,
)

router = APIRouter(prefix="/plugins", tags=["plugins"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[PluginListItem])
async def list_plugins(company_id: CurrentCompanyId, db: DbSession) -> list[PluginListItem]:
    result = await db.execute(
        select(InstalledPlugin).where(InstalledPlugin.company_id == company_id)
    )
    installed_by_name = {p.plugin_name: p for p in result.scalars().all()}

    items = []
    for manifest in registry.list_manifests():
        installation = installed_by_name.get(manifest.name)
        items.append(
            PluginListItem(
                manifest=PluginManifestRead(**manifest.model_dump()),
                installation=(
                    InstalledPluginRead.model_validate(installation)
                    if installation is not None
                    else None
                ),
            )
        )
    return items


@router.post(
    "/{name}/install", response_model=InstalledPluginRead, status_code=status.HTTP_201_CREATED
)
async def install_plugin(name: str, company_id: CurrentCompanyId, db: DbSession) -> InstalledPlugin:
    return await manager.install(db, company_id, name)


@router.delete("/{name}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_plugin(name: str, company_id: CurrentCompanyId, db: DbSession) -> None:
    await manager.uninstall(db, company_id, name)


@router.patch("/{name}/configure", response_model=InstalledPluginRead)
async def configure_plugin(
    name: str, payload: PluginConfigureRequest, company_id: CurrentCompanyId, db: DbSession
) -> InstalledPlugin:
    return await manager.configure(db, company_id, name, payload.config)


@router.post("/{name}/enable", response_model=InstalledPluginRead)
async def enable_plugin(name: str, company_id: CurrentCompanyId, db: DbSession) -> InstalledPlugin:
    return await _set_enabled(db, company_id, name, True)


@router.post("/{name}/disable", response_model=InstalledPluginRead)
async def disable_plugin(name: str, company_id: CurrentCompanyId, db: DbSession) -> InstalledPlugin:
    return await _set_enabled(db, company_id, name, False)


async def _set_enabled(
    db: AsyncSession, company_id: UUID, name: str, enabled: bool
) -> InstalledPlugin:
    result = await db.execute(
        select(InstalledPlugin).where(
            InstalledPlugin.company_id == company_id, InstalledPlugin.plugin_name == name
        )
    )
    installation = result.scalar_one_or_none()
    if installation is None:
        raise NotFoundError(f"Plugin '{name}' no está instalado")
    installation.is_enabled = enabled
    await db.commit()
    await db.refresh(installation)
    return installation
