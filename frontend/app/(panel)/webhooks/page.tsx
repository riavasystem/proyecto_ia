"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, ApiError } from "@/lib/api";

interface WebhookEndpoint {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
}

interface WebhookEndpointCreated extends WebhookEndpoint {
  secret: string;
}

interface WebhookDelivery {
  id: string;
  created_at: string;
  event_type: string;
  status: string;
  attempt_count: number;
  last_status_code: number | null;
  last_error: string | null;
}

const AVAILABLE_EVENTS = [
  "message.received",
  "message.replied",
  "conversation.started",
  "conversation.closed",
  "handoff.requested",
  "plugin.executed",
];

const STATUS_LABEL: Record<string, string> = {
  pending: "pendiente",
  success: "entregado",
  dead_letter: "fallido (agotó reintentos)",
};

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<string[]>([]);
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [openDeliveriesFor, setOpenDeliveriesFor] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);

  async function load() {
    try {
      setWebhooks(await apiFetch<WebhookEndpoint[]>("/api/v1/admin/webhooks"));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    // Falso positivo conocido de react-hooks/set-state-in-effect para fetch-on-mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  function toggleEvent(event: string) {
    setEvents((prev) => (prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]));
  }

  async function handleCreate(formEvent: FormEvent) {
    formEvent.preventDefault();
    setError(null);
    try {
      const created = await apiFetch<WebhookEndpointCreated>("/api/v1/admin/webhooks", {
        method: "POST",
        body: JSON.stringify({ url, events }),
      });
      setCreatedSecret(created.secret);
      setUrl("");
      setEvents([]);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el webhook");
    }
  }

  async function handleToggleActive(webhook: WebhookEndpoint) {
    await apiFetch(`/api/v1/admin/webhooks/${webhook.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !webhook.is_active }),
    });
    await load();
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar este webhook? Se perderá su historial de entregas.")) return;
    await apiFetch(`/api/v1/admin/webhooks/${id}`, { method: "DELETE" });
    if (openDeliveriesFor === id) setOpenDeliveriesFor(null);
    await load();
  }

  async function handleViewDeliveries(id: string) {
    if (openDeliveriesFor === id) {
      setOpenDeliveriesFor(null);
      return;
    }
    setOpenDeliveriesFor(id);
    setDeliveriesLoading(true);
    try {
      setDeliveries(await apiFetch<WebhookDelivery[]>(`/api/v1/admin/webhooks/${id}/deliveries`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las entregas");
    } finally {
      setDeliveriesLoading(false);
    }
  }

  return (
    <main className="flex flex-col gap-6 p-8">
      <h1 className="text-xl font-semibold tracking-tight">Webhooks</h1>
      <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Notificaciones salientes hacia sistemas externos cuando pasan cosas en la plataforma
        (sección 10.6 del CLAUDE.md). Cada entrega va firmada con HMAC-SHA256 en el header
        <code className="mx-1 rounded bg-zinc-100 px-1 dark:bg-zinc-800">X-Signature</code>
        para que puedas verificar que viene de acá.
      </p>

      {createdSecret && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm dark:border-emerald-800 dark:bg-emerald-950/30">
          <p className="font-medium">
            Copiá este secreto ahora, no se volverá a mostrar. Lo necesitás para verificar la
            firma de cada entrega:
          </p>
          <code className="mt-2 block break-all rounded bg-white px-2 py-1 dark:bg-zinc-900">
            {createdSecret}
          </code>
          <button onClick={() => setCreatedSecret(null)} className="mt-2 text-sm underline">
            Cerrar
          </button>
        </div>
      )}

      <form
        onSubmit={handleCreate}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
      >
        <label className="flex flex-col gap-1 text-sm">
          URL
          <input
            required
            type="url"
            placeholder="https://tu-sistema.com/hooks/asistente"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-72 rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <fieldset className="flex flex-col gap-1 text-sm">
          <legend>Eventos</legend>
          <div className="flex max-w-md flex-wrap gap-2">
            {AVAILABLE_EVENTS.map((event) => (
              <label key={event} className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  checked={events.includes(event)}
                  onChange={() => toggleEvent(event)}
                />
                {event}
              </label>
            ))}
          </div>
        </fieldset>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={events.length === 0}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
        >
          Crear webhook
        </button>
      </form>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Cargando…</p>
      ) : webhooks.length === 0 ? (
        <p className="text-sm text-zinc-500">Todavía no hay webhooks configurados.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {webhooks.map((webhook) => (
            <div
              key={webhook.id}
              className="rounded-lg border border-zinc-200 dark:border-zinc-800"
            >
              <div className="flex flex-wrap items-center gap-3 p-3">
                <span className="font-mono text-sm break-all">{webhook.url}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    webhook.is_active
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                      : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                  }`}
                >
                  {webhook.is_active ? "activo" : "inactivo"}
                </span>
                <span className="text-xs text-zinc-500">{webhook.events.join(", ")}</span>
                <div className="ml-auto flex gap-3 text-sm">
                  <button onClick={() => handleViewDeliveries(webhook.id)} className="underline">
                    {openDeliveriesFor === webhook.id ? "Ocultar entregas" : "Ver entregas"}
                  </button>
                  <button onClick={() => handleToggleActive(webhook)} className="underline">
                    {webhook.is_active ? "Desactivar" : "Activar"}
                  </button>
                  <button
                    onClick={() => handleDelete(webhook.id)}
                    className="text-red-600 underline"
                  >
                    Eliminar
                  </button>
                </div>
              </div>

              {openDeliveriesFor === webhook.id && (
                <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
                  {deliveriesLoading ? (
                    <p className="text-sm text-zinc-500">Cargando entregas…</p>
                  ) : deliveries.length === 0 ? (
                    <p className="text-sm text-zinc-500">Todavía no hay entregas registradas.</p>
                  ) : (
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-50 dark:bg-zinc-900">
                        <tr>
                          <th className="px-2 py-1 font-medium">Fecha</th>
                          <th className="px-2 py-1 font-medium">Evento</th>
                          <th className="px-2 py-1 font-medium">Estado</th>
                          <th className="px-2 py-1 font-medium">Intentos</th>
                          <th className="px-2 py-1 font-medium">HTTP</th>
                          <th className="px-2 py-1 font-medium">Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {deliveries.map((delivery) => (
                          <tr key={delivery.id} className="border-t border-zinc-200 dark:border-zinc-800">
                            <td className="px-2 py-1 text-xs">
                              {new Date(delivery.created_at).toLocaleString()}
                            </td>
                            <td className="px-2 py-1 text-xs">{delivery.event_type}</td>
                            <td className="px-2 py-1 text-xs">
                              {STATUS_LABEL[delivery.status] ?? delivery.status}
                            </td>
                            <td className="px-2 py-1 text-xs">{delivery.attempt_count}</td>
                            <td className="px-2 py-1 text-xs">{delivery.last_status_code ?? "—"}</td>
                            <td className="px-2 py-1 text-xs text-red-600">
                              {delivery.last_error ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
