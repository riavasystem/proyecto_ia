"use client";

import { CrudPage, type FieldConfig } from "@/lib/crud-page";

interface Service {
  id: string;
  name: string;
  category: string | null;
  price: number | null;
  estimated_minutes: number | null;
  is_active: boolean;
}

const fields: FieldConfig<Service>[] = [
  { name: "name", label: "Nombre" },
  { name: "category", label: "Categoría" },
  { name: "price", label: "Precio", type: "number" },
  { name: "estimated_minutes", label: "Duración (min)", type: "number" },
  { name: "is_active", label: "Activo", type: "checkbox", render: (v) => (v ? "Sí" : "No") },
];

export default function ServiciosPage() {
  return (
    <CrudPage<Service>
      title="Servicios"
      resourcePath="/api/v1/admin/services"
      fields={fields}
      emptyForm={{
        name: "",
        category: "",
        price: "",
        estimated_minutes: "",
        is_active: true,
      }}
    />
  );
}
