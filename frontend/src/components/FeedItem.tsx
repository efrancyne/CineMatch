import Image from "next/image";
import Link from "next/link";
import type { ItemFeed } from "@/lib/types";
import { Avatar } from "./Avatar";
import { Stars } from "./Stars";
import styles from "./FeedItem.module.css";

export function FeedItem({ item }: { item: ItemFeed }) {
  const { autor, filme } = item;
  const data = new Date(item.rated_at).toLocaleDateString("pt-BR");

  return (
    <article className={styles.item}>
      <div className={styles.main}>
        <div className={styles.profile}>
          <Link href={`/usuarios/${autor.id}`} className={styles.ring} aria-label={`Perfil de ${autor.name}`}>
            <Avatar name={autor.name} src={autor.avatar_url} size={60} />
          </Link>
          <Link href={`/usuarios/${autor.id}`}>
            <p className={styles.name}>{autor.name}</p>
            <p className={styles.username}>@{autor.username}</p>
          </Link>
        </div>
        <Link href={`/reviews/${item.id}`} className={styles.reviewLink}>
          <p className={styles.review}>{item.content}</p>
        </Link>
      </div>

      <div className={styles.movie}>
        <time className={styles.date} dateTime={item.rated_at}>
          {data}
        </time>
        <Link href={`/filmes/${filme.id}`} className={styles.movieInfo}>
          <div className={styles.poster}>
            {filme.poster_url && (
              <Image src={filme.poster_url} alt={`Pôster de ${filme.title ?? "filme"}`} fill sizes="60px" />
            )}
          </div>
          <div>
            <p className={styles.title}>
              {filme.title}
              {filme.year && <span className={styles.year}>{filme.year}</span>}
            </p>
            <Stars value={item.rating} size={25.667} color="var(--gold)" />
          </div>
        </Link>
      </div>
    </article>
  );
}
