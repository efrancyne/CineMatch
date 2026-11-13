"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi, usePaged } from "@/lib/hooks";
import type { AvaliacaoComFilme, FilmeResumo, Review, UsuarioPerfil } from "@/lib/types";
import { Avatar } from "@/components/Avatar";
import { AvaliacaoRow } from "@/components/AvaliacaoRow";
import { MovieGrid } from "@/components/MovieGrid";
import { PagedFooter } from "@/components/PagedFooter";
import { ProfileEditor } from "@/components/ProfileEditor";
import { ReviewCard } from "@/components/ReviewCard";
import { Tabs } from "@/components/Tabs";
import page from "@/components/page.module.css";
import styles from "./perfil.module.css";

type Aba = "avaliacoes" | "reviews" | "favoritos";

const TABS: { id: Aba; label: string }[] = [
  { id: "avaliacoes", label: "Avaliações" },
  { id: "reviews", label: "Reviews" },
  { id: "favoritos", label: "Favoritos" },
];

export default function PerfilPage() {
  const { id } = useParams<{ id: string }>();
  const { token, user: me, logout } = useAuth();
  const valid = /^\d+$/.test(id);
  const isMe = me?.id === Number(id);

  const perfil = useApi<UsuarioPerfil>(valid ? `/users/${id}` : null);
  const segue = useApi<{ seguindo: boolean }>(valid && me && !isMe ? `/users/me/following/${id}` : null);
  const [aba, setAba] = useState<Aba>("avaliacoes");
  const [editando, setEditando] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const avaliacoes = usePaged<AvaliacaoComFilme>(valid && aba === "avaliacoes" ? `/users/${id}/ratings` : null);
  const reviews = usePaged<Review>(valid && aba === "reviews" ? `/users/${id}/reviews` : null);
  const favoritos = usePaged<FilmeResumo>(valid && aba === "favoritos" ? `/users/${id}/favorites` : null);
  const lista = aba === "avaliacoes" ? avaliacoes : aba === "reviews" ? reviews : favoritos;

  async function toggleFollow() {
    if (!segue.data) return;
    const seguir = !segue.data.seguindo;
    setBusy(true);
    setError(null);
    try {
      await api(`/follows/${id}`, { method: seguir ? "POST" : "DELETE", token });
      segue.setData(() => ({ seguindo: seguir }));
      perfil.setData((p) => ({ ...p, seguidores: p.seguidores + (seguir ? 1 : -1) }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!valid || perfil.error) {
    return (
      <main className={page.page}>
        <p className={page.muted}>{!valid ? "Perfil inválido." : perfil.error}</p>
      </main>
    );
  }
  if (!perfil.data) {
    return (
      <main className={page.page}>
        <p className={page.muted}>Carregando…</p>
      </main>
    );
  }

  const p = perfil.data;
  const vazio = {
    avaliacoes: isMe ? "Você ainda não avaliou nenhum filme." : "Nenhuma avaliação ainda.",
    reviews: isMe ? "Você ainda não escreveu nenhuma review." : "Nenhuma review ainda.",
    favoritos: isMe ? "Você ainda não favoritou nenhum filme." : "Nenhum favorito ainda.",
  }[aba];

  return (
    <main className={page.page}>
      <section className={styles.header}>
        <Avatar name={p.name} src={p.avatar_url} size={96} />
        <div className={styles.info}>
          <h1 className={styles.name}>{p.name}</h1>
          <p className={styles.username}>@{p.username}</p>
          {p.bio && <p className={styles.bio}>{p.bio}</p>}
          <ul className={styles.stats}>
            <li>
              <strong>{p.avaliacoes}</strong> avaliações
            </li>
            <li>
              <strong>{p.seguidores}</strong> seguidores
            </li>
            <li>
              <strong>{p.seguindo}</strong> seguindo
            </li>
          </ul>
        </div>
        <div className={styles.actions}>
          {isMe ? (
            <>
              <button type="button" className={page.btn} onClick={() => setEditando((v) => !v)}>
                Editar perfil
              </button>
              <button type="button" className={page.btn} onClick={logout}>
                Sair
              </button>
            </>
          ) : (
            segue.data && (
              <button
                type="button"
                className={`${page.btn} ${segue.data.seguindo ? "" : page.btnPrimary}`}
                disabled={busy}
                onClick={toggleFollow}
              >
                {segue.data.seguindo ? "Seguindo" : "Seguir"}
              </button>
            )
          )}
        </div>
      </section>
      {error && <p className={page.error}>{error}</p>}

      {isMe && editando && me && <ProfileEditor me={me} onSaved={perfil.reload} onClose={() => setEditando(false)} />}

      <Tabs tabs={TABS} value={aba} onChange={setAba} />
      {aba === "avaliacoes" && (
        <div>
          {avaliacoes.itens.map((a) => (
            <AvaliacaoRow key={a.movie_id} item={a} />
          ))}
        </div>
      )}
      {aba === "reviews" && (
        <div>
          {reviews.itens.map((r) => (
            <ReviewCard key={r.id} review={r} showMovieLink />
          ))}
        </div>
      )}
      {aba === "favoritos" && <MovieGrid filmes={favoritos.itens} />}
      <PagedFooter
        loading={lista.loading}
        error={lista.error}
        empty={lista.itens.length === 0}
        emptyText={vazio}
        hasMore={lista.hasMore}
        loadingMore={lista.loadingMore}
        onMore={lista.loadMore}
      />
    </main>
  );
}
