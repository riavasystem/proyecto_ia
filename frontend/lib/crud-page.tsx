"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { apiFetch, ApiError } from "@/lib/api";

export interface FieldConfig<T> {
  name: keyof T & string;
  label: string;
  type?: "text" | "number" | "textarea" | "checkbox" | "date" | "time" | "select";
  options?: { value: string; label: string }[]; // requerido si type === "select"
  render?: (value: T[keyof T]) => ReactNode;
}

interface CrudSectionProps<T extends { id: string }> {
  title: string;
  resourcePath: string; // e.g. "/api/v1/admin/services"
  fields: FieldConfig<T>[];
  emptyForm: Record<string, unknown>;
  headingTag?: "h1" | "h2";
  onChange?: () => void; // notifica a un padre cuando la lista cambia (alta/edición/borrado)
}

/** El cuerpo de un CRUD genérico (form + tabla), sin wrapper de página propio,
 * para poder combinar varias secciones en una sola pantalla (p. ej. Horarios:
 * sucursales + horario semanal + excepciones). CrudPage lo envuelve para el
 * caso de uso original de "una pantalla, un recurso". */
export function CrudSection<T extends { id: string }>({
  title,
  resourcePath,
  fields,
  emptyForm,
  headingTag = "h1",
  onChange,
}: CrudSectionProps<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<T[]>(resourcePath);
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista");
    } finally {
      setIsLoading(false);
    }
  }, [resourcePath]);

  useEffect(() => {
    // Fetch-on-mount estándar: react-hooks/set-state-in-effect marca cualquier
    // setState alcanzable desde el efecto, incluso detrás de un await — falso
    // positivo conocido de esta regla para el patrón clásico de carga inicial.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function startEdit(item: T) {
    setEditingId(item.id);
    const next: Record<string, unknown> = {};
    for (const field of fields) {
      next[field.name] = (item as Record<string, unknown>)[field.name] ?? "";
    }
    setForm(next);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value === "" ? null : value]),
    );
    try {
      if (editingId) {
        await apiFetch(`${resourcePath}/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch(resourcePath, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      startCreate();
      await load();
      onChange?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar este registro?")) return;
    try {
      await apiFetch(`${resourcePath}/${id}`, { method: "DELETE" });
      await load();
      onChange?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    }
  }

  const Heading = headingTag;

  return (
    <section className="flex flex-col gap-4">
      <Heading
        className={
          headingTag === "h1"
            ? "text-xl font-semibold tracking-tight"
            : "text-base font-semibold tracking-tight"
        }
      >
        {title}
      </Heading>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <form
        onSubmit={handleSubmit}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
      >
        {fields.map((field) => (
          <label key={field.name} className="flex flex-col gap-1 text-sm">
            {field.label}
            {field.type === "textarea" ? (
              <textarea
                value={String(form[field.name] ?? "")}
                onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
                className="w-56 rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
              />
            ) : field.type === "checkbox" ? (
              <input
                type="checkbox"
                checked={Boolean(form[field.name])}
                onChange={(e) => setForm({ ...form, [field.name]: e.target.checked })}
                className="h-4 w-4 self-start"
              />
            ) : field.type === "select" ? (
              <select
                value={String(form[field.name] ?? "")}
                onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
                className="w-56 rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
              >
                <option value="">Seleccioná una opción</option>
                {(field.options ?? []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.type ?? "text"}
                value={String(form[field.name] ?? "")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    [field.name]:
                      field.type === "number"
                        ? e.target.value === ""
                          ? ""
                          : Number(e.target.value)
                        : e.target.value,
                  })
                }
                className="w-56 rounded-md border border-zinc-300 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900"
              />
            )}
          </label>
        ))}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-zinc-900"
        >
          {editingId ? "Guardar cambios" : "Crear"}
        </button>
        {editingId && (
          <button type="button" onClick={startCreate} className="text-sm underline">
            Cancelar
          </button>
        )}
      </form>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Cargando…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">Todavía no hay registros.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 dark:bg-zinc-900">
              <tr>
                {fields.map((field) => (
                  <th key={field.name} className="px-3 py-2 font-medium">
                    {field.label}
                  </th>
                ))}
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-zinc-200 dark:border-zinc-800">
                  {fields.map((field) => {
                    const value = (item as Record<string, unknown>)[field.name] as T[keyof T];
                    return (
                      <td key={field.name} className="px-3 py-2">
                        {field.render ? field.render(value) : String(value ?? "")}
                      </td>
                    );
                  })}
                  <td className="flex gap-3 px-3 py-2">
                    <button onClick={() => startEdit(item)} className="text-sm underline">
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="text-sm text-red-600 underline"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

interface CrudPageProps<T extends { id: string }> {
  title: string;
  resourcePath: string;
  fields: FieldConfig<T>[];
  emptyForm: Record<string, unknown>;
}

export function CrudPage<T extends { id: string }>(props: CrudPageProps<T>) {
  return (
    <main className="flex flex-col gap-6 p-8">
      <CrudSection {...props} headingTag="h1" />
    </main>
  );
}
