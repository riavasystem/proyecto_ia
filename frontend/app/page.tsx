import { apiFetch, type HealthStatus } from "@/lib/api";

async function getBackendHealth(): Promise<HealthStatus | null> {
  try {
    return await apiFetch<HealthStatus>("/api/v1/public/health");
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const health = await getBackendHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Panel administrativo</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Plataforma de asistentes digitales multi-tenant. Este panel consume exclusivamente la API
        pública del Core.
      </p>
      <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="font-medium">Estado del backend</h2>
        {health ? (
          <p className="text-sm text-emerald-600">
            {health.status} · {health.environment} · db: {health.database}
          </p>
        ) : (
          <p className="text-sm text-red-600">No se pudo conectar con la API.</p>
        )}
      </section>
    </main>
  );
}
