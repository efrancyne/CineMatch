import type { CSSProperties } from "react";
import styles from "./Stars.module.css";

interface Props {
  /** nota de 0 a 5 (aceita meios pontos e médias) */
  value: number;
  /** lado de cada estrela em px (design: 25.667 grande, 21 pequena) */
  size?: number;
  color?: string;
}

export function Stars({ value, size = 21, color = "var(--text)" }: Props) {
  return (
    <span
      className={styles.stars}
      role="img"
      aria-label={`Nota ${value.toFixed(1)} de 5`}
      style={{ "--size": `${size}px`, "--color": color } as CSSProperties}
    >
      {[0, 1, 2, 3, 4].map((i) => {
        const fill = Math.min(1, Math.max(0, value - i));
        return <span key={i} className={styles.star} style={{ "--fill": `${fill * 100}%` } as CSSProperties} />;
      })}
    </span>
  );
}
