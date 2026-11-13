"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Comentario, FilmeDetalhe, ReviewDetalhe } from "@/lib/types";
import { Avatar } from "@/components/Avatar";
import { LikeButton } from "@/components/LikeButton";
import { Stars } from "@/components/Stars";
import page from "@/components/page.module.css";
import styles from "./review.module.css";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { token, user } = useAuth();
  const valid = /^\d+$/.test(id);
  const review = useApi<ReviewDetalhe>(valid ? `/reviews/${id}` : null);
  const movieId = review.data?.movie_id;
  const filme = useApi<FilmeDetalhe>(movieId !== undefined ? `/movies/${movieId}` : null);
  const [texto, setTexto] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!valid || review.error) {
    return (
      <main className={page.page}>
        <p className={page.muted}>{!valid ? "Review inválida." : review.error}</p>
      </main>
    );
  }
  if (!review.data) {
    return (
      <main className={page.page}>
        <p className={page.muted}>Carregando…</p>
      </main>
    );
  }

  const r = review.data;
  const isMine = user?.id === r.autor.id;

  async function addComment(e: React.FormEvent) {
    e.preventDefault();
    const content = texto.trim();
    if (!content) return;
    setBusy(true);
    setError(null);
    try {
      const novo = await api<Comentario>(`/reviews/${id}/comments`, { method: "POST", token, body: { content } });
      review.setData((old) => ({
        ...old,
        comentarios: old.comentarios + 1,
        lista_comentarios: [...old.lista_comentarios, novo],
      }));
      setTexto("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function removeComment(commentId: number) {
    setError(null);
    try {
      await api(`/comments/${commentId}`, { method: "DELETE", token });
      review.setData((old) => ({
        ...old,
        comentarios: old.comentarios - 1,
        lista_comentarios: old.lista_comentarios.filter((c) => c.id !== commentId),
      }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeReview() {
    if (!window.confirm("Excluir esta review? A sua nota para o filme, os comentários e as curtidas também serão removidos.")) return;
    setError(null);
    try {
      await api(`/ratings/${r.movie_id}`, { method: "DELETE", token });
      router.replace(`/filmes/${r.movie_id}`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className={`${page.page} ${styles.narrow}`}>
      {filme.data && (
        <Link href={`/filmes/${filme.data.id}`} className={styles.movie}>
          <span className={styles.poster}>
            {filme.data.poster_url && <Image src={filme.data.poster_url} alt="" fill sizes="60px" />}
          </span>
          <span>
            <strong>{filme.data.title}</strong>
            {filme.data.year && <small>{filme.data.year}</small>}
          </span>
        </Link>
      )}

      <article className={styles.review}>
        <header className={styles.author}>
          <Link href={`/usuarios/${r.autor.id}`} className={styles.who}>
            <Avatar name={r.autor.name} src={r.autor.avatar_url} size={56} />
            <span>
              <strong>{r.autor.name}</strong>
              <small>@{r.autor.username}</small>
            </span>
          </Link>
          <Stars value={r.rating} size={24} color="var(--gold)" />
          <time dateTime={r.rated_at}>{new Date(r.rated_at).toLocaleDateString("pt-BR")}</time>
        </header>
        <p className={styles.content}>{r.content}</p>
        <footer className={styles.footer}>
          <LikeButton reviewId={r.id} liked={r.curtida_por_mim} count={r.curtidas} />
          {isMine && (
            <button type="button" className={page.btn} onClick={removeReview}>
              Excluir review
            </button>
          )}
        </footer>
      </article>

      <section>
        <h2 className={styles.heading}>
          {r.comentarios === 1 ? "1 comentário" : `${r.comentarios} comentários`}
        </h2>
        <form onSubmit={addComment} className={styles.form}>
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            maxLength={144}
            placeholder="Escreva um comentário…"
            aria-label="Comentário"
          />
          <button type="submit" className={`${page.btn} ${page.btnPrimary}`} disabled={busy || !texto.trim()}>
            Comentar
          </button>
        </form>
        {error && <p className={page.error}>{error}</p>}
        <ul className={styles.comments}>
          {r.lista_comentarios.map((c) => (
            <li key={c.id}>
              <Link href={`/usuarios/${c.autor.id}`}>
                <Avatar name={c.autor.name} src={c.autor.avatar_url} size={36} />
              </Link>
              <div>
                <p>
                  <Link href={`/usuarios/${c.autor.id}`}>
                    <strong>{c.autor.name}</strong>
                  </Link>{" "}
                  <small>{new Date(c.created_at).toLocaleDateString("pt-BR")}</small>
                </p>
                <p>{c.content}</p>
              </div>
              {user?.id === c.autor.id && (
                <button type="button" className={styles.remove} onClick={() => removeComment(c.id)} aria-label="Excluir comentário">
                  Excluir
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
