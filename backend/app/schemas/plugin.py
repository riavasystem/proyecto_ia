from typing import Any

from pydantic import BaseModel

from app.plugins_runtime.interface import PluginScreen
from app.schemas.common import ReadBase


class PluginManifestRead(BaseModel):
    name: str
    version: str
    author: str
    description: str
    category: str
    permissions: list[str]
    hooks: list[str]
    screens: list[PluginScreen]
    chat_triggers: list[str]


class InstalledPluginRead(ReadBase):
    plugin_name: str
    version: str
    config: dict[str, Any]
    is_enabled: bool


class PluginListItem(BaseModel):
    manifest: PluginManifestRead
    installation: InstalledPluginRead | None = None

    @property
    def is_installed(self) -> bool:
        return self.installation is not None


class PluginConfigureRequest(BaseModel):
    config: dict[str, Any]


class PluginExecuteRequest(BaseModel):
    action: str
    payload: dict[str, Any] = {}


class PluginExecuteResponse(BaseModel):
    success: bool
    message: str
    data: dict[str, Any]
