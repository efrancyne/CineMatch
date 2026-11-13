import Image from "next/image";
import Link from "next/link";
import type { FilmeResumo } from "@/lib/types";
import { Stars } from "./Stars";
import styles from "./MovieGrid.module.css";

export function MovieGrid({ filmes }: { filmes: FilmeResumo[] }) {
  return (
    <ul className={styles.grid}>
      {filmes.map((f) => (
        <li key={f.id}>
          <Link href={`/filmes/${f.id}`} className={styles.card}>
            <div className={styles.poster}>
              {f.poster_url ? (
                <Image src={f.poster_url} alt="" fill sizes="200px" />
              ) : (
                <span className={styles.noPoster}>{f.title}</span>
              )}
            </div>
            <p className={styles.title}>{f.title}</p>
            <p className={styles.meta}>
              {f.year ?? "—"}
              {f.media !== null && (
                <>
                  <Stars value={f.media} size={14} color="var(--gold)" />
                  <span>{f.media.toFixed(1)}</span>
                </>
              )}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
