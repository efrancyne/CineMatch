import Image from "next/image";
import Link from "next/link";
import type { AvaliacaoComFilme } from "@/lib/types";
import { Stars } from "./Stars";
import styles from "./AvaliacaoRow.module.css";

/** Uma linha do histórico de avaliações (RF06). */
export function AvaliacaoRow({ item }: { item: AvaliacaoComFilme }) {
  const { filme } = item;
  return (
    <article className={styles.row}>
      <Link href={`/filmes/${filme.id}`} className={styles.poster}>
        {filme.poster_url && <Image src={filme.poster_url} alt="" fill sizes="60px" />}
      </Link>
      <div className={styles.body}>
        <Link href={`/filmes/${filme.id}`} className={styles.title}>
          {filme.title}
          {filme.year && <span>{filme.year}</span>}
        </Link>
        <Stars value={item.rating} size={20} color="var(--gold)" />
        {item.review && (
          <p className={styles.review}>
            {item.review_id ? <Link href={`/reviews/${item.review_id}`}>{item.review}</Link> : item.review}
          </p>
        )}
      </div>
      <time className={styles.date} dateTime={item.rated_at}>
        {new Date(item.rated_at).toLocaleDateString("pt-BR")}
      </time>
    </article>
  );
}
