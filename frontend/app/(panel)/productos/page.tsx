"use client";

import { CrudPage, type FieldConfig } from "@/lib/crud-page";

interface Product {
  id: string;
  name: string;
  sku: string | null;
  price: number | null;
  stock: number | null;
  is_active: boolean;
}

const fields: FieldConfig<Product>[] = [
  { name: "name", label: "Nombre" },
  { name: "sku", label: "Código (SKU)" },
  { name: "price", label: "Precio", type: "number" },
  { name: "stock", label: "Stock", type: "number" },
  { name: "is_active", label: "Activo", type: "checkbox", render: (v) => (v ? "Sí" : "No") },
];

export default function ProductosPage() {
  return (
    <CrudPage<Product>
      title="Productos"
      resourcePath="/api/v1/admin/products"
      fields={fields}
      emptyForm={{ name: "", sku: "", price: "", stock: "", is_active: true }}
    />
  );
}
