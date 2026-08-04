"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/empresa", label: "Empresa" },
  { href: "/servicios", label: "Servicios" },
  { href: "/productos", label: "Productos" },
  { href: "/promociones", label: "Promociones" },
  { href: "/politicas", label: "Políticas" },
  { href: "/faq", label: "FAQ" },
  { href: "/plugins", label: "Plugins" },
  { href: "/api-keys", label: "API Keys" },
  { href: "/conversaciones", label: "Conversaciones" },
];

export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-zinc-500">Cargando…</p>
      </main>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col gap-1 border-r border-zinc-200 p-4 dark:border-zinc-800">
        <h1 className="mb-4 px-2 text-sm font-semibold tracking-tight">Panel administrativo</h1>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-md px-2 py-1.5 text-sm ${
              pathname?.startsWith(item.href)
                ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }`}
          >
            {item.label}
          </Link>
        ))}
        <button
          onClick={logout}
          className="mt-4 rounded-md px-2 py-1.5 text-left text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
        >
          Cerrar sesión
        </button>
      </aside>
      <div className="flex-1 overflow-x-auto">{children}</div>
    </div>
  );
}
