import Link from "next/link";
import type { Review } from "@/lib/types";
import { Avatar } from "./Avatar";
import { LikeButton } from "./LikeButton";
import { Stars } from "./Stars";
import styles from "./ReviewCard.module.css";

export function ReviewCard({ review, showMovieLink }: { review: Review; showMovieLink?: boolean }) {
  const { autor } = review;
  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <Link href={`/usuarios/${autor.id}`} className={styles.author}>
          <Avatar name={autor.name} src={autor.avatar_url} size={44} />
          <span>
            <strong>{autor.name}</strong>
            <small>@{autor.username}</small>
          </span>
        </Link>
        <Stars value={review.rating} size={20} color="var(--gold)" />
        <time className={styles.date} dateTime={review.rated_at}>
          {new Date(review.rated_at).toLocaleDateString("pt-BR")}
        </time>
      </header>
      <p className={styles.content}>{review.content}</p>
      <footer className={styles.footer}>
        <LikeButton reviewId={review.id} liked={review.curtida_por_mim} count={review.curtidas} />
        <Link href={`/reviews/${review.id}`} className={styles.comments}>
          {review.comentarios === 1 ? "1 comentário" : `${review.comentarios} comentários`}
        </Link>
        {showMovieLink && (
          <Link href={`/filmes/${review.movie_id}`} className={styles.comments}>
            Ver filme →
          </Link>
        )}
      </footer>
    </article>
  );
}
