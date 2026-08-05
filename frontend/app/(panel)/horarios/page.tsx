"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { CrudSection, type FieldConfig } from "@/lib/crud-page";

interface Branch {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  is_active: boolean;
}

interface BusinessHour {
  id: string;
  branch_id: string;
  day_of_week: number;
  opens_at: string;
  closes_at: string;
}

interface ScheduleException {
  id: string;
  branch_id: string;
  exception_date: string;
  is_closed: boolean;
  opens_at: string | null;
  closes_at: string | null;
  reason: string | null;
}

const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

export default function HorariosPage() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchesError, setBranchesError] = useState<string | null>(null);

  async function loadBranches() {
    try {
      setBranches(await apiFetch<Branch[]>("/api/v1/admin/branches"));
      setBranchesError(null);
    } catch (err) {
      setBranchesError(err instanceof ApiError ? err.message : "No se pudieron cargar sucursales");
    }
  }

  useEffect(() => {
    // Falso positivo conocido de react-hooks/set-state-in-effect para fetch-on-mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadBranches();
  }, []);

  const branchOptions = branches.map((b) => ({ value: b.id, label: b.name }));
  const branchName = (id: unknown) => branches.find((b) => b.id === id)?.name ?? String(id ?? "");

  const branchFields: FieldConfig<Branch>[] = [
    { name: "name", label: "Nombre" },
    { name: "address", label: "Dirección" },
    { name: "phone", label: "Teléfono" },
    { name: "is_active", label: "Activa", type: "checkbox" },
  ];

  const businessHourFields: FieldConfig<BusinessHour>[] = [
    { name: "branch_id", label: "Sucursal", type: "select", options: branchOptions, render: branchName },
    {
      name: "day_of_week",
      label: "Día",
      type: "select",
      options: DAYS.map((d, i) => ({ value: String(i), label: d })),
      render: (v) => DAYS[Number(v)] ?? String(v),
    },
    { name: "opens_at", label: "Abre", type: "time" },
    { name: "closes_at", label: "Cierra", type: "time" },
  ];

  const exceptionFields: FieldConfig<ScheduleException>[] = [
    { name: "branch_id", label: "Sucursal", type: "select", options: branchOptions, render: branchName },
    { name: "exception_date", label: "Fecha", type: "date" },
    { name: "is_closed", label: "Cerrado todo el día", type: "checkbox" },
    { name: "opens_at", label: "Abre (si no está cerrado)", type: "time" },
    { name: "closes_at", label: "Cierra (si no está cerrado)", type: "time" },
    { name: "reason", label: "Motivo" },
  ];

  return (
    <main className="flex flex-col gap-10 p-8">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Horarios y sucursales</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          El asistente usa esta información para responder preguntas de horario y disponibilidad
          por sucursal, sin necesidad de que nadie escriba texto libre.
        </p>
      </div>

      <CrudSection<Branch>
        title="Sucursales"
        headingTag="h2"
        resourcePath="/api/v1/admin/branches"
        fields={branchFields}
        emptyForm={{ name: "", address: "", phone: "", is_active: true }}
        onChange={loadBranches}
      />

      {branchesError && <p className="text-sm text-red-600">{branchesError}</p>}
      {branches.length === 0 ? (
        <p className="text-sm text-zinc-500">
          Creá al menos una sucursal para poder cargar horarios y excepciones.
        </p>
      ) : (
        <>
          <CrudSection<BusinessHour>
            title="Horario semanal"
            headingTag="h2"
            resourcePath="/api/v1/admin/business-hours"
            fields={businessHourFields}
            emptyForm={{ branch_id: "", day_of_week: "0", opens_at: "", closes_at: "" }}
          />

          <CrudSection<ScheduleException>
            title="Excepciones (feriados, cierres puntuales)"
            headingTag="h2"
            resourcePath="/api/v1/admin/schedule-exceptions"
            fields={exceptionFields}
            emptyForm={{
              branch_id: "",
              exception_date: "",
              is_closed: true,
              opens_at: "",
              closes_at: "",
              reason: "",
            }}
          />
        </>
      )}
    </main>
  );
}
