"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Counts {
  services: number;
  products: number;
  conversations: number;
  pluginsInstalled: number;
}

async function safeCount(path: string): Promise<number> {
  try {
    const data = await apiFetch<unknown[]>(path);
    return data.length;
  } catch {
    return 0;
  }
}

export default function DashboardPage() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [companyName, setCompanyName] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      safeCount("/api/v1/admin/services"),
      safeCount("/api/v1/admin/products"),
      safeCount("/api/v1/admin/conversations"),
      apiFetch<{ manifest: unknown; installation: unknown | null }[]>("/api/v1/admin/plugins")
        .then((items) => items.filter((i) => i.installation !== null).length)
        .catch(() => 0),
      apiFetch<{ name: string }>("/api/v1/admin/company")
        .then((c) => c.name)
        .catch(() => null),
    ]).then(([services, products, conversations, pluginsInstalled, name]) => {
      setCounts({ services, products, conversations, pluginsInstalled });
      setCompanyName(name);
    });
  }, []);

  const cards = counts
    ? [
        { label: "Servicios", value: counts.services },
        { label: "Productos", value: counts.products },
        { label: "Conversaciones", value: counts.conversations },
        { label: "Plugins instalados", value: counts.pluginsInstalled },
      ]
    : [];

  return (
    <main className="flex flex-col gap-6 p-8">
      <h1 className="text-xl font-semibold tracking-tight">
        {companyName ? `Hola, ${companyName}` : "Dashboard"}
      </h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <p className="text-2xl font-semibold">{card.value}</p>
            <p className="text-sm text-zinc-500">{card.label}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
