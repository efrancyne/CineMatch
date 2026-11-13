"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { usePaged } from "@/lib/hooks";
import type { AvaliacaoComFilme, FilmeResumo } from "@/lib/types";
import { AvaliacaoRow } from "@/components/AvaliacaoRow";
import { MovieGrid } from "@/components/MovieGrid";
import { PagedFooter } from "@/components/PagedFooter";
import { Tabs } from "@/components/Tabs";
import page from "@/components/page.module.css";

type Aba = "favoritos" | "watchlist" | "historico";

const TABS: { id: Aba; label: string }[] = [
  { id: "favoritos", label: "Favoritos" },
  { id: "watchlist", label: "Quero assistir" },
  { id: "historico", label: "Histórico de avaliações" },
];

const VAZIO: Record<Aba, string> = {
  favoritos: "Você ainda não favoritou nenhum filme. Abra um filme e toque em “Favoritar”.",
  watchlist: "Sua lista está vazia. Abra um filme e toque em “Quero assistir”.",
  historico: "Você ainda não avaliou nenhum filme.",
};

export default function ListasPage() {
  const { user } = useAuth();
  const [aba, setAba] = useState<Aba>("favoritos");
  const id = user?.id;

  const filmesPath =
    id === undefined ? null : aba === "favoritos" ? `/users/${id}/favorites` : aba === "watchlist" ? "/users/me/watchlist" : null;
  const historicoPath = id !== undefined && aba === "historico" ? `/users/${id}/ratings` : null;

  const filmes = usePaged<FilmeResumo>(filmesPath);
  const historico = usePaged<AvaliacaoComFilme>(historicoPath);
  const lista = aba === "historico" ? historico : filmes;

  return (
    <main className={page.page}>
      <h1 className={page.title}>Minhas Listas</h1>
      <Tabs tabs={TABS} value={aba} onChange={setAba} />
      {aba === "historico" ? (
        <div>
          {historico.itens.map((a) => (
            <AvaliacaoRow key={a.movie_id} item={a} />
          ))}
        </div>
      ) : (
        <MovieGrid filmes={filmes.itens} />
      )}
      <PagedFooter
        loading={lista.loading}
        error={lista.error}
        empty={lista.itens.length === 0}
        emptyText={VAZIO[aba]}
        hasMore={lista.hasMore}
        loadingMore={lista.loadingMore}
        onMore={lista.loadMore}
      />
    </main>
  );
}
