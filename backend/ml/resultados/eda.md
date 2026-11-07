# Análise exploratória (EDA)

## Matriz usuário × filme
- 100836 avaliações, 610 usuários, 9742 filmes no catálogo (9724 com ao menos uma avaliação; 18 sem nenhuma).
- Esparsidade: **98.30%** das células estão vazias.
- Período: 1996-03-29 a 2018-09-24.

## Avaliações por usuário
- mín 20, p25 35, mediana 70, média 165.3, p75 168, p90 400, máx 2698

## Avaliações por filme (entre os avaliados)
- mín 1, p25 1, mediana 3, média 10.4, p75 9, p90 27, máx 329
- Filmes com 1 avaliação: 3446 (35.4%); com 10 ou mais: 2269.
- Os 10% de filmes mais avaliados concentram 60.0% das avaliações (cauda longa).

## Distribuição das notas
- Média 3.50; relevantes (>= 4.0): 48.2%.

| nota | avaliações | % |
|---:|---:|---:|
| 0.5 | 1370 | 1.4% |
| 1.0 | 2811 | 2.8% |
| 1.5 | 1791 | 1.8% |
| 2.0 | 7551 | 7.5% |
| 2.5 | 5550 | 5.5% |
| 3.0 | 20047 | 19.9% |
| 3.5 | 13136 | 13.0% |
| 4.0 | 26818 | 26.6% |
| 4.5 | 8551 | 8.5% |
| 5.0 | 13211 | 13.1% |

## Cobertura dos dados do TMDB no banco
- tmdb_id: 9733 de 9742 (99.9%)
- overview: 8439 (86.6%)
- poster_path: 9617 (98.7%)
- release_date: 9620 (98.7%)
- já checados (tmdb_checked_at): 0

Os modelos não usam esses campos (só ratings, gêneros e ano); eles servem à interface.
