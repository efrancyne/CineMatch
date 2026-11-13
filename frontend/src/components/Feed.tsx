"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ItemFeed, Pagina } from "@/lib/types";
import { FeedItem } from "./FeedItem";
import styles from "./Section.module.css";

const TAMANHO = 20;

interface State {
  itens: ItemFeed[];
  total: number;
  pagina: number;
}

export function Feed() {
  const { token } = useAuth();
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    api<Pagina<ItemFeed>>(`/users/me/feed?pagina=1&tamanho=${TAMANHO}`, { token, signal: controller.signal })
      .then((p) => setState({ itens: p.itens, total: p.total, pagina: p.pagina }))
      .catch((err: Error) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [token]);

  async function loadMore() {
    if (!state) return;
    setLoadingMore(true);
    try {
      const p = await api<Pagina<ItemFeed>>(`/users/me/feed?pagina=${state.pagina + 1}&tamanho=${TAMANHO}`, { token });
      setState({ itens: [...state.itens, ...p.itens], total: p.total, pagina: p.pagina });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <section>
      <h2 className={styles.title}>O que seus amigos estão assistindo?</h2>
      {error ? (
        <p className={styles.message}>{error}</p>
      ) : state === null ? (
        <p className={styles.message}>Carregando…</p>
      ) : state.itens.length === 0 ? (
        <p className={styles.message}>Siga outros usuários para ver o que eles estão assistindo.</p>
      ) : (
        <>
          <div>
            {state.itens.map((item) => (
              <FeedItem key={item.id} item={item} />
            ))}
          </div>
          {state.itens.length < state.total && (
            <button type="button" className={styles.more} onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? "Carregando…" : "Ver mais"}
            </button>
          )}
        </>
      )}
    </section>
  );
}
