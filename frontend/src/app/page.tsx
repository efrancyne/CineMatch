import Image from "next/image";
import Link from "next/link";
import { api } from "@/lib/api";
import type { FilmeResumo, Pagina } from "@/lib/types";
import { PublicHeader } from "@/components/Header";
import { MovieCarousel } from "@/components/MovieCarousel";
import { RedirectIfLoggedIn } from "@/components/RedirectIfLoggedIn";
import styles from "./landing.module.css";

// Renderiza sob demanda: o build não depende da API e um erro nunca fica "congelado" na página.
export const dynamic = "force-dynamic";

async function filmesPopulares(): Promise<FilmeResumo[]> {
  try {
    // /movies já ordena do mais avaliado para o menos
    const pagina = await api<Pagina<FilmeResumo>>("/movies?tamanho=10", { revalidate: 300 });
    return pagina.itens;
  } catch {
    return [];
  }
}

export default async function LandingPage() {
  const filmes = await filmesPopulares();

  return (
    <>
      <RedirectIfLoggedIn />
      <PublicHeader />
      <main className={styles.main}>
        <section className={styles.hero}>
          <Image src="/assets/hero.png" alt="" fill priority sizes="(max-width: 1440px) 100vw, 1338px" className={styles.heroImage} />
          <div className={styles.heroFade} />
          <div className={styles.heroText}>
            <h1 className={styles.headline}>
              <span>Suas opiniões<i>.</i></span>
              <span>Seus gostos<i>.</i></span>
              <span>Seus filmes<i>.</i></span>
            </h1>
            <Link href="/cadastro" className={styles.cta}>
              Criar Conta
            </Link>
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Populares entre os usuários</h2>
          {filmes.length > 0 ? (
            <MovieCarousel filmes={filmes} />
          ) : (
            <p className={styles.empty}>Não foi possível carregar os filmes agora.</p>
          )}
        </section>
      </main>
    </>
  );
}
