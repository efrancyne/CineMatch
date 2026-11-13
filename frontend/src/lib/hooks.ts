"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Pagina } from "./types";

/** GET autenticado. Passe `null` para não buscar (ex.: parâmetro ainda desconhecido). */
export function useApi<T>(path: string | null) {
  const { token } = useAuth();
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<{ key: string; data?: T; error?: string } | null>(null);
  const key = `${path}#${nonce}`;

  useEffect(() => {
    if (!path || !token) return;
    const controller = new AbortController();
    api<T>(path, { token, signal: controller.signal })
      .then((data) => setState({ key, data }))
      .catch((err: Error) => {
        if (!controller.signal.aborted) setState({ key, error: err.message });
      });
    return () => controller.abort();
  }, [path, token, key]);

  const current = state?.key === key ? state : null;
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const setData = useCallback(
    (update: (old: T) => T) =>
      setState((s) => (s?.data !== undefined ? { ...s, data: update(s.data) } : s)),
    [],
  );
  return { data: current?.data, error: current?.error, loading: !!path && !current, reload, setData };
}

interface Paged<T> {
  key: string;
  itens: T[];
  total: number;
  pagina: number;
  error?: string;
}

/** Lista paginada com "ver mais". Reinicia quando `path` muda. */
export function usePaged<T>(path: string | null, tamanho = 20) {
  const { token } = useAuth();
  const [state, setState] = useState<Paged<T> | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const sep = path?.includes("?") ? "&" : "?";
  const url = (pagina: number) => `${path}${sep}pagina=${pagina}&tamanho=${tamanho}`;

  useEffect(() => {
    if (!path || !token) return;
    const controller = new AbortController();
    api<Pagina<T>>(`${path}${sep}pagina=1&tamanho=${tamanho}`, { token, signal: controller.signal })
      .then((p) => setState({ key: path, itens: p.itens, total: p.total, pagina: p.pagina }))
      .catch((err: Error) => {
        if (!controller.signal.aborted) setState({ key: path, itens: [], total: 0, pagina: 1, error: err.message });
      });
    return () => controller.abort();
  }, [path, token, tamanho, sep]);

  const current = state?.key === path ? state : null;

  async function loadMore() {
    if (!current || !path) return;
    setLoadingMore(true);
    try {
      const p = await api<Pagina<T>>(url(current.pagina + 1), { token });
      setState({ ...current, itens: [...current.itens, ...p.itens], total: p.total, pagina: p.pagina });
    } catch (err) {
      setState({ ...current, error: (err as Error).message });
    } finally {
      setLoadingMore(false);
    }
  }

  const setItens = useCallback(
    (update: (old: T[]) => T[]) => setState((s) => (s ? { ...s, itens: update(s.itens) } : s)),
    [],
  );

  return {
    itens: current?.itens ?? [],
    total: current?.total ?? 0,
    error: current?.error,
    loading: !!path && !current,
    hasMore: !!current && current.itens.length < current.total,
    loadingMore,
    loadMore,
    setItens,
  };
}
