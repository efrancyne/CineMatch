import csv
import re

import psycopg

from configuracao import PASTA_DADOS, database_url

with (PASTA_DADOS / "links.csv").open(encoding="utf-8", newline="") as arquivo:
    links = {}
    tmdb_vistos = set()
    for linha in csv.DictReader(arquivo):
        tmdb_id = int(linha["tmdbId"]) if linha["tmdbId"] else None
        # Alguns filmes do MovieLens apontam para o mesmo tmdbId;
        # como tmdb_id é UNIQUE, só a primeira ocorrência fica com ele.
        if tmdb_id in tmdb_vistos:
            tmdb_id = None
        elif tmdb_id is not None:
            tmdb_vistos.add(tmdb_id)
        links[linha["movieId"]] = tmdb_id

with psycopg.connect(database_url()) as conexao:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT name, id FROM genres")
        generos = dict(cursor.fetchall())

        with (PASTA_DADOS / "movies.csv").open(
            encoding="utf-8", newline=""
        ) as arquivo:
            for indice, filme in enumerate(csv.DictReader(arquivo), start=1):
                movie_lens_id = filme["movieId"]
                titulo_original = filme["title"]

                ano_encontrado = re.search(r"\((\d{4})\)$", titulo_original)
                ano = int(ano_encontrado.group(1)) if ano_encontrado else None
                titulo = re.sub(r"\s*\(\d{4}\)$", "", titulo_original).strip()

                cursor.execute(
                    """
                    INSERT INTO movies (title, year, movielens_id, tmdb_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (movielens_id) DO UPDATE
                    SET title = EXCLUDED.title,
                        year = EXCLUDED.year,
                        tmdb_id = EXCLUDED.tmdb_id
                    RETURNING id
                    """,
                    (titulo, ano, int(movie_lens_id), links.get(movie_lens_id)),
                )
                id_filme = cursor.fetchone()[0]

                for nome_genero in filme["genres"].split("|"):
                    if not nome_genero or nome_genero == "(no genres listed)":
                        continue

                    id_genero = generos.get(nome_genero)
                    if id_genero is None:
                        cursor.execute(
                            "INSERT INTO genres (name) VALUES (%s) RETURNING id",
                            (nome_genero,),
                        )
                        id_genero = cursor.fetchone()[0]
                        generos[nome_genero] = id_genero

                    cursor.execute(
                        """
                        INSERT INTO movie_genres (movie_id, genre_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (id_filme, id_genero),
                    )

                if indice % 1000 == 0:
                    print(f"{indice} filmes processados...", flush=True)

print("Importação de filmes e gêneros concluída.")