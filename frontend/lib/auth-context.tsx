"use client";

import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/api";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (companyName: string, adminEmail: string, adminPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// El token vive en localStorage, fuera del árbol de React. useSyncExternalStore
// es la forma correcta de leerlo: evita el mismatch de hidratación que produciría
// un useEffect + setState en el primer render (server no ve localStorage).
let listeners: Array<() => void> = [];

function notifyAuthChanged(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

function getSnapshot(): boolean {
  return getAccessToken() !== null;
}

function getServerSnapshot(): boolean {
  return false;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const isAuthenticated = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const router = useRouter();

  async function login(email: string, password: string): Promise<void> {
    const tokens = await apiFetch<TokenResponse>("/api/v1/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    notifyAuthChanged();
    router.push("/dashboard");
  }

  async function register(
    companyName: string,
    adminEmail: string,
    adminPassword: string,
  ): Promise<void> {
    const tokens = await apiFetch<TokenResponse>("/api/v1/admin/auth/register", {
      method: "POST",
      body: JSON.stringify({
        company_name: companyName,
        admin_email: adminEmail,
        admin_password: adminPassword,
      }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    notifyAuthChanged();
    router.push("/dashboard");
  }

  function logout(): void {
    const refreshToken = getRefreshToken();
    clearTokens();
    notifyAuthChanged();
    router.push("/login");
    if (refreshToken) {
      // Best-effort: invalida el refresh token en el servidor. Si falla (red,
      // backend caído), la sesión local ya quedó cerrada de todas formas.
      void apiFetch("/api/v1/admin/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
