"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { EstadoFilme } from "@/lib/types";
import { RatingInput } from "./RatingInput";
import page from "./page.module.css";
import styles from "./MyMovieState.module.css";

interface Props {
  movieId: number;
  estado: EstadoFilme;
  onChange: (update: (old: EstadoFilme) => EstadoFilme) => void;
  /** chamado depois de publicar/atualizar a review, para recarregar a lista */
  onReviewSaved: () => void;
}

export function MyMovieState({ movieId, estado, onChange, onReviewSaved }: Props) {
  const { token } = useAuth();
  const [texto, setTexto] = useState(estado.review ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const rate = (nota: number) =>
    run(async () => {
      await api("/ratings", { method: "POST", token, body: { movie_id: movieId, rating: nota } });
      onChange((e) => ({ ...e, nota }));
    });

  const removeRating = () => {
    if (!window.confirm("Remover sua nota? Se você escreveu uma review, ela e seus comentários também serão apagados.")) return;
    return run(async () => {
      await api(`/ratings/${movieId}`, { method: "DELETE", token });
      setTexto("");
      onChange((e) => ({ ...e, nota: null, review_id: null, review: null }));
      onReviewSaved();
    });
  };

  const toggle = (campo: "favorito" | "watchlist", rota: "favorites" | "watchlist") =>
    run(async () => {
      const ligar = !estado[campo];
      await api(`/${rota}/${movieId}`, { method: ligar ? "POST" : "DELETE", token });
      onChange((e) => ({ ...e, [campo]: ligar }));
    });

  const saveReview = (e: React.FormEvent) => {
    e.preventDefault();
    const review = texto.trim();
    if (!review || estado.nota === null) return;
    return run(async () => {
      const res = await api<{ review_id: number | null }>("/ratings", {
        method: "POST",
        token,
        body: { movie_id: movieId, rating: estado.nota, review },
      });
      onChange((s) => ({ ...s, review, review_id: res.review_id }));
      onReviewSaved();
    });
  };

  return (
    <section className={styles.panel} aria-label="Sua avaliação">
      <div className={styles.row}>
        <div>
          <h2 className={styles.heading}>Sua avaliação</h2>
          <RatingInput value={estado.nota} onChange={rate} disabled={busy} />
        </div>
        <div className={styles.buttons}>
          <button
            type="button"
            className={`${page.btn} ${estado.favorito ? page.btnPrimary : ""}`}
            aria-pressed={estado.favorito}
            disabled={busy}
            onClick={() => toggle("favorito", "favorites")}
          >
            {estado.favorito ? "♥ Nos favoritos" : "♡ Favoritar"}
          </button>
          <button
            type="button"
            className={`${page.btn} ${estado.watchlist ? page.btnPrimary : ""}`}
            aria-pressed={estado.watchlist}
            disabled={busy}
            onClick={() => toggle("watchlist", "watchlist")}
          >
            {estado.watchlist ? "✓ Na watchlist" : "+ Quero assistir"}
          </button>
          {estado.nota !== null && (
            <button type="button" className={page.btn} disabled={busy} onClick={removeRating}>
              Remover nota
            </button>
          )}
        </div>
      </div>

      <form onSubmit={saveReview} className={styles.review}>
        <label htmlFor="review">{estado.review_id ? "Sua review" : "Escreva uma review"}</label>
        <textarea
          id="review"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          maxLength={250}
          rows={3}
          placeholder={estado.nota === null ? "Escolha uma nota para poder publicar sua review." : "O que você achou do filme?"}
          disabled={estado.nota === null}
        />
        <div className={styles.reviewFooter}>
          <small>{texto.length}/250</small>
          <button
            type="submit"
            className={`${page.btn} ${page.btnPrimary}`}
            disabled={busy || estado.nota === null || !texto.trim() || texto.trim() === (estado.review ?? "")}
          >
            {estado.review_id ? "Atualizar review" : "Publicar review"}
          </button>
        </div>
      </form>
      {error && (
        <p role="alert" className={page.error}>
          {error}
        </p>
      )}
    </section>
  );
}
