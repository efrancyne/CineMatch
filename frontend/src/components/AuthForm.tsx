"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Genero } from "@/lib/types";
import page from "./page.module.css";
import styles from "./AuthForm.module.css";

export function AuthForm({ mode }: { mode: "login" | "cadastro" }) {
  const { token, ready, login, register } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [generos, setGeneros] = useState<Genero[]>([]);
  const [escolhidos, setEscolhidos] = useState<string[]>([]);
  const isLogin = mode === "login";

  // gêneros do onboarding: ajudam as recomendações de quem ainda não avaliou nada
  useEffect(() => {
    if (isLogin) return;
    const controller = new AbortController();
    api<Genero[]>("/genres", { signal: controller.signal })
      .then(setGeneros)
      .catch(() => {});
    return () => controller.abort();
  }, [isLogin]);

  useEffect(() => {
    if (ready && token) router.replace("/home");
  }, [ready, token, router]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const get = (k: string) => String(form.get(k) ?? "").trim();
    setError(null);
    setSubmitting(true);
    try {
      if (isLogin) await login(get("username"), String(form.get("password") ?? ""));
      else
        await register({
          username: get("username"),
          name: get("name"),
          email: get("email"),
          password: String(form.get("password") ?? ""),
          generos: escolhidos,
        });
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <h1 className={styles.title}>{isLogin ? "Fazer Login" : "Criar Conta"}</h1>

      {!isLogin && (
        <label className={styles.field}>
          Nome
          <input name="name" required maxLength={100} autoComplete="name" />
        </label>
      )}
      <label className={styles.field}>
        {isLogin ? "Usuário ou e-mail" : "Usuário"}
        <input
          name="username"
          required
          {...(!isLogin && { minLength: 3, maxLength: 30, pattern: "[A-Za-z0-9_.]+", title: "Letras, números, _ e ." })}
          autoComplete="username"
        />
      </label>
      {!isLogin && (
        <label className={styles.field}>
          E-mail
          <input name="email" type="email" required autoComplete="email" />
        </label>
      )}
      <label className={styles.field}>
        Senha
        <input
          name="password"
          type="password"
          required
          minLength={isLogin ? undefined : 8}
          maxLength={128}
          autoComplete={isLogin ? "current-password" : "new-password"}
        />
      </label>

      {!isLogin && generos.length > 0 && (
        <fieldset className={styles.genres}>
          <legend>Quais gêneros você curte? <small>(opcional)</small></legend>
          <div className={styles.chips}>
            {generos.map((g) => {
              const on = escolhidos.includes(g.name);
              return (
                <button
                  key={g.id}
                  type="button"
                  aria-pressed={on}
                  className={`${page.chip} ${on ? page.chipOn : ""}`}
                  onClick={() => setEscolhidos((c) => (on ? c.filter((n) => n !== g.name) : [...c, g.name]))}
                >
                  {g.name}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}

      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}

      <button type="submit" className={styles.submit} disabled={submitting}>
        {submitting ? "Aguarde…" : isLogin ? "Entrar" : "Criar Conta"}
      </button>

      <p className={styles.switch}>
        {isLogin ? (
          <>
            Ainda não tem conta? <Link href="/cadastro">Criar Conta</Link>
          </>
        ) : (
          <>
            Já tem conta? <Link href="/login">Fazer Login</Link>
          </>
        )}
      </p>
    </form>
  );
}
