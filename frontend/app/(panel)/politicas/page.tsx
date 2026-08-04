"use client";

import { CrudPage, type FieldConfig } from "@/lib/crud-page";

interface Policy {
  id: string;
  type: string;
  content: string;
}

const fields: FieldConfig<Policy>[] = [
  { name: "type", label: "Tipo (pagos, garantias, devoluciones, reservas, privacidad)" },
  { name: "content", label: "Contenido", type: "textarea" },
];

export default function PoliticasPage() {
  return (
    <CrudPage<Policy>
      title="Políticas"
      resourcePath="/api/v1/admin/policies"
      fields={fields}
      emptyForm={{ type: "", content: "" }}
    />
  );
}
