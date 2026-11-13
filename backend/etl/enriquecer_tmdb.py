"""Enriquece movies com sinopse, data de lançamento e pôster do TMDB.

Uso:
    python enriquecer_tmdb.py                # filmes ainda não checados
    python enriquecer_tmdb.py --limite 20    # só os 20 primeiros
    python enriquecer_tmdb.py --refazer      # reconsulta filmes já checados

Credenciais (ambiente ou backend/.env): TMDB_BEARER_TOKEN (preferido, não
aparece na URL) ou TMDB_API_KEY.
"""
import argparse
import os
import time

import psycopg
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from configuracao import database_url

TMDB_API_URL = os.getenv("TMDB_API_URL", "https://api.themoviedb.org/3")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")


def criar_sessao() -> requests.Session:
    if not TMDB_BEARER_TOKEN and not TMDB_API_KEY:
        raise RuntimeError(
            "Defina TMDB_BEARER_TOKEN ou TMDB_API_KEY "
            "(no ambiente ou em backend/.env)."
        )

    # Retry com backoff exponencial para erros de rede, 5xx e 429.
    # No 429, o header Retry-After é respeitado.
    tentativas = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    sessao = requests.Session()
    sessao.mount("https://", HTTPAdapter(max_retries=tentativas))
    sessao.mount("http://", HTTPAdapter(max_retries=tentativas))

    if TMDB_BEARER_TOKEN:
        sessao.headers["Authorization"] = f"Bearer {TMDB_BEARER_TOKEN}"
    else:
        sessao.params = {"api_key": TMDB_API_KEY}
    return sessao


def sem_segredos(mensagem: str) -> str:
    """Remove a api_key de mensagens de erro (que costumam conter a URL)."""
    if TMDB_API_KEY:
        mensagem = mensagem.replace(TMDB_API_KEY, "***")
    return mensagem


def consultar(sessao: requests.Session, tmdb_id: int, idioma: str):
    """Retorna o JSON do filme, ou None se o TMDB não o conhece (404)."""
    resposta = sessao.get(
        f"{TMDB_API_URL}/movie/{tmdb_id}",
        params={"language": idioma},
        timeout=20,
    )
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limite", type=int, help="máximo de filmes a consultar")
    parser.add_argument(
        "--refazer",
        action="store_true",
        help="reconsulta também os filmes já checados (tmdb_checked_at)",
    )
    args = parser.parse_args()

    sessao = criar_sessao()

    with psycopg.connect(database_url()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tmdb_id
                FROM movies
                WHERE tmdb_id IS NOT NULL
                  AND (overview IS NULL OR release_date IS NULL OR poster_path IS NULL)
                  AND (%(refazer)s OR tmdb_checked_at IS NULL)
                -- mais avaliados primeiro: são os que a interface mostra antes
                ORDER BY (SELECT count(*) FROM ratings r WHERE r.movie_id = movies.id) DESC, id
                LIMIT %(limite)s
                """,
                {"refazer": args.refazer, "limite": args.limite},
            )
            filmes = cursor.fetchall()

            print(f"{len(filmes)} filmes precisam de dados do TMDB.")

            totais = {
                "consultados": 0,
                "atualizados": 0,
                "sem_sinopse": 0,
                "nao_encontrados": 0,
                "erros": 0,
            }

            for numero, (movie_id, tmdb_id) in enumerate(filmes, start=1):
                totais["consultados"] += 1
                try:
                    dados = consultar(sessao, tmdb_id, "pt-BR")

                    # Fallback de idioma: sem sinopse em pt-BR, tenta en-US
                    if dados is not None and not dados.get("overview"):
                        dados_en = consultar(sessao, tmdb_id, "en-US")
                        if dados_en is not None:
                            dados["overview"] = dados_en.get("overview")
                except requests.RequestException as erro:
                    totais["erros"] += 1
                    print(
                        f"Erro no filme TMDB {tmdb_id} (movie {movie_id}): "
                        f"{sem_segredos(str(erro))}"
                    )
                    continue

                if dados is None:
                    totais["nao_encontrados"] += 1
                    print(f"Filme TMDB {tmdb_id} não encontrado; pulando.")
                    cursor.execute(
                        "UPDATE movies SET tmdb_checked_at = now() WHERE id = %s",
                        (movie_id,),
                    )
                else:
                    if not dados.get("overview"):
                        totais["sem_sinopse"] += 1

                    # COALESCE: nunca troca um valor existente por NULL
                    cursor.execute(
                        """
                        UPDATE movies
                        SET overview = COALESCE(%s, overview),
                            release_date = COALESCE(%s, release_date),
                            poster_path = COALESCE(%s, poster_path),
                            tmdb_checked_at = now()
                        WHERE id = %s
                        """,
                        (
                            dados.get("overview") or None,
                            dados.get("release_date") or None,
                            dados.get("poster_path") or None,
                            movie_id,
                        ),
                    )
                    totais["atualizados"] += 1

                if numero % 100 == 0:
                    conexao.commit()
                    print(f"{numero}/{len(filmes)} filmes consultados.", flush=True)

                time.sleep(0.05)

            conexao.commit()

    print("Enriquecimento concluído.")
    print(
        "Resumo: {consultados} consultados, {atualizados} atualizados, "
        "{sem_sinopse} sem sinopse, {nao_encontrados} não encontrados (404), "
        "{erros} erros.".format(**totais)
    )


if __name__ == "__main__":
    main()
