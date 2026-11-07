"""Métricas de ranking, cobertura, novidade e diversidade.

Critério de relevância: uma avaliação de teste com nota >= 4.0
(LIMIAR_RELEVANTE). As métricas de acurácia (Precision, Recall, NDCG, MAP)
são médias sobre os usuários com pelo menos um item relevante no teste;
usuários sem nenhum relevante não entram na média.
"""
import numpy as np
import pandas as pd
from scipy import sparse

from ml.dados import LIMIAR_RELEVANTE
from ml.modelos import Recomendador, matriz_conteudo


def top_k_todos(modelo: Recomendador, k: int, lote: int = 256) -> np.ndarray:
    """Top-k (índices de coluna) para todos os usuários do treino,
    excluindo os filmes já vistos no treino."""
    n = modelo.indice.n_usuarios
    saida = np.empty((n, k), dtype=np.int64)
    for inicio in range(0, n, lote):
        linhas = np.arange(inicio, min(inicio + lote, n))
        scores = modelo.pontuar(linhas).astype(np.float64)
        vistos = modelo.vistos[linhas].tocoo()
        scores[vistos.row, vistos.col] = -np.inf
        top = np.argpartition(-scores, k, axis=1)[:, :k]
        ordem = np.argsort(-np.take_along_axis(scores, top, axis=1), axis=1)
        saida[linhas] = np.take_along_axis(top, ordem, axis=1)
    return saida


def avaliar(modelo: Recomendador, teste: pd.DataFrame, ks=(10, 20)) -> dict:
    indice = modelo.indice
    k_max = max(ks)
    top = top_k_todos(modelo, k_max)

    relevantes = teste[teste["rating"] >= LIMIAR_RELEVANTE]
    relevantes = relevantes[relevantes["user_id"].isin(indice.linha)]
    rel_por_linha = {
        indice.linha[u]: set(grupo["movie_id"].map(indice.coluna))
        for u, grupo in relevantes.groupby("user_id")
    }
    linhas_avaliadas = np.array(sorted(rel_por_linha))
    linhas_teste = np.array(
        sorted({indice.linha[u] for u in teste["user_id"] if u in indice.linha})
    )

    # Popularidade de cada filme no treino (para novidade)
    n_usuarios = indice.n_usuarios
    pop = np.asarray((modelo.vistos).sum(axis=0)).ravel()
    auto_informacao = -np.log2((pop + 1) / (n_usuarios + 1))

    F = matriz_conteudo(modelo.dados, indice.movie_ids)

    resultado = {"modelo": modelo.nome, "usuarios_avaliados": len(linhas_avaliadas)}
    for k in ks:
        precisoes, recalls, ndcgs, aps = [], [], [], []
        descontos = 1.0 / np.log2(np.arange(2, k + 2))
        for linha in linhas_avaliadas:
            rel = rel_por_linha[linha]
            acertos = np.array([j in rel for j in top[linha, :k]], dtype=float)
            n_acertos = acertos.sum()
            precisoes.append(n_acertos / k)
            recalls.append(n_acertos / len(rel))
            dcg = (acertos * descontos).sum()
            idcg = descontos[: min(len(rel), k)].sum()
            ndcgs.append(dcg / idcg)
            precisao_em = np.cumsum(acertos) / np.arange(1, k + 1)
            aps.append((precisao_em * acertos).sum() / min(len(rel), k))

        listas = top[linhas_teste, :k]
        cobertura = len(np.unique(listas)) / indice.n_filmes
        novidade = auto_informacao[listas].mean()
        diversidade = _diversidade_intra_lista(F, listas)

        resultado.update({
            f"precision@{k}": np.mean(precisoes),
            f"recall@{k}": np.mean(recalls),
            f"ndcg@{k}": np.mean(ndcgs),
            f"map@{k}": np.mean(aps),
            f"cobertura@{k}": cobertura,
            f"novidade@{k}": novidade,
            f"diversidade@{k}": diversidade,
        })
    return resultado


def _diversidade_intra_lista(F: sparse.csr_matrix, listas: np.ndarray) -> float:
    """1 - similaridade média (cosseno de gêneros+década) entre pares de
    filmes da mesma lista. 0 = todos iguais; 1 = nada em comum."""
    k = listas.shape[1]
    valores = []
    for lista in listas:
        V = F[lista]
        S = (V @ V.T).toarray()
        media_pares = (S.sum() - np.trace(S)) / (k * (k - 1))
        valores.append(1.0 - media_pares)
    return float(np.mean(valores))
