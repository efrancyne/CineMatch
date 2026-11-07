"""Modelos de recomendação com interface comum.

Todos recebem os metadados (`Dados`) no construtor e expõem:
    fit(treino)                                  -> self
    recomendar(user_id, k=10, excluir_vistos=True) -> [(movie_id, score), ...]
    pontuar(linhas)                              -> matriz densa (usuários x filmes)

O catálogo é o conjunto de todos os filmes do banco; filmes sem avaliações
no treino recebem score 0 nos modelos colaborativos.
"""
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import svds

from ml.dados import Dados, Indice

RANDOM_STATE = 42


class Recomendador:
    nome = "base"

    def __init__(self, dados: Dados):
        self.dados = dados
        self.indice: Indice | None = None
        self.vistos: sparse.csr_matrix | None = None

    # --- interface pública ---
    def fit(self, treino: pd.DataFrame) -> "Recomendador":
        self.indice = Indice(treino["user_id"], self.dados.filmes["movie_id"])
        self.R = self.indice.matriz(treino)
        self.vistos = (self.R > 0).astype(np.float32).tocsr()
        self._treinar(treino)
        return self

    def recomendar(self, user_id: int, k: int = 10, excluir_vistos: bool = True):
        if user_id not in self.indice.linha:
            raise KeyError(f"Usuário {user_id} não está no treino (cold start).")
        linha = self.indice.linha[user_id]
        scores = self.pontuar(np.array([linha]))[0]
        if excluir_vistos:
            scores[self.vistos[linha].indices] = -np.inf
        top = np.argpartition(-scores, k)[:k]
        top = top[np.argsort(-scores[top])]
        return [(int(self.indice.movie_ids[j]), float(scores[j])) for j in top]

    # --- a implementar ---
    def _treinar(self, treino: pd.DataFrame) -> None:
        pass

    def pontuar(self, linhas: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class Aleatorio(Recomendador):
    nome = "aleatorio"

    def _treinar(self, treino):
        self.rng = np.random.default_rng(RANDOM_STATE)

    def pontuar(self, linhas):
        return self.rng.random((len(linhas), self.indice.n_filmes), dtype=np.float32)


class Popularidade(Recomendador):
    """Popularidade não personalizada.

    tipo="bayesiana": média bayesiana (n*média + m*C) / (n + m), onde C é a
        média global e m é o número mínimo de votos (padrão: mediana de
        avaliações por filme). Favorece filmes bem avaliados *e* com votos.
    tipo="contagem": número de avaliações no treino.
    """

    def __init__(self, dados, tipo: str = "bayesiana", m: float | None = None):
        super().__init__(dados)
        self.tipo = tipo
        self.m = m
        self.nome = f"popularidade-{tipo}"

    def _treinar(self, treino):
        n = np.asarray((self.R > 0).sum(axis=0)).ravel().astype(np.float64)
        soma = np.asarray(self.R.sum(axis=0)).ravel()
        if self.tipo == "contagem":
            self.scores = n
        else:
            media = np.divide(soma, n, out=np.zeros_like(soma), where=n > 0)
            C = treino["rating"].mean()
            m = self.m if self.m is not None else float(np.median(n[n > 0]))
            self.scores = (n * media + m * C) / (n + m)
            self.scores[n == 0] = 0.0
        self.scores = self.scores.astype(np.float32)

    def pontuar(self, linhas):
        return np.tile(self.scores, (len(linhas), 1))


class ItemItem(Recomendador):
    """Filtragem colaborativa item-item com similaridade de cosseno.

    A similaridade é calculada entre as colunas (filmes) da matriz de notas
    do treino; cada filme mantém apenas os `vizinhos` mais similares.
    score(u, i) = soma, sobre os vizinhos j de i avaliados por u, de
    sim(i, j) * nota(u, j).
    """

    def __init__(self, dados, vizinhos: int = 50, bloco: int = 1000):
        super().__init__(dados)
        self.vizinhos = vizinhos
        self.bloco = bloco
        self.nome = f"item-item-k{vizinhos}"

    def _treinar(self, treino):
        X = self.R.tocsc().astype(np.float32)
        normas = np.sqrt(np.asarray(X.multiply(X).sum(axis=0)).ravel())
        normas[normas == 0] = 1.0
        Xn = (X @ sparse.diags(1.0 / normas)).tocsc()
        XnT = Xn.T.tocsr()

        n = self.indice.n_filmes
        k = self.vizinhos
        linhas, colunas, valores = [], [], []
        for inicio in range(0, n, self.bloco):
            fim = min(inicio + self.bloco, n)
            S = (XnT[inicio:fim] @ Xn).toarray()
            S[np.arange(fim - inicio), np.arange(inicio, fim)] = 0.0  # sem auto-similaridade
            top = np.argpartition(-S, k, axis=1)[:, :k]
            vals = np.take_along_axis(S, top, axis=1)
            mantem = vals > 0
            linhas.append(np.repeat(np.arange(inicio, fim), k)[mantem.ravel()])
            colunas.append(top.ravel()[mantem.ravel()])
            valores.append(vals.ravel()[mantem.ravel()])
        # S_topk[i, j] = sim(i, j) se j está entre os k vizinhos de i
        self.S = sparse.csr_matrix(
            (np.concatenate(valores), (np.concatenate(linhas), np.concatenate(colunas))),
            shape=(n, n),
        )

    def pontuar(self, linhas):
        return np.asarray((self.R[linhas] @ self.S.T).todense(), dtype=np.float32)


class SVD(Recomendador):
    """Fatoração de matrizes por SVD truncado (PureSVD).

    Aplica SVD truncado à matriz de notas do treino (ausentes = 0) e usa a
    reconstrução de posto `fatores` como score. Bom para ranking top-N
    (Cremonesi et al., 2010) e sem dependências além do SciPy.
    """

    def __init__(self, dados, fatores: int = 50):
        super().__init__(dados)
        self.fatores = fatores
        self.nome = f"svd-f{fatores}"

    def _treinar(self, treino):
        U, s, Vt = svds(
            self.R.astype(np.float64), k=self.fatores, random_state=RANDOM_STATE
        )
        self.P = (U * s).astype(np.float32)
        self.Q = Vt.astype(np.float32)

    def pontuar(self, linhas):
        return self.P[linhas] @ self.Q


def matriz_conteudo(dados: Dados, movie_ids: np.ndarray, peso_decada: float = 0.5):
    """Vetor de conteúdo de cada filme: gêneros (one-hot) + década (one-hot,
    com peso menor). Linhas normalizadas (L2). Usado pelo content-based e
    pela medida de diversidade."""
    coluna = {m: j for j, m in enumerate(movie_ids)}
    generos = sorted(dados.generos["genre"].unique())
    g_col = {g: i for i, g in enumerate(generos)}
    G = sparse.csr_matrix(
        (
            np.ones(len(dados.generos), dtype=np.float32),
            (
                dados.generos["movie_id"].map(coluna).to_numpy(),
                dados.generos["genre"].map(g_col).to_numpy(),
            ),
        ),
        shape=(len(movie_ids), len(generos)),
    )
    filmes = dados.filmes.dropna(subset=["year"])
    decadas = (filmes["year"].astype(int) // 10 * 10).to_numpy()
    d_vals = sorted(set(decadas))
    d_col = {d: i for i, d in enumerate(d_vals)}
    D = sparse.csr_matrix(
        (
            np.full(len(filmes), peso_decada, dtype=np.float32),
            (filmes["movie_id"].map(coluna).to_numpy(), [d_col[d] for d in decadas]),
        ),
        shape=(len(movie_ids), len(d_vals)),
    )
    F = sparse.hstack([G, D]).tocsr()
    normas = np.sqrt(np.asarray(F.multiply(F).sum(axis=1)).ravel())
    normas[normas == 0] = 1.0
    return (sparse.diags(1.0 / normas) @ F).tocsr()


class ConteudoGeneros(Recomendador):
    """Content-based com gêneros e década.

    Perfil do usuário = soma dos vetores dos filmes avaliados, ponderada
    por (nota - média do usuário): filmes acima da média puxam o perfil, os
    abaixo empurram. Score = cosseno entre o perfil e cada filme. Funciona
    para filmes sem nenhuma avaliação.
    """

    nome = "conteudo-generos"

    def _treinar(self, treino):
        self.F = matriz_conteudo(self.dados, self.indice.movie_ids)
        R = self.R.tocsr()
        n = np.diff(R.indptr)
        media = np.asarray(R.sum(axis=1)).ravel() / np.maximum(n, 1)
        W = R.copy()
        W.data = W.data - np.repeat(media, n).astype(np.float32)
        perfis = np.asarray((W @ self.F).todense())
        # Usuário que deu a mesma nota a tudo: usa a média simples dos filmes
        nulos = np.linalg.norm(perfis, axis=1) == 0
        if nulos.any():
            perfis[nulos] = np.asarray((self.vistos[nulos] @ self.F).todense())
        normas = np.linalg.norm(perfis, axis=1, keepdims=True)
        normas[normas == 0] = 1.0
        self.perfis = (perfis / normas).astype(np.float32)

    def pontuar(self, linhas):
        return np.asarray((self.F @ self.perfis[linhas].T).T, dtype=np.float32)


def _minmax_linhas(M: np.ndarray) -> np.ndarray:
    minimo = M.min(axis=1, keepdims=True)
    amplitude = M.max(axis=1, keepdims=True) - minimo
    amplitude[amplitude == 0] = 1.0
    return (M - minimo) / amplitude


class Hibrido(Recomendador):
    """Combinação ponderada dos scores (normalizados por usuário com
    min-max) de um modelo colaborativo e do content-based:
        score = alfa * CF + (1 - alfa) * CB
    """

    def __init__(self, dados, colaborativo: Recomendador, conteudo: Recomendador,
                 alfa: float = 0.8):
        super().__init__(dados)
        self.colaborativo = colaborativo
        self.conteudo = conteudo
        self.alfa = alfa
        self.nome = f"hibrido-{colaborativo.nome}+cb-a{alfa}"

    def _treinar(self, treino):
        self.colaborativo.fit(treino)
        self.conteudo.fit(treino)

    def pontuar(self, linhas):
        cf = _minmax_linhas(self.colaborativo.pontuar(linhas))
        cb = _minmax_linhas(self.conteudo.pontuar(linhas))
        return (self.alfa * cf + (1 - self.alfa) * cb).astype(np.float32)
