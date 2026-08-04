import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DomainError, NotFoundError
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models.installed_plugin import InstalledPlugin
from app.plugins_runtime.interface import PluginContext, PluginResult
from app.plugins_runtime.registry import registry


class PluginExecutionError(DomainError):
    code = "plugin_error"
    status_code = 502


class PluginManager:
    """Instalar/desinstalar/configurar propaga errores del plugin como
    PluginExecutionError (el admin necesita saber que algo falló). execute()
    en cambio nunca deja que una excepción o un timeout del plugin tumbe la
    request: siempre devuelve un PluginResult, con éxito o degradado."""

    def _build_context(
        self,
        db: AsyncSession,
        company_id: UUID,
        config: dict[str, Any],
        user_id: UUID | None = None,
    ) -> PluginContext:
        return PluginContext(
            company_id=company_id,
            db=db,
            cache=get_redis(),
            config=config,
            logger=get_logger(plugins_runtime=True).bind(company_id=str(company_id)),
            user_id=user_id,
        )

    async def _get_installation(
        self, db: AsyncSession, company_id: UUID, name: str
    ) -> InstalledPlugin | None:
        result = await db.execute(
            select(InstalledPlugin).where(
                InstalledPlugin.company_id == company_id, InstalledPlugin.plugin_name == name
            )
        )
        return result.scalar_one_or_none()

    async def install(self, db: AsyncSession, company_id: UUID, name: str) -> InstalledPlugin:
        manifest = registry.get_manifest(name)
        plugin = registry.get(name)
        if manifest is None or plugin is None:
            raise NotFoundError(f"Plugin '{name}' no encontrado")

        existing = await self._get_installation(db, company_id, name)
        if existing is not None:
            return existing

        ctx = self._build_context(db, company_id, {})
        try:
            await plugin.install(ctx)
        except Exception as exc:
            raise PluginExecutionError(f"Falló la instalación del plugin '{name}'") from exc

        installation = InstalledPlugin(
            company_id=company_id, plugin_name=name, version=manifest.version, config={}
        )
        db.add(installation)
        await db.commit()
        await db.refresh(installation)
        return installation

    async def uninstall(self, db: AsyncSession, company_id: UUID, name: str) -> None:
        installation = await self._get_installation(db, company_id, name)
        if installation is None:
            raise NotFoundError(f"Plugin '{name}' no está instalado")

        plugin = registry.get(name)
        if plugin is not None:
            ctx = self._build_context(db, company_id, installation.config)
            try:
                await plugin.uninstall(ctx)
            except Exception:
                ctx.logger.exception("plugin_uninstall_failed", plugin=name)

        await db.delete(installation)
        await db.commit()

    async def configure(
        self, db: AsyncSession, company_id: UUID, name: str, config: dict[str, Any]
    ) -> InstalledPlugin:
        plugin = registry.get(name)
        installation = await self._get_installation(db, company_id, name)
        if plugin is None or installation is None:
            raise NotFoundError(f"Plugin '{name}' no está instalado")

        ctx = self._build_context(db, company_id, config)
        try:
            await plugin.configure(ctx, config)
        except Exception as exc:
            raise PluginExecutionError(f"Falló la configuración del plugin '{name}'") from exc

        installation.config = config
        await db.commit()
        await db.refresh(installation)
        return installation

    async def execute(
        self,
        db: AsyncSession,
        company_id: UUID,
        name: str,
        action: str,
        payload: dict[str, Any],
        user_id: UUID | None = None,
    ) -> PluginResult:
        plugin = registry.get(name)
        installation = await self._get_installation(db, company_id, name)
        if plugin is None or installation is None or not installation.is_enabled:
            return PluginResult(success=False, message="Plugin no instalado o deshabilitado")

        ctx = self._build_context(db, company_id, installation.config, user_id)

        try:
            allowed = await plugin.check_permissions(ctx, action)
        except Exception:
            ctx.logger.exception("plugin_check_permissions_failed", plugin=name, action=action)
            return PluginResult(success=False, message="Error interno del plugin")

        if not allowed:
            return PluginResult(success=False, message="Acción no permitida para este plugin")

        timeout = get_settings().plugin_execution_timeout_seconds
        try:
            return await asyncio.wait_for(plugin.execute(ctx, action, payload), timeout=timeout)
        except TimeoutError:
            ctx.logger.warning("plugin_execution_timeout", plugin=name, action=action)
            return PluginResult(success=False, message="El plugin tardó demasiado en responder")
        except Exception:
            ctx.logger.exception("plugin_execution_failed", plugin=name, action=action)
            return PluginResult(success=False, message="Ocurrió un error ejecutando el plugin")


manager = PluginManager()
