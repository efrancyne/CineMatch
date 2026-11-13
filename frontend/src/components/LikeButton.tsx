"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import styles from "./LikeButton.module.css";

interface Props {
  reviewId: number;
  liked: boolean;
  count: number;
  onChange?: (liked: boolean, count: number) => void;
}

export function LikeButton({ reviewId, liked: initialLiked, count: initialCount, onChange }: Props) {
  const { token } = useAuth();
  const [state, setState] = useState({ liked: initialLiked, count: initialCount });
  const [busy, setBusy] = useState(false);

  async function toggle() {
    if (busy) return;
    const next = { liked: !state.liked, count: state.count + (state.liked ? -1 : 1) };
    setState(next); // otimista
    setBusy(true);
    try {
      await api(`/reviews/${reviewId}/like`, { method: next.liked ? "POST" : "DELETE", token });
      onChange?.(next.liked, next.count);
    } catch {
      setState(state); // desfaz
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className={`${styles.like} ${state.liked ? styles.on : ""}`}
      onClick={toggle}
      aria-pressed={state.liked}
      aria-label={state.liked ? "Descurtir" : "Curtir"}
    >
      <span aria-hidden>{state.liked ? "♥" : "♡"}</span> {state.count}
    </button>
  );
}
