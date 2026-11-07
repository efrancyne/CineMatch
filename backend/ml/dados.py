"""Carga dos dados do banco e split temporal por usuário."""
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv
from scipy import sparse

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

LIMIAR_RELEVANTE = 4.0
FRACAO_TESTE = 0.2


def conectar() -> psycopg.Connection:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("A variável DATABASE_URL não foi encontrada.")
    return psycopg.connect(url)


def _consulta(conexao, sql: str) -> pd.DataFrame:
    with conexao.cursor() as cursor:
        cursor.execute(sql)
        colunas = [c.name for c in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=colunas)


@dataclass
class Dados:
    avaliacoes: pd.DataFrame  # user_id, movie_id, rating, rated_at
    filmes: pd.DataFrame  # movie_id, year
    generos: pd.DataFrame  # movie_id, genre


def carregar(conexao=None) -> Dados:
    fechar = conexao is None
    conexao = conexao or conectar()
    try:
        avaliacoes = _consulta(
            conexao,
            "SELECT user_id, movie_id, rating, rated_at FROM ratings",
        )
        filmes = _consulta(conexao, "SELECT id AS movie_id, year FROM movies")
        generos = _consulta(
            conexao,
            """
            SELECT mg.movie_id, g.name AS genre
            FROM movie_genres mg JOIN genres g ON g.id = mg.genre_id
            """,
        )
    finally:
        if fechar:
            conexao.close()
    avaliacoes["rating"] = avaliacoes["rating"].astype(float)
    return Dados(avaliacoes, filmes, generos)


def split_temporal(
    avaliacoes: pd.DataFrame, fracao_teste: float = FRACAO_TESTE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Para cada usuário, as avaliações mais recentes vão para o teste.

    Regra: ordena as avaliações do usuário por (rated_at, movie_id) e põe as
    últimas ceil(fracao_teste * n) no teste, com no mínimo 1. Usuários com
    uma única avaliação ficam só no treino (não há o que testar).
    O desempate por movie_id torna o split determinístico quando várias
    avaliações têm o mesmo timestamp (comum no MovieLens).
    """
    ordenado = avaliacoes.sort_values(["user_id", "rated_at", "movie_id"])
    posicao = ordenado.groupby("user_id").cumcount(ascending=False)  # 0 = mais recente
    total = ordenado.groupby("user_id")["movie_id"].transform("size")
    n_teste = np.maximum(1, np.ceil(fracao_teste * total)).astype(int)
    n_teste = np.where(total > 1, n_teste, 0)
    no_teste = posicao < n_teste
    return ordenado[~no_teste].copy(), ordenado[no_teste].copy()


class Indice:
    """Mapeia user_id/movie_id para linhas/colunas de matrizes."""

    def __init__(self, user_ids, movie_ids):
        self.user_ids = np.asarray(sorted(set(user_ids)))
        self.movie_ids = np.asarray(sorted(set(movie_ids)))
        self.linha = {u: i for i, u in enumerate(self.user_ids)}
        self.coluna = {m: j for j, m in enumerate(self.movie_ids)}

    @property
    def n_usuarios(self) -> int:
        return len(self.user_ids)

    @property
    def n_filmes(self) -> int:
        return len(self.movie_ids)

    def matriz(self, avaliacoes: pd.DataFrame, valor: str = "rating") -> sparse.csr_matrix:
        linhas = avaliacoes["user_id"].map(self.linha).to_numpy()
        colunas = avaliacoes["movie_id"].map(self.coluna).to_numpy()
        valores = avaliacoes[valor].to_numpy(dtype=np.float32)
        return sparse.csr_matrix(
            (valores, (linhas, colunas)), shape=(self.n_usuarios, self.n_filmes)
        )
