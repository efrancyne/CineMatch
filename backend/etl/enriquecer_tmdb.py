import time

import psycopg
import requests

from configuracao import database_url, variavel_obrigatoria

TMDB_API_KEY = variavel_obrigatoria("TMDB_API_KEY")

with psycopg.connect(database_url()) as conexao:
    with conexao.cursor() as cursor:
        cursor.execute("""
            SELECT id, tmdb_id
            FROM movies
            WHERE tmdb_id IS NOT NULL
              AND (overview IS NULL OR release_date IS NULL OR poster_path IS NULL)
        """)
        filmes = cursor.fetchall()

        print(f"{len(filmes)} filmes precisam de dados do TMDB.")

        for numero, (movie_id, tmdb_id) in enumerate(filmes, start=1):
            resposta = requests.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                params={
                    "api_key": TMDB_API_KEY,
                    "language": "pt-BR",
                },
                timeout=20,
            )

            if resposta.status_code == 404:
                print(f"Filme TMDB {tmdb_id} não encontrado; pulando.")
                continue

            resposta.raise_for_status()
            dados = resposta.json()

            cursor.execute(
                """
                UPDATE movies
                SET overview = %s,
                    release_date = %s,
                    poster_path = %s
                WHERE id = %s
                """,
                (
                    dados.get("overview") or None,
                    dados.get("release_date") or None,
                    dados.get("poster_path"),
                    movie_id,
                ),
            )

            if numero % 100 == 0:
                conexao.commit()
                print(f"{numero}/{len(filmes)} filmes consultados.")

            time.sleep(0.05)

        conexao.commit()

print("Enriquecimento concluído.")