"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useIsMounted } from "@/lib/use-is-mounted";

interface PluginManifest {
  name: string;
  version: string;
  description: string;
  category: string;
  permissions: string[];
  hooks: string[];
}

interface Installation {
  id: string;
  version: string;
  is_enabled: boolean;
}

interface PluginListItem {
  manifest: PluginManifest;
  installation: Installation | null;
}

export default function PluginsPage() {
  const [items, setItems] = useState<PluginListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const isMounted = useIsMounted();

  async function load() {
    try {
      const data = await apiFetch<PluginListItem[]>("/api/v1/admin/plugins");
      if (isMounted.current) {
        setItems(data);
        setError(null);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar");
      }
    } finally {
      if (isMounted.current) setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(name: string, action: "install" | "uninstall" | "enable" | "disable") {
    setBusy(name);
    setError(null);
    try {
      const method = action === "install" ? "POST" : action === "uninstall" ? "DELETE" : "POST";
      const path =
        action === "uninstall"
          ? `/api/v1/admin/plugins/${name}/uninstall`
          : `/api/v1/admin/plugins/${name}/${action}`;
      await apiFetch(path, { method });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="flex flex-col gap-6 p-8">
      <h1 className="text-xl font-semibold tracking-tight">Plugins</h1>
      <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Extensiones independientes que agregan lógica de negocio (sección 8 del CLAUDE.md). El
        Core solo administra su instalación y estado.
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {isLoading ? (
        <p className="text-sm text-zinc-500">Cargando…</p>
      ) : (
        <div className="flex flex-col gap-4">
          {items.map((item) => (
            <div
              key={item.manifest.name}
              className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-medium">
                    {item.manifest.name}{" "}
                    <span className="text-xs text-zinc-500">v{item.manifest.version}</span>
                  </h2>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {item.manifest.description}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Permisos: {item.manifest.permissions.join(", ") || "ninguno"}
                  </p>
                </div>
                <div className="flex gap-2">
                  {item.installation === null ? (
                    <button
                      disabled={busy === item.manifest.name}
                      onClick={() => run(item.manifest.name, "install")}
                      className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
                    >
                      Instalar
                    </button>
                  ) : (
                    <>
                      <span className="self-center text-xs text-emerald-600">
                        {item.installation.is_enabled ? "instalado y activo" : "instalado, deshabilitado"}
                      </span>
                      <button
                        disabled={busy === item.manifest.name}
                        onClick={() =>
                          run(item.manifest.name, item.installation!.is_enabled ? "disable" : "enable")
                        }
                        className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-zinc-700"
                      >
                        {item.installation.is_enabled ? "Deshabilitar" : "Habilitar"}
                      </button>
                      <button
                        disabled={busy === item.manifest.name}
                        onClick={() => run(item.manifest.name, "uninstall")}
                        className="rounded-md border border-red-300 px-3 py-1.5 text-sm text-red-600 disabled:opacity-50 dark:border-red-800"
                      >
                        Desinstalar
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
