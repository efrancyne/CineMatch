# Resultados dos modelos (2026-11-06 22:20)

- Split temporal por usuário: últimas 20% das avaliações de cada usuário (mínimo 1) no teste.
- Relevante: nota de teste >= 4.0. Métricas de acurácia são médias sobre 592 usuários com ao menos um relevante no teste.
- Filmes já vistos no treino são excluídos das recomendações.
- Cobertura = fração do catálogo que aparece em alguma lista; novidade = auto-informação média (-log2 da popularidade); diversidade = 1 - similaridade média de gêneros/década dentro da lista.
- Modelo escolhido: **hibrido-svd-f20+cb-a0.8** (fatores e alfa ajustados por NDCG@10 numa validação temporal tirada só do treino; o teste não foi usado no ajuste).

| modelo                        |   precision@10 |   recall@10 |   ndcg@10 |   map@10 |   cobertura@10 |   novidade@10 |   diversidade@10 |   precision@20 |   recall@20 |   ndcg@20 |   map@20 |   cobertura@20 |   novidade@20 |   diversidade@20 |
|:------------------------------|---------------:|------------:|----------:|---------:|---------------:|--------------:|-----------------:|---------------:|------------:|----------:|---------:|---------------:|--------------:|-----------------:|
| aleatorio                     |         0.0017 |      0.0007 |    0.0013 |   0.0003 |         0.4623 |        7.3154 |           0.7622 |         0.0018 |      0.0026 |    0.0020 |   0.0003 |         0.7110 |        7.3091 |           0.7626 |
| popularidade-contagem         |         0.0576 |      0.0484 |    0.0750 |   0.0359 |         0.0101 |        1.5201 |           0.6789 |         0.0486 |      0.0832 |    0.0813 |   0.0326 |         0.0165 |        1.6981 |           0.6924 |
| popularidade-bayesiana        |         0.0098 |      0.0071 |    0.0194 |   0.0099 |         0.0025 |        5.3519 |           0.4896 |         0.0106 |      0.0153 |    0.0213 |   0.0085 |         0.0051 |        5.0606 |           0.6210 |
| item-item-k50                 |         0.0807 |      0.0772 |    0.1010 |   0.0485 |         0.0744 |        2.6155 |           0.6565 |         0.0705 |      0.1347 |    0.1155 |   0.0469 |         0.1022 |        2.7231 |           0.6791 |
| svd-f50                       |         0.0848 |      0.0875 |    0.1064 |   0.0492 |         0.0692 |        2.5098 |           0.6708 |         0.0684 |      0.1471 |    0.1207 |   0.0492 |         0.0996 |        2.7127 |           0.6830 |
| conteudo-generos              |         0.0054 |      0.0030 |    0.0064 |   0.0022 |         0.3558 |        7.0961 |           0.1145 |         0.0053 |      0.0064 |    0.0073 |   0.0018 |         0.5304 |        7.1135 |           0.1382 |
| hibrido-item-item-k50+cb-a0.8 |         0.0868 |      0.0815 |    0.1087 |   0.0532 |         0.0799 |        2.6995 |           0.6110 |         0.0719 |      0.1360 |    0.1200 |   0.0498 |         0.1139 |        2.8128 |           0.6386 |
| hibrido-svd-f50+cb-a0.8       |         0.0863 |      0.0933 |    0.1110 |   0.0525 |         0.0768 |        2.6268 |           0.6058 |         0.0697 |      0.1493 |    0.1244 |   0.0516 |         0.1146 |        2.8579 |           0.6156 |
| hibrido-svd-f20+cb-a0.8       |         0.0912 |      0.0866 |    0.1138 |   0.0557 |         0.0545 |        2.3636 |           0.6164 |         0.0753 |      0.1477 |    0.1273 |   0.0534 |         0.0815 |        2.5968 |           0.6347 |
