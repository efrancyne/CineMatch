"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useApi, usePaged } from "@/lib/hooks";
import type { FilmeResumo, Genero } from "@/lib/types";
import { MovieGrid } from "@/components/MovieGrid";
import { PagedFooter } from "@/components/PagedFooter";
import page from "@/components/page.module.css";
import styles from "./buscar.module.css";

const FILTROS = ["q", "genero", "ano", "nota_minima"] as const;

function Busca() {
  const router = useRouter();
  const params = useSearchParams();
  const generos = useApi<Genero[]>("/genres");

  const query = new URLSearchParams();
  for (const k of FILTROS) {
    const v = params.get(k);
    if (v) query.set(k, v);
  }
  const qs = query.toString();
  const resultados = usePaged<FilmeResumo>(`/movies${qs ? `?${qs}` : ""}`, 24);
  const filtrando = qs !== "";

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const next = new URLSearchParams();
    for (const k of FILTROS) {
      const v = String(form.get(k) ?? "").trim();
      if (v) next.set(k, v);
    }
    router.replace(`/buscar${next.size ? `?${next}` : ""}`);
  }

  // key: o formulário reinicia quando a URL muda (ex.: busca feita pelo header)
  return (
    <main className={page.page}>
      <h1 className={page.title}>{filtrando ? "Resultados" : "Explorar filmes"}</h1>

      <form key={qs} className={styles.form} onSubmit={onSubmit}>
        <label>
          Título
          <input name="q" defaultValue={params.get("q") ?? ""} maxLength={100} placeholder="Ex.: Toy Story" />
        </label>
        <label>
          Gênero
          <select name="genero" defaultValue={params.get("genero") ?? ""}>
            <option value="">Todos</option>
            {generos.data?.map((g) => (
              <option key={g.id} value={g.name}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Ano
          <input name="ano" type="number" min={1800} max={2200} defaultValue={params.get("ano") ?? ""} placeholder="Ex.: 1994" />
        </label>
        <label>
          Nota mínima
          <select name="nota_minima" defaultValue={params.get("nota_minima") ?? ""}>
            <option value="">Qualquer</option>
            {[2, 3, 3.5, 4, 4.5].map((n) => (
              <option key={n} value={n}>
                {n.toLocaleString("pt-BR")}+ estrelas
              </option>
            ))}
          </select>
        </label>
        <div className={styles.actions}>
          <button type="submit" className={`${page.btn} ${page.btnPrimary}`}>
            Buscar
          </button>
          {filtrando && (
            <button type="button" className={page.btn} onClick={() => router.replace("/buscar")}>
              Limpar
            </button>
          )}
        </div>
      </form>

      {!resultados.loading && !resultados.error && resultados.total > 0 && (
        <p className={page.muted}>
          {resultados.total.toLocaleString("pt-BR")} {resultados.total === 1 ? "filme" : "filmes"}
          {!filtrando && " — dos mais para os menos avaliados"}
        </p>
      )}
      <MovieGrid filmes={resultados.itens} />
      <PagedFooter
        loading={resultados.loading}
        error={resultados.error}
        empty={resultados.itens.length === 0}
        emptyText="Nenhum filme encontrado com esses filtros."
        hasMore={resultados.hasMore}
        loadingMore={resultados.loadingMore}
        onMore={resultados.loadMore}
      />
    </main>
  );
}

export default function BuscarPage() {
  return (
    <Suspense fallback={null}>
      <Busca />
    </Suspense>
  );
}
