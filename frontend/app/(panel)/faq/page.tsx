"use client";

import { CrudPage, type FieldConfig } from "@/lib/crud-page";

interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string | null;
}

const fields: FieldConfig<FAQ>[] = [
  { name: "question", label: "Pregunta" },
  { name: "answer", label: "Respuesta", type: "textarea" },
  { name: "category", label: "Categoría" },
];

export default function FaqPage() {
  return (
    <CrudPage<FAQ>
      title="FAQ"
      resourcePath="/api/v1/admin/faqs"
      fields={fields}
      emptyForm={{ question: "", answer: "", category: "" }}
    />
  );
}
