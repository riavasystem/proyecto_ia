from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.typing import FilteringBoundLogger


class PluginScreen(BaseModel):
    path: str
    label: str
    icon: str = ""


class PluginManifest(BaseModel):
    name: str
    version: str
    author: str = ""
    description: str = ""
    category: str = ""
    dependencies: list[str] = []
    permissions: list[str] = []
    hooks: list[str] = []
    screens: list[PluginScreen] = []
    chat_triggers: list[str] = []
    """Palabras clave que, si aparecen en un mensaje entrante, hacen que el
    motor de IA delegue la respuesta a este plugin (acción "chat") en vez de
    usar las categorías genéricas. Mantiene al Core desacoplado de plugins
    concretos (sección 8 del CLAUDE.md): el Core solo sabe matchear texto
    contra una lista declarada, nunca conoce la lógica de negocio detrás."""


@dataclass
class PluginContext:
    """Lo único que un plugin puede tocar del Core. Nunca importa módulos
    internos de app/ fuera de app/plugins_runtime (sección 8 del CLAUDE.md)."""

    company_id: UUID
    db: AsyncSession
    cache: Redis
    config: dict[str, Any]
    logger: FilteringBoundLogger
    user_id: UUID | None = None


@dataclass
class PluginResult:
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class PluginInterface(Protocol):
    manifest: PluginManifest

    async def install(self, ctx: PluginContext) -> None: ...
    async def update(self, ctx: PluginContext) -> None: ...
    async def uninstall(self, ctx: PluginContext) -> None: ...
    async def configure(self, ctx: PluginContext, config: dict[str, Any]) -> None: ...
    async def execute(
        self, ctx: PluginContext, action: str, payload: dict[str, Any]
    ) -> PluginResult: ...
    async def check_permissions(self, ctx: PluginContext, action: str) -> bool: ...
