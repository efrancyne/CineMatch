"use client";

import { useState } from "react";
import Image from "next/image";
import { useParams } from "next/navigation";
import { useApi, usePaged } from "@/lib/hooks";
import type { EstadoFilme, FilmeDetalhe, FilmeResumo, Review } from "@/lib/types";
import { MovieGrid } from "@/components/MovieGrid";
import { MyMovieState } from "@/components/MyMovieState";
import { PagedFooter } from "@/components/PagedFooter";
import { ReviewCard } from "@/components/ReviewCard";
import { Stars } from "@/components/Stars";
import page from "@/components/page.module.css";
import styles from "./filme.module.css";

export default function FilmePage() {
  const { id } = useParams<{ id: string }>();
  const valid = /^\d+$/.test(id);
  const filme = useApi<FilmeDetalhe>(valid ? `/movies/${id}` : null);
  const estado = useApi<EstadoFilme>(valid ? `/users/me/movies/${id}` : null);
  const similares = useApi<FilmeResumo[]>(valid ? `/movies/${id}/similar?k=12` : null);
  const [reviewsVersion, setReviewsVersion] = useState(0);
  const reviews = usePaged<Review>(valid ? `/movies/${id}/reviews?v=${reviewsVersion}` : null, 10);

  if (!valid || filme.error) {
    return (
      <main className={page.page}>
        <p className={page.muted}>{!valid ? "Filme inválido." : filme.error}</p>
      </main>
    );
  }
  if (!filme.data) {
    return (
      <main className={page.page}>
        <p className={page.muted}>Carregando…</p>
      </main>
    );
  }

  const f = filme.data;
  const ext = f.detalhes_externos;
  const trailer = ext?.videos.find((v) => v.tipo === "Trailer") ?? ext?.videos[0];

  return (
    <main className={page.page}>
      <section className={styles.hero}>
        <div className={styles.poster}>
          {f.poster_url ? (
            <Image src={f.poster_url} alt={`Pôster de ${f.title}`} fill sizes="280px" priority />
          ) : (
            <span className={styles.noPoster}>{f.title}</span>
          )}
        </div>
        <div className={styles.info}>
          <h1 className={styles.title}>
            {f.title}
            {f.year && <span className={styles.year}>{f.year}</span>}
          </h1>
          {ext?.titulo_original && ext.titulo_original !== f.title && (
            <p className={page.muted}>Título original: {ext.titulo_original}</p>
          )}
          <ul className={styles.chips}>
            {f.generos.map((g) => (
              <li key={g} className={styles.chip}>
                {g}
              </li>
            ))}
          </ul>
          <p className={styles.meta}>
            {[
              f.release_date && new Date(f.release_date + "T12:00:00").toLocaleDateString("pt-BR"),
              ext?.duracao_minutos && `${Math.floor(ext.duracao_minutos / 60)}h ${ext.duracao_minutos % 60}min`,
              ext?.diretores.length ? `Direção: ${ext.diretores.join(", ")}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <div className={styles.rating}>
            {f.media !== null ? (
              <>
                <strong>{f.media.toFixed(1)}</strong>
                <Stars value={f.media} size={26} color="var(--gold)" />
                <span>
                  {f.avaliacoes} {f.avaliacoes === 1 ? "avaliação" : "avaliações"}
                </span>
              </>
            ) : (
              <span>Ainda sem avaliações</span>
            )}
          </div>
          <p className={styles.overview}>{f.overview ?? "Sem sinopse disponível."}</p>
          {trailer && (
            <a
              className={`${page.btn} ${styles.trailer}`}
              href={`https://www.youtube.com/watch?v=${trailer.youtube_key}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              ▶ Assistir ao trailer
            </a>
          )}
        </div>
      </section>

      {estado.data ? (
        <MyMovieState
          movieId={f.id}
          estado={estado.data}
          onChange={estado.setData}
          onReviewSaved={() => setReviewsVersion((v) => v + 1)}
        />
      ) : estado.error ? (
        <p className={page.error}>{estado.error}</p>
      ) : null}

      {ext && ext.elenco.length > 0 && (
        <section>
          <h2 className={styles.section}>Elenco</h2>
          <ul className={styles.cast}>
            {ext.elenco.slice(0, 12).map((p) => (
              <li key={`${p.nome}-${p.personagem}`}>
                <div className={styles.castPhoto}>
                  {p.foto_url && <Image src={p.foto_url} alt="" fill sizes="96px" />}
                </div>
                <strong>{p.nome}</strong>
                {p.personagem && <small>{p.personagem}</small>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {ext && ext.keywords.length > 0 && (
        <ul className={styles.chips} aria-label="Palavras-chave">
          {ext.keywords.slice(0, 12).map((k) => (
            <li key={k} className={styles.chip}>
              {k}
            </li>
          ))}
        </ul>
      )}

      <section>
        <h2 className={styles.section}>Reviews</h2>
        <div>
          {reviews.itens.map((r) => (
            <ReviewCard key={r.id} review={r} />
          ))}
        </div>
        <PagedFooter
          loading={reviews.loading}
          error={reviews.error}
          empty={reviews.itens.length === 0}
          emptyText="Ninguém escreveu uma review ainda. Seja a primeira pessoa!"
          hasMore={reviews.hasMore}
          loadingMore={reviews.loadingMore}
          onMore={reviews.loadMore}
        />
      </section>

      {similares.data && similares.data.length > 0 && (
        <section>
          <h2 className={styles.section}>Quem gostou deste também gostou de</h2>
          <MovieGrid filmes={similares.data} />
        </section>
      )}
    </main>
  );
}
