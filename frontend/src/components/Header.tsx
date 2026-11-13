"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Avatar } from "./Avatar";
import styles from "./Header.module.css";

function Logo() {
  return (
    <Link href="/" className={styles.logo} aria-label="CineMatch">
      CineMatch<span className={styles.dot}>.</span>
    </Link>
  );
}

/** Header da landing e das telas de login/cadastro (Figma: Tela Inicial). */
export function PublicHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Logo />
        <nav className={styles.nav}>
          <Link href="/login" className={styles.link}>
            Fazer Login
          </Link>
          <Link href="/cadastro" className={styles.button}>
            Criar Conta
          </Link>
        </nav>
      </div>
    </header>
  );
}

/** Header da área logada (Figma: Feed). */
export function AppHeader() {
  const { user, logout } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const params = useSearchParams();
  const pathname = usePathname();

  function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = String(new FormData(e.currentTarget).get("q") ?? "").trim();
    router.push(q ? `/buscar?q=${encodeURIComponent(q)}` : "/buscar");
  }

  useEffect(() => {
    if (!moreOpen) return;
    const close = (e: Event) => {
      if (e.type === "keydown" || !moreRef.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [moreOpen]);

  const active = (href: string) => (pathname === href || pathname.startsWith(`${href}/`) ? styles.active : "");

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Logo />
        <nav className={styles.nav}>
          <Link href="/home" className={`${styles.link} ${active("/home")}`}>
            Home
          </Link>
          <Link href="/buscar" className={`${styles.link} ${active("/buscar")} ${active("/filmes")}`}>
            Filmes
          </Link>
          <div className={styles.more} ref={moreRef}>
            <button
              type="button"
              className={`${styles.link} ${styles.moreBtn}`}
              aria-haspopup="menu"
              aria-expanded={moreOpen}
              onClick={() => setMoreOpen((o) => !o)}
            >
              Mais
              <svg className={styles.chevron} viewBox="0 0 10 10" aria-hidden="true">
                <path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {moreOpen && (
              <div className={styles.menu} role="menu">
                <Link
                  href={user ? `/usuarios/${user.id}` : "/home"}
                  role="menuitem"
                  className={styles.onlyXs}
                  onClick={() => setMoreOpen(false)}
                >
                  Meu perfil
                </Link>
                <Link href="/listas" role="menuitem" onClick={() => setMoreOpen(false)}>
                  Minhas Listas
                </Link>
                <Link href="/amigos" role="menuitem" onClick={() => setMoreOpen(false)}>
                  Amigos
                </Link>
                <div className={styles.menuSep} role="separator" />
                <button type="button" role="menuitem" className={styles.menuDanger} onClick={logout}>
                  Sair
                </button>
              </div>
            )}
          </div>
          <form className={`${styles.search} ${styles.hideMd}`} onSubmit={onSearch} role="search">
            <Image src="/assets/search.png" alt="" width={24} height={24} />
            <input
              // key força o campo a refletir a busca atual ao navegar
              key={pathname === "/buscar" ? params.get("q") ?? "" : ""}
              name="q"
              type="search"
              placeholder="Pesquisa"
              aria-label="Pesquisar filmes"
              defaultValue={pathname === "/buscar" ? params.get("q") ?? "" : ""}
            />
          </form>
          <Link href={user ? `/usuarios/${user.id}` : "/home"} className={`${styles.userButton} ${styles.hideXs}`} aria-label="Meu perfil" title="Meu perfil">
            <Avatar name={user?.name ?? ""} src={user?.avatar_url} size={45} />
          </Link>
        </nav>
      </div>
    </header>
  );
}
