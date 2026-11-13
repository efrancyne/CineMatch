"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Genero, UsuarioProprio } from "@/lib/types";
import page from "./page.module.css";
import styles from "./ProfileEditor.module.css";

/** Edição do próprio perfil (RF07): nome, bio, foto e gêneros preferidos. */
export function ProfileEditor({ me, onSaved, onClose }: { me: UsuarioProprio; onSaved: () => void; onClose: () => void }) {
  const { token, refreshUser } = useAuth();
  const generos = useApi<Genero[]>("/genres");
  const [selecionados, setSelecionados] = useState<string[]>(me.generos);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(nome: string) {
    setSelecionados((s) => (s.includes(nome) ? s.filter((g) => g !== nome) : [...s, nome]));
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await api<UsuarioProprio>("/users/me", {
        method: "PATCH",
        token,
        body: {
          name: String(form.get("name") ?? "").trim(),
          bio: String(form.get("bio") ?? "").trim(),
          avatar_url: String(form.get("avatar_url") ?? "").trim(),
        },
      });
      const atualizado = await api<UsuarioProprio>("/users/me/genres", {
        method: "PUT",
        token,
        body: { generos: selecionados },
      });
      refreshUser(atualizado);
      onSaved();
      onClose();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <label>
        Nome
        <input name="name" defaultValue={me.name} required maxLength={100} />
      </label>
      <label>
        Bio <small>(até 144 caracteres)</small>
        <textarea name="bio" defaultValue={me.bio ?? ""} maxLength={144} rows={2} />
      </label>
      <label>
        URL da foto
        <input name="avatar_url" type="url" defaultValue={me.avatar_url ?? ""} maxLength={500} placeholder="https://…" />
      </label>
      <fieldset>
        <legend>Gêneros preferidos</legend>
        <div className={styles.chips}>
          {generos.data?.map((g) => (
            <button
              key={g.id}
              type="button"
              aria-pressed={selecionados.includes(g.name)}
              className={`${page.chip} ${selecionados.includes(g.name) ? page.chipOn : ""}`}
              onClick={() => toggle(g.name)}
            >
              {g.name}
            </button>
          ))}
        </div>
      </fieldset>
      {error && (
        <p role="alert" className={page.error}>
          {error}
        </p>
      )}
      <div className={styles.actions}>
        <button type="submit" className={`${page.btn} ${page.btnPrimary}`} disabled={busy}>
          {busy ? "Salvando…" : "Salvar"}
        </button>
        <button type="button" className={page.btn} onClick={onClose} disabled={busy}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
