"""Análise exploratória dos dados de avaliação.

Uso (a partir de backend/):
    python -m ml.eda

Grava ml/resultados/eda.md.
"""
from pathlib import Path

import pandas as pd

from ml.dados import LIMIAR_RELEVANTE, _consulta, carregar, conectar

PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"


def descrever(serie: pd.Series) -> str:
    q = serie.quantile([0.25, 0.5, 0.75, 0.9]).to_dict()
    return (
        f"mín {serie.min()}, p25 {q[0.25]:.0f}, mediana {q[0.5]:.0f}, "
        f"média {serie.mean():.1f}, p75 {q[0.75]:.0f}, p90 {q[0.9]:.0f}, máx {serie.max()}"
    )


def main() -> None:
    with conectar() as conexao:
        dados = carregar(conexao)
        cobertura = _consulta(
            conexao,
            """
            SELECT count(*) AS filmes,
                   count(tmdb_id) AS com_tmdb_id,
                   count(overview) AS com_overview,
                   count(poster_path) AS com_poster,
                   count(release_date) AS com_release_date,
                   count(tmdb_checked_at) AS checados_tmdb
            FROM movies
            """,
        ).iloc[0]

    av = dados.avaliacoes
    n_usuarios = av["user_id"].nunique()
    n_filmes_catalogo = len(dados.filmes)
    n_filmes_avaliados = av["movie_id"].nunique()
    esparsidade = 1 - len(av) / (n_usuarios * n_filmes_catalogo)

    por_usuario = av.groupby("user_id").size()
    por_filme = av.groupby("movie_id").size()
    filmes_sem_avaliacao = n_filmes_catalogo - n_filmes_avaliados
    distribuicao = av["rating"].value_counts().sort_index()

    linhas = [
        "# Análise exploratória (EDA)",
        "",
        "## Matriz usuário × filme",
        f"- {len(av)} avaliações, {n_usuarios} usuários, {n_filmes_catalogo} filmes no catálogo "
        f"({n_filmes_avaliados} com ao menos uma avaliação; {filmes_sem_avaliacao} sem nenhuma).",
        f"- Esparsidade: **{esparsidade:.2%}** das células estão vazias.",
        f"- Período: {av['rated_at'].min():%Y-%m-%d} a {av['rated_at'].max():%Y-%m-%d}.",
        "",
        "## Avaliações por usuário",
        f"- {descrever(por_usuario)}",
        "",
        "## Avaliações por filme (entre os avaliados)",
        f"- {descrever(por_filme)}",
        f"- Filmes com 1 avaliação: {(por_filme == 1).sum()} "
        f"({(por_filme == 1).mean():.1%}); com 10 ou mais: {(por_filme >= 10).sum()}.",
        f"- Os 10% de filmes mais avaliados concentram "
        f"{por_filme.nlargest(int(len(por_filme) * 0.1)).sum() / len(av):.1%} das avaliações "
        "(cauda longa).",
        "",
        "## Distribuição das notas",
        f"- Média {av['rating'].mean():.2f}; relevantes (>= {LIMIAR_RELEVANTE}): "
        f"{(av['rating'] >= LIMIAR_RELEVANTE).mean():.1%}.",
        "",
        "| nota | avaliações | % |",
        "|---:|---:|---:|",
        *[f"| {nota} | {n} | {n / len(av):.1%} |" for nota, n in distribuicao.items()],
        "",
        "## Cobertura dos dados do TMDB no banco",
        f"- tmdb_id: {cobertura['com_tmdb_id']} de {cobertura['filmes']} "
        f"({cobertura['com_tmdb_id'] / cobertura['filmes']:.1%})",
        f"- overview: {cobertura['com_overview']} ({cobertura['com_overview'] / cobertura['filmes']:.1%})",
        f"- poster_path: {cobertura['com_poster']} ({cobertura['com_poster'] / cobertura['filmes']:.1%})",
        f"- release_date: {cobertura['com_release_date']} "
        f"({cobertura['com_release_date'] / cobertura['filmes']:.1%})",
        f"- já checados (tmdb_checked_at): {cobertura['checados_tmdb']}",
        "",
        "Os modelos não usam esses campos (só ratings, gêneros e ano); eles servem à interface.",
        "",
    ]
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    (PASTA_RESULTADOS / "eda.md").write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
