"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { FilmeResumo, Recomendacoes } from "@/lib/types";
import { MovieCarousel } from "./MovieCarousel";
import styles from "./Section.module.css";

export function Recommendations() {
  const { token, user } = useAuth();
  const [filmes, setFilmes] = useState<FilmeResumo[] | null>(null);
  const [fonte, setFonte] = useState<Recomendacoes["fonte"] | null>(null);
  const [failed, setFailed] = useState(false);
  const userId = user?.id;

  useEffect(() => {
    if (!token || userId === undefined) return;
    const controller = new AbortController();
    api<Recomendacoes>(`/users/me/recommendations/social?k=10`, { token, signal: controller.signal })
      .then((r) => {
        setFonte(r.fonte);
        setFilmes(r.itens.map((i) => i.filme));
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [token, userId]);

  return (
    <section>
      <h2 className={styles.title}>Recomendações para você</h2>
      {fonte && (
        <p className={styles.message}>
          {fonte === "seguindo"
            ? "Com base no gosto de quem você segue."
            : "Você ainda não segue ninguém: mostramos o que a comunidade inteira mais curte."}
        </p>
      )}
      {failed ? (
        <p className={styles.message}>Não foi possível carregar suas recomendações.</p>
      ) : filmes === null ? (
        <p className={styles.message}>Carregando…</p>
      ) : filmes.length === 0 ? (
        <p className={styles.message}>Avalie alguns filmes para receber recomendações.</p>
      ) : (
        <MovieCarousel filmes={filmes} />
      )}
    </section>
  );
}
