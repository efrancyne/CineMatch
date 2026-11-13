"""Grava no Redis o ranking inicial `ranking:top-rated` (relatório, seção 2.7).

Roda ao final da carga no Postgres, para a estrutura não começar vazia.
Uso (a partir de backend/etl/):  ../../.venv/bin/python gravar_ranking_redis.py
"""
import os
import sys
from pathlib import Path

import psycopg
import redis
from configuracao import database_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.cache import CHAVE_RANKING, TAMANHO_RANKING, TTL_RANKING  # noqa: E402
from ml.cold_start import recomendar_cold_start  # noqa: E402


def main() -> None:
    with psycopg.connect(database_url()) as conexao:
        pares = recomendar_cold_start(conexao, k=TAMANHO_RANKING)
    r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    pipe = r.pipeline()
    pipe.delete(CHAVE_RANKING)
    pipe.zadd(CHAVE_RANKING, {str(m): s for m, s in pares})
    pipe.expire(CHAVE_RANKING, TTL_RANKING)
    pipe.execute()
    print(f"{len(pares)} filmes gravados em {CHAVE_RANKING}")


if __name__ == "__main__":
    main()
