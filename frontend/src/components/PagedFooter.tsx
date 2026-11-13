import styles from "./Section.module.css";

interface Props {
  loading: boolean;
  error?: string;
  empty: boolean;
  emptyText: string;
  hasMore: boolean;
  loadingMore: boolean;
  onMore: () => void;
}

/** Estados comuns de listas paginadas: carregando, erro, vazio e "Ver mais". */
export function PagedFooter({ loading, error, empty, emptyText, hasMore, loadingMore, onMore }: Props) {
  if (error) return <p className={styles.message}>{error}</p>;
  if (loading) return <p className={styles.message}>Carregando…</p>;
  if (empty) return <p className={styles.message}>{emptyText}</p>;
  if (!hasMore) return null;
  return (
    <button type="button" className={styles.more} onClick={onMore} disabled={loadingMore}>
      {loadingMore ? "Carregando…" : "Ver mais"}
    </button>
  );
}
