"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearTokens, getAccessToken, setTokens } from "@/lib/api";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (companyName: string, adminEmail: string, adminPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    setIsAuthenticated(getAccessToken() !== null);
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string): Promise<void> {
    const tokens = await apiFetch<TokenResponse>("/api/v1/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    setIsAuthenticated(true);
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
    setIsAuthenticated(true);
    router.push("/dashboard");
  }

  function logout(): void {
    clearTokens();
    setIsAuthenticated(false);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
