import Image from "next/image";
import Link from "next/link";
import type { FilmeResumo } from "@/lib/types";
import { ScrollRow } from "./ScrollRow";
import { Stars } from "./Stars";
import styles from "./MovieCarousel.module.css";

// O Figma dá a cada card um degradê tirado da cor do pôster.
// A API não devolve cores, então alternamos as três paletas do design.
const PALETTES: [string, string][] = [
  ["#a7b376", "#2a352e"],
  ["#5592b4", "#050413"],
  ["#f1563f", "#f0a148"],
];

function Poster({ filme, sizes }: { filme: FilmeResumo; sizes: string }) {
  if (!filme.poster_url) {
    return <div className={styles.noPoster}>{filme.title}</div>;
  }
  return (
    <Image src={filme.poster_url} alt={`Pôster de ${filme.title ?? "filme"}`} fill sizes={sizes} className={styles.poster} />
  );
}

function Rating({ media, large }: { media: number | null; large?: boolean }) {
  if (media === null) return null;
  return (
    <div className={`${styles.rating} ${large ? styles.ratingLg : ""}`}>
      <span>{media.toFixed(1)}</span>
      <Stars value={media} size={large ? 25.667 : 21} />
    </div>
  );
}

export function MovieCarousel({ filmes }: { filmes: FilmeResumo[] }) {
  if (filmes.length === 0) return null;
  const [destaque, ...demais] = filmes;

  return (
    <ScrollRow className={styles.carousel}>
      <li className={styles.featured}>
        <Link href={`/filmes/${destaque.id}`} className={styles.cover} aria-label={destaque.title ?? "Ver filme"} />
        <Poster filme={destaque} sizes="600px" />
        {/* triângulo translúcido do design (exportado do Figma) */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/assets/featured-overlay.svg" alt="" className={styles.overlay} />
        <div className={styles.featuredText}>
          <h3 className={styles.featuredTitle}>{destaque.title}</h3>
          <Rating media={destaque.media} large />
        </div>
      </li>

      {demais.map((filme, i) => {
        const [from, to] = PALETTES[i % PALETTES.length];
        return (
          <li key={filme.id} className={styles.card}>
            <Link href={`/filmes/${filme.id}`} className={styles.cover} aria-label={filme.title ?? "Ver filme"} />
            <Poster filme={filme} sizes="268px" />
            <div className={styles.footer} style={{ background: `linear-gradient(to bottom, ${from}, ${to})` }}>
              <h3 className={styles.cardTitle}>{filme.title}</h3>
              <Rating media={filme.media} />
            </div>
          </li>
        );
      })}
    </ScrollRow>
  );
}
