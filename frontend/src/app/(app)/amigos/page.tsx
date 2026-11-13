"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePaged } from "@/lib/hooks";
import type { UsuarioPublico } from "@/lib/types";
import { PagedFooter } from "@/components/PagedFooter";
import { PersonRow } from "@/components/PersonRow";
import { Tabs } from "@/components/Tabs";
import page from "@/components/page.module.css";

type Aba = "seguindo" | "seguidores";

const TABS: { id: Aba; label: string }[] = [
  { id: "seguindo", label: "Seguindo" },
  { id: "seguidores", label: "Seguidores" },
];

export default function AmigosPage() {
  const { token, user } = useAuth();
  const [aba, setAba] = useState<Aba>("seguindo");
  const [error, setError] = useState<string | null>(null);
  const lista = usePaged<UsuarioPublico>(user ? `/users/${user.id}/${aba === "seguindo" ? "following" : "followers"}` : null);

  async function unfollow(id: number) {
    setError(null);
    try {
      await api(`/follows/${id}`, { method: "DELETE", token });
      lista.setItens((itens) => itens.filter((u) => u.id !== id));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className={page.page}>
      <h1 className={page.title}>Amigos</h1>
      <Tabs tabs={TABS} value={aba} onChange={setAba} />
      {error && <p className={page.error}>{error}</p>}
      <div>
        {lista.itens.map((u) => (
          <PersonRow
            key={u.id}
            user={u}
            action={
              aba === "seguindo" ? (
                <button type="button" className={page.btn} onClick={() => unfollow(u.id)}>
                  Deixar de seguir
                </button>
              ) : undefined
            }
          />
        ))}
      </div>
      <PagedFooter
        loading={lista.loading}
        error={lista.error}
        empty={lista.itens.length === 0}
        emptyText={
          aba === "seguindo"
            ? "Você ainda não segue ninguém. Abra um filme, veja as reviews e entre no perfil de quem escreveu para seguir."
            : "Ninguém segue você ainda."
        }
        hasMore={lista.hasMore}
        loadingMore={lista.loadingMore}
        onMore={lista.loadMore}
      />
    </main>
  );
}
