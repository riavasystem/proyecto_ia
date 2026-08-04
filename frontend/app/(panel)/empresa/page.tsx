"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, ApiError } from "@/lib/api";

interface Company {
  id: string;
  name: string;
  industry: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  is_active: boolean;
}

export default function EmpresaPage() {
  const [company, setCompany] = useState<Company | null>(null);
  const [form, setForm] = useState({ name: "", industry: "", email: "", phone: "", website: "" });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<Company>("/api/v1/admin/company")
      .then((data) => {
        setCompany(data);
        setForm({
          name: data.name,
          industry: data.industry ?? "",
          email: data.email ?? "",
          phone: data.phone ?? "",
          website: data.website ?? "",
        });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar"))
      .finally(() => setIsLoading(false));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await apiFetch<Company>("/api/v1/admin/company", {
        method: "PATCH",
        body: JSON.stringify(form),
      });
      setCompany(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <main className="p-8 text-sm text-zinc-500">Cargando…</main>;

  return (
    <main className="flex max-w-md flex-col gap-6 p-8">
      <h1 className="text-xl font-semibold tracking-tight">Empresa</h1>
      {company && (
        <p className="text-sm text-zinc-500">
          Estado: {company.is_active ? "activa" : "inactiva"}
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Nombre
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Rubro
          <input
            value={form.industry}
            onChange={(e) => setForm({ ...form, industry: e.target.value })}
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Teléfono
          <input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Sitio web
          <input
            value={form.website}
            onChange={(e) => setForm({ ...form, website: e.target.value })}
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {saved && <p className="text-sm text-emerald-600">Guardado.</p>}
        <button
          type="submit"
          disabled={isSaving}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
        >
          {isSaving ? "Guardando..." : "Guardar"}
        </button>
      </form>
    </main>
  );
}
