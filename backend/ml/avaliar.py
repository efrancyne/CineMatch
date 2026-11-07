"""Treina e avalia todos os modelos com o split temporal por usuário.

Uso (a partir de backend/):
    python -m ml.avaliar

Grava ml/resultados/resultados.csv (histórico: uma linha por modelo e
execução) e ml/resultados/resultados.md (tabela da última execução).
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from ml.dados import FRACAO_TESTE, LIMIAR_RELEVANTE, carregar, split_temporal
from ml.metricas import avaliar
from ml.modelos import (
    SVD,
    Aleatorio,
    ConteudoGeneros,
    Hibrido,
    ItemItem,
    Popularidade,
)

PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"


def modelos_candidatos(dados):
    return [
        Aleatorio(dados),
        Popularidade(dados, tipo="contagem"),
        Popularidade(dados, tipo="bayesiana"),
        ItemItem(dados, vizinhos=50),
        SVD(dados, fatores=50),
        ConteudoGeneros(dados),
        Hibrido(dados, ItemItem(dados, vizinhos=50), ConteudoGeneros(dados), alfa=0.8),
        Hibrido(dados, SVD(dados, fatores=50), ConteudoGeneros(dados), alfa=0.8),
    ]


GRADE_FATORES = (20, 50, 100)
GRADE_ALFA = (0.6, 0.8, 0.9, 1.0)


def ajustar_hibrido(dados, treino) -> dict:
    """Escolhe fatores do SVD e alfa do híbrido por NDCG@10 numa validação
    temporal tirada só do treino (o teste não é usado no ajuste)."""
    sub_treino, validacao = split_temporal(treino)
    melhor = None
    for fatores in GRADE_FATORES:
        for alfa in GRADE_ALFA:
            modelo = Hibrido(dados, SVD(dados, fatores), ConteudoGeneros(dados), alfa)
            ndcg = avaliar(modelo.fit(sub_treino), validacao, ks=(10,))["ndcg@10"]
            print(f"  validação fatores={fatores:3d} alfa={alfa:.1f} NDCG@10={ndcg:.4f}")
            if melhor is None or ndcg > melhor["ndcg@10_validacao"]:
                melhor = {"fatores": fatores, "alfa": alfa, "ndcg@10_validacao": ndcg}
    return melhor


def main() -> None:
    dados = carregar()
    treino, teste = split_temporal(dados.avaliacoes)
    print(
        f"{len(dados.avaliacoes)} avaliações | treino {len(treino)} | teste {len(teste)} "
        f"| {dados.avaliacoes['user_id'].nunique()} usuários | "
        f"{len(dados.filmes)} filmes no catálogo"
    )

    print("Ajustando o híbrido na validação (sem usar o teste)...")
    escolhido = ajustar_hibrido(dados, treino)
    print(f"Escolhido: {escolhido}")

    execucao = datetime.now().strftime("%Y-%m-%d %H:%M")
    linhas = []
    hibrido_ajustado = Hibrido(
        dados,
        SVD(dados, escolhido["fatores"]),
        ConteudoGeneros(dados),
        escolhido["alfa"],
    )
    # O ajustado vai por último (é o "final"); se coincidir com um dos
    # candidatos fixos, sai da lista fixa para não duplicar a linha.
    candidatos = [
        m for m in modelos_candidatos(dados) if m.nome != hibrido_ajustado.nome
    ] + [hibrido_ajustado]
    for modelo in candidatos:
        inicio = time.perf_counter()
        modelo.fit(treino)
        resultado = avaliar(modelo, teste)
        resultado["segundos"] = round(time.perf_counter() - inicio, 1)
        resultado["execucao"] = execucao
        linhas.append(resultado)
        print(
            f"{modelo.nome:40s} P@10={resultado['precision@10']:.4f} "
            f"R@10={resultado['recall@10']:.4f} NDCG@10={resultado['ndcg@10']:.4f} "
            f"MAP@10={resultado['map@10']:.4f} cob@10={resultado['cobertura@10']:.3f} "
            f"({resultado['segundos']}s)"
        )

    tabela = pd.DataFrame(linhas)
    PASTA_RESULTADOS.mkdir(exist_ok=True)

    # Confere, no teste, se o escolhido supera os baselines
    final = linhas[-1]
    for baseline in ("aleatorio", "popularidade-contagem", "popularidade-bayesiana"):
        b = next(l for l in linhas if l["modelo"] == baseline)
        if final["ndcg@10"] <= b["ndcg@10"]:
            print(f"ATENÇÃO: {final['modelo']} NÃO supera {baseline} em NDCG@10.")
    escolhido["modelo"] = final["modelo"]
    escolhido["ndcg@10_teste"] = final["ndcg@10"]
    escolhido["execucao"] = execucao
    (PASTA_RESULTADOS / "modelo_escolhido.json").write_text(
        json.dumps(escolhido, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    csv = PASTA_RESULTADOS / "resultados.csv"
    historico = pd.concat([pd.read_csv(csv), tabela]) if csv.exists() else tabela
    historico.to_csv(csv, index=False, float_format="%.5f")

    colunas = ["modelo"] + [
        f"{m}@{k}"
        for k in (10, 20)
        for m in ("precision", "recall", "ndcg", "map", "cobertura", "novidade", "diversidade")
    ]
    md = [
        f"# Resultados dos modelos ({execucao})",
        "",
        f"- Split temporal por usuário: últimas {FRACAO_TESTE:.0%} das avaliações "
        "de cada usuário (mínimo 1) no teste.",
        f"- Relevante: nota de teste >= {LIMIAR_RELEVANTE}. Métricas de acurácia "
        f"são médias sobre {linhas[0]['usuarios_avaliados']} usuários com ao menos "
        "um relevante no teste.",
        "- Filmes já vistos no treino são excluídos das recomendações.",
        "- Cobertura = fração do catálogo que aparece em alguma lista; novidade = "
        "auto-informação média (-log2 da popularidade); diversidade = 1 - "
        "similaridade média de gêneros/década dentro da lista.",
        f"- Modelo escolhido: **{final['modelo']}** (fatores e alfa ajustados por "
        "NDCG@10 numa validação temporal tirada só do treino; o teste não foi "
        "usado no ajuste).",
        "",
        tabela[colunas].to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (PASTA_RESULTADOS / "resultados.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Resultados gravados em {PASTA_RESULTADOS}")


if __name__ == "__main__":
    main()
