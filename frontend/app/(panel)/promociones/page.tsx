"use client";

import { CrudPage, type FieldConfig } from "@/lib/crud-page";

interface Promotion {
  id: string;
  name: string;
  description: string | null;
  starts_on: string | null;
  ends_on: string | null;
  is_active: boolean;
}

const fields: FieldConfig<Promotion>[] = [
  { name: "name", label: "Nombre" },
  { name: "description", label: "Descripción", type: "textarea" },
  { name: "starts_on", label: "Desde", type: "date" },
  { name: "ends_on", label: "Hasta", type: "date" },
  { name: "is_active", label: "Activa", type: "checkbox", render: (v) => (v ? "Sí" : "No") },
];

export default function PromocionesPage() {
  return (
    <CrudPage<Promotion>
      title="Promociones"
      resourcePath="/api/v1/admin/promotions"
      fields={fields}
      emptyForm={{ name: "", description: "", starts_on: "", ends_on: "", is_active: true }}
    />
  );
}
