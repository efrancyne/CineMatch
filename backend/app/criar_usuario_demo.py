"""Cria (ou atualiza) o usuário de demonstração para testar o login.

Uso (a partir de backend/):
    python -m app.criar_usuario_demo

A senha vem de DEMO_PASSWORD (ambiente ou backend/.env). O usuário recebe
gêneros preferidos e algumas avaliações de filmes conhecidos; depois de
rodar `python -m ml.gerar_recomendacoes` ele passa a ter recomendações do
modelo (antes disso, recebe as de cold start). Idempotente.
"""
import os

import psycopg
from dotenv import load_dotenv

from app.config import ARQUIVO_ENV, get_settings
from app.security import gerar_hash

load_dotenv(ARQUIVO_ENV)

USERNAME = "demo"
GENEROS = ["Animation", "Comedy", "Sci-Fi"]
# (movielens_id, nota): ids estáveis do MovieLens
AVALIACOES = [
    (1, 5.0),  # Toy Story
    (2571, 4.5),  # Matrix
    (260, 5.0),  # Star Wars IV
    (4306, 4.0),  # Shrek
    (6377, 4.5),  # Finding Nemo
    (1270, 4.0),  # Back to the Future
    (356, 3.5),  # Forrest Gump
    (2959, 3.0),  # Fight Club
    (588, 4.0),  # Aladdin
    (1265, 4.5),  # Groundhog Day
]


def main() -> None:
    senha = os.getenv("DEMO_PASSWORD")
    if not senha or len(senha) < 8:
        raise RuntimeError("Defina DEMO_PASSWORD (mín. 8 caracteres) no ambiente ou em backend/.env.")

    with psycopg.connect(get_settings().database_url) as conexao:
        user_id = conexao.execute(
            """
            INSERT INTO users (username, name, email, password_hash, bio)
            VALUES (%s, 'Usuário Demo', 'demo@cinematch.local', %s, 'Conta de demonstração.')
            ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
            RETURNING id
            """,
            (USERNAME, gerar_hash(senha)),
        ).fetchone()[0]

        conexao.execute(
            """
            INSERT INTO user_genres (user_id, genre_id)
            SELECT %s, id FROM genres WHERE name = ANY(%s)
            ON CONFLICT DO NOTHING
            """,
            (user_id, GENEROS),
        )
        for movielens_id, nota in AVALIACOES:
            conexao.execute(
                """
                INSERT INTO ratings (user_id, movie_id, rating, rated_at)
                SELECT %s, id, %s, now() FROM movies WHERE movielens_id = %s
                ON CONFLICT (user_id, movie_id) DO NOTHING
                """,
                (user_id, nota, movielens_id),
            )
        n = conexao.execute(
            "SELECT count(*) FROM ratings WHERE user_id = %s", (user_id,)
        ).fetchone()[0]

    print(f"Usuário '{USERNAME}' pronto (id {user_id}, {n} avaliações).")


if __name__ == "__main__":
    main()
