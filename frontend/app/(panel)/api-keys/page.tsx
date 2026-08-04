"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, ApiError } from "@/lib/api";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  environment: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
}

interface ApiKeyCreated extends ApiKey {
  key: string;
}

const AVAILABLE_SCOPES = [
  "chat:write",
  "conversations:read",
  "catalog:read",
  "catalog:write",
  "plugins:execute",
  "webhooks:manage",
];

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState<"live" | "test">("test");
  const [scopes, setScopes] = useState<string[]>([]);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  async function load() {
    try {
      setKeys(await apiFetch<ApiKey[]>("/api/v1/admin/api-keys"));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function toggleScope(scope: string) {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await apiFetch<ApiKeyCreated>("/api/v1/admin/api-keys", {
        method: "POST",
        body: JSON.stringify({ name, environment, scopes }),
      });
      setCreatedKey(created.key);
      setName("");
      setScopes([]);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la key");
    }
  }

  async function handleRevoke(id: string) {
    if (!confirm("¿Revocar esta API key?")) return;
    await apiFetch(`/api/v1/admin/api-keys/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <main className="flex flex-col gap-6 p-8">
      <h1 className="text-xl font-semibold tracking-tight">API Keys</h1>
      <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Estas keys autentican a proyectos externos contra la API pública (sección 10 del
        CLAUDE.md). El valor completo solo se muestra una vez, al crearla.
      </p>

      {createdKey && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm dark:border-emerald-800 dark:bg-emerald-950/30">
          <p className="font-medium">Copiá esta key ahora, no se volverá a mostrar:</p>
          <code className="mt-2 block break-all rounded bg-white px-2 py-1 dark:bg-zinc-900">
            {createdKey}
          </code>
          <button onClick={() => setCreatedKey(null)} className="mt-2 text-sm underline">
            Cerrar
          </button>
        </div>
      )}

      <form
        onSubmit={handleCreate}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
      >
        <label className="flex flex-col gap-1 text-sm">
          Nombre
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-48 rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Entorno
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value as "live" | "test")}
            className="rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
          >
            <option value="test">test</option>
            <option value="live">live</option>
          </select>
        </label>
        <fieldset className="flex flex-col gap-1 text-sm">
          <legend>Scopes</legend>
          <div className="flex max-w-md flex-wrap gap-2">
            {AVAILABLE_SCOPES.map((scope) => (
              <label key={scope} className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={() => toggleScope(scope)}
                />
                {scope}
              </label>
            ))}
          </div>
        </fieldset>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white dark:bg-white dark:text-zinc-900"
        >
          Crear key
        </button>
      </form>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Cargando…</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2 font-medium">Nombre</th>
                <th className="px-3 py-2 font-medium">Prefijo</th>
                <th className="px-3 py-2 font-medium">Entorno</th>
                <th className="px-3 py-2 font-medium">Scopes</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key.id} className="border-t border-zinc-200 dark:border-zinc-800">
                  <td className="px-3 py-2">{key.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{key.key_prefix}…</td>
                  <td className="px-3 py-2">{key.environment}</td>
                  <td className="px-3 py-2 text-xs">{key.scopes.join(", ")}</td>
                  <td className="px-3 py-2">{key.is_active ? "activa" : "revocada"}</td>
                  <td className="px-3 py-2">
                    {key.is_active && (
                      <button
                        onClick={() => handleRevoke(key.id)}
                        className="text-sm text-red-600 underline"
                      >
                        Revocar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
