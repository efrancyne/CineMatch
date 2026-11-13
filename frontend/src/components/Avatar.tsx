import styles from "./Avatar.module.css";

interface Props {
  name: string;
  src?: string | null;
  size?: number;
}

export function Avatar({ name, src, size = 60 }: Props) {
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <span className={styles.avatar} style={{ width: size, height: size, fontSize: size * 0.42 }}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element -- URL arbitrária vinda do perfil do usuário
        <img src={src} alt={name} width={size} height={size} className={styles.img} />
      ) : (
        <span aria-hidden>{initial}</span>
      )}
    </span>
  );
}
