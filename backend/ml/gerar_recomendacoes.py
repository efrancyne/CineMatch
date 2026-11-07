"""Treina o modelo escolhido com todas as avaliações e grava o top-N de
cada usuário na tabela recommendations.

Uso (a partir de backend/):
    python -m ml.gerar_recomendacoes                 # versão hibrido-AAAA-MM-DD
    python -m ml.gerar_recomendacoes --versao teste1 --n 50

Lê os hiperparâmetros de ml/resultados/modelo_escolhido.json (gerado por
ml.avaliar). Idempotente: reexecutar com a mesma versão substitui só os
registros dessa versão, numa única transação.
"""
import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

from ml.dados import carregar, conectar
from ml.metricas import top_k_todos
from ml.modelos import SVD, ConteudoGeneros, Hibrido

ARQUIVO_MODELO = Path(__file__).resolve().parent / "resultados" / "modelo_escolhido.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera recomendações em lote.")
    parser.add_argument("--versao", default=f"hibrido-{date.today():%Y-%m-%d}")
    parser.add_argument("--n", type=int, default=50, help="recomendações por usuário")
    args = parser.parse_args()

    if not ARQUIVO_MODELO.exists():
        raise RuntimeError("Rode antes: python -m ml.avaliar (gera modelo_escolhido.json).")
    escolhido = json.loads(ARQUIVO_MODELO.read_text(encoding="utf-8"))
    print(f"Modelo: {escolhido['modelo']} | versão: {args.versao}")

    with conectar() as conexao:
        dados = carregar(conexao)
        modelo = Hibrido(
            dados,
            SVD(dados, escolhido["fatores"]),
            ConteudoGeneros(dados),
            escolhido["alfa"],
        ).fit(dados.avaliacoes)

        top = top_k_todos(modelo, args.n)
        todas = np.arange(modelo.indice.n_usuarios)
        scores = np.take_along_axis(modelo.pontuar(todas), top, axis=1)

        with conexao.cursor() as cursor:
            cursor.execute(
                "DELETE FROM recommendations WHERE model_version = %s", (args.versao,)
            )
            removidas = cursor.rowcount
            with cursor.copy(
                "COPY recommendations (user_id, movie_id, score, rank, model_version) "
                "FROM STDIN"
            ) as copia:
                for linha, user_id in enumerate(modelo.indice.user_ids):
                    for posicao, coluna in enumerate(top[linha], start=1):
                        copia.write_row((
                            int(user_id),
                            int(modelo.indice.movie_ids[coluna]),
                            float(scores[linha][posicao - 1]),
                            posicao,
                            args.versao,
                        ))
        conexao.commit()

    total = modelo.indice.n_usuarios * args.n
    print(
        f"{total} recomendações gravadas para {modelo.indice.n_usuarios} usuários "
        f"({removidas} da mesma versão substituídas)."
    )


if __name__ == "__main__":
    main()
