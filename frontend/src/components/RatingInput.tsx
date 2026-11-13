"use client";

import { useState } from "react";
import { Stars } from "./Stars";
import styles from "./RatingInput.module.css";

interface Props {
  value: number | null;
  onChange: (value: number) => void;
  disabled?: boolean;
  size?: number;
}

/** Nota de 0,5 a 5 em passos de meia estrela: cada estrela tem duas áreas de clique. */
export function RatingInput({ value, onChange, disabled, size = 40 }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  return (
    <div className={styles.wrap} style={{ width: size * 5, height: size }} onMouseLeave={() => setHover(null)}>
      <Stars value={hover ?? value ?? 0} size={size} color="var(--gold)" />
      <div className={styles.zones}>
        {Array.from({ length: 10 }, (_, i) => {
          const v = (i + 1) / 2;
          return (
            <button
              key={v}
              type="button"
              disabled={disabled}
              aria-label={`${v.toLocaleString("pt-BR")} estrelas`}
              aria-pressed={value === v}
              onMouseEnter={() => setHover(v)}
              onFocus={() => setHover(v)}
              onBlur={() => setHover(null)}
              onClick={() => onChange(v)}
            />
          );
        })}
      </div>
    </div>
  );
}
