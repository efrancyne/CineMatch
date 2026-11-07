import csv

import psycopg

from configuracao import PASTA_DADOS, database_url

LOTE = 1000

with psycopg.connect(database_url()) as conexao:
    with conexao.cursor() as cursor:
        # Traduz movieId do MovieLens para o id interno de movies
        cursor.execute("SELECT movielens_id, id FROM movies")
        ids_filmes = {
            str(movie_lens_id): id_interno
            for movie_lens_id, id_interno in cursor.fetchall()
        }

        with (PASTA_DADOS / "ratings.csv").open(
            encoding="utf-8", newline=""
        ) as arquivo:
            lote = []

            for numero, avaliacao in enumerate(csv.DictReader(arquivo), start=1):
                movie_lens_id = avaliacao["movieId"]

                if movie_lens_id not in ids_filmes:
                    raise ValueError(
                        f"Filme MovieLens {movie_lens_id} não encontrado em movies."
                    )

                lote.append((
                    int(avaliacao["userId"]),
                    ids_filmes[movie_lens_id],
                    float(avaliacao["rating"]),
                    int(avaliacao["timestamp"]),
                ))

                if len(lote) == LOTE:
                    cursor.executemany(
                        """
                        INSERT INTO movielens_ratings
                            (movielens_user_id, movie_id, rating, timestamp_unix)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (movielens_user_id, movie_id) DO UPDATE
                        SET rating = EXCLUDED.rating,
                            timestamp_unix = EXCLUDED.timestamp_unix
                        """,
                        lote,
                    )
                    lote.clear()
                    print(f"{numero} avaliações processadas...", flush=True)

            if lote:
                cursor.executemany(
                    """
                    INSERT INTO movielens_ratings
                        (movielens_user_id, movie_id, rating, timestamp_unix)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (movielens_user_id, movie_id) DO UPDATE
                    SET rating = EXCLUDED.rating,
                        timestamp_unix = EXCLUDED.timestamp_unix
                    """,
                    lote,
                )

print("Importação das avaliações concluída.")