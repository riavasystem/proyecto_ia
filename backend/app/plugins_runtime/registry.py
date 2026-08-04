import importlib.util
import json
from pathlib import Path
from types import ModuleType

from app.core.config import get_settings
from app.plugins_runtime.interface import PluginInterface, PluginManifest


class PluginRegistry:
    """Descubre plugins en disco (manifest.json + plugin.py) y los mantiene
    en memoria. Un plugin roto (manifest inválido, import que explota) se
    omite y se loguea, no tumba el arranque del Core."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInterface] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._discovered = False

    def discover(self, force: bool = False) -> None:
        if self._discovered and not force:
            return
        self._plugins.clear()
        self._manifests.clear()

        plugins_dir = Path(get_settings().plugins_dir).resolve()
        if not plugins_dir.is_dir():
            self._discovered = True
            return

        for plugin_dir in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
            manifest_path = plugin_dir / "manifest.json"
            plugin_file = plugin_dir / "plugin.py"
            if not manifest_path.exists() or not plugin_file.exists():
                continue
            try:
                manifest = PluginManifest.model_validate(json.loads(manifest_path.read_text()))
                module = self._load_module(plugin_dir.name, plugin_file)
                plugin_instance: PluginInterface = module.plugin
            except Exception:
                continue

            self._manifests[manifest.name] = manifest
            self._plugins[manifest.name] = plugin_instance

        self._discovered = True

    @staticmethod
    def _load_module(dir_name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(f"proyecto_ia_plugins.{dir_name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo cargar el plugin en {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def get(self, name: str) -> PluginInterface | None:
        self.discover()
        return self._plugins.get(name)

    def get_manifest(self, name: str) -> PluginManifest | None:
        self.discover()
        return self._manifests.get(name)

    def list_manifests(self) -> list[PluginManifest]:
        self.discover()
        return list(self._manifests.values())


registry = PluginRegistry()
