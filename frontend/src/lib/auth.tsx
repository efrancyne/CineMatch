"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { api, ApiError } from "./api";
import type { Token, UsuarioProprio } from "./types";

const STORAGE_KEY = "cinematch.token";
const EVENT = "cinematch:auth";

// O token vive no localStorage; useSyncExternalStore mantém abas e componentes em sincronia.
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(EVENT, callback);
  };
}

function readToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // armazenamento indisponível: a sessão só dura até recarregar
  }
  window.dispatchEvent(new Event(EVENT));
}

interface AuthContextValue {
  token: string | null;
  user: UsuarioProprio | null;
  /** false até sabermos se há sessão (evita redirecionar antes da hora) */
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (data: { username: string; name: string; email: string; password: string; generos?: string[] }) => Promise<void>;
  logout: () => void;
  /** atualiza o usuário em memória depois de editar o perfil */
  refreshUser: (user: UsuarioProprio) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const token = useSyncExternalStore(subscribe, readToken, () => null);
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const [loaded, setLoaded] = useState<{ token: string; user: UsuarioProprio | null } | null>(null);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    api<UsuarioProprio>("/users/me", { token, signal: controller.signal })
      .then((user) => setLoaded({ token, user }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        // token expirado/inválido: encerra a sessão
        if (err instanceof ApiError && err.status === 401) writeToken(null);
        else setLoaded({ token, user: null });
      });
    return () => controller.abort();
  }, [token]);

  const user = token && loaded?.token === token ? loaded.user : null;
  const ready = hydrated && (!token || loaded?.token === token);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api<Token>("/auth/login", { method: "POST", body: { username, password } });
    writeToken(res.access_token);
  }, []);

  const register = useCallback(
    async (data: { username: string; name: string; email: string; password: string; generos?: string[] }) => {
      await api("/auth/register", { method: "POST", body: { ...data, generos: data.generos ?? [] } });
      const res = await api<Token>("/auth/login", {
        method: "POST",
        body: { username: data.username, password: data.password },
      });
      writeToken(res.access_token);
    },
    [],
  );

  const logout = useCallback(() => writeToken(null), []);

  const refreshUser = useCallback((updated: UsuarioProprio) => {
    setLoaded((l) => (l ? { ...l, user: updated } : l));
  }, []);

  const value = useMemo(
    () => ({ token, user, ready, login, register, logout, refreshUser }),
    [token, user, ready, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
