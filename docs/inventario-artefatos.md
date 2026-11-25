# Inventário dos artefatos

Este mapa distingue as fontes, os arquivos necessários ao funcionamento e os resultados para
consulta. Os artefatos gerados estão versionados para permitir a leitura e o uso da ferramenta sem
reexecutar o pipeline. Ser reproduzível não significa que um arquivo possa ser removido sem afetar
os consumidores atuais. Execute os notebooks na ordem indicada no README antes de atualizar os
resumos; as entradas congeladas usam hashes para detectar alterações nas fontes.

| Arquivos | Origem | Papel e consumidores | Tratamento na entrega |
|---|---|---|---|
| `data/raw/instance_desafio_minerva.xlsx` | Planilha do desafio | Fonte do notebook 1.0 | Manter como fonte original para reprodução. |
| `data/interim/minerva_holdout.csv` | 1.0 | Avaliação final nos notebooks 2.0 e 3.0 | Manter para reprodução e conferência do teste. |
| `data/interim/minerva_restricoes.csv` | 1.0 | Regras para o 3.0; fonte verificada pelas entradas do planejamento e pela ferramenta | Manter. |
| `data/processed/minerva_modelagem_treino.csv` | 1.0 | Treino do 2.0; fonte verificada pela curva e pelas entradas carregadas pela ferramenta | Manter. |
| `models/preditivo_diario/curva_demanda.json` | 2.0 | Curva congelada usada no 3.0, no gerador de resumos e na ferramenta | Manter. |
| `models/otimizacao/entradas_planejamento.json` | 3.0 | Entradas congeladas usadas no 3.1, nos resumos e na ferramenta | Manter com suas fontes e hashes. |
| `models/otimizacao/limites_flexibilizacoes.json` | 3.0 | Configuração usada no estudo 3.1 e em testes | Manter. |
| `data/processed/minerva_otimizacao_resultado.json` | 3.0 | Cenários para o 3.1, resumos e abas de consulta da ferramenta | Manter. |
| `data/processed/minerva_diagnostico_infactividade.json` | 3.0 | Diagnóstico consumido pelo gerador de resumos | Manter enquanto os resumos forem gerados assim. |
| `data/processed/minerva_referencia_real_teste.json` | 3.0 | Referência realizada usada na comparação do 3.1 | Manter para reprodução do 3.1. |
| `data/processed/minerva_sensibilidade_isolada.json`, `minerva_sensibilidade_preco_anterior.json` | 3.0 | Resultados detalhados de sensibilidade, também usados em testes | Manter para auditoria e testes. |
| `data/processed/minerva_plano_precos.csv` | 3.0 | Planos diários exportados para consulta | Manter como resultado da entrega; reproduzível. |
| `data/processed/minerva_simulacao_relaxacoes.json` | 3.1 | Resultado detalhado, usado no gerador de resumos e em testes | Manter. |
| `data/processed/minerva_planos_relaxacoes.csv` | 3.1 | Planos diários das flexibilizações para consulta | Manter como resultado da entrega; reproduzível. |
| `reports/tables/01_*.csv` e `reports/figures/01_*.png` | 1.0 | Tabelas e figuras exploratórias | Manter para consulta e eventual relatório; reproduzíveis. |
| `reports/tables/preditivo_diario/` e `reports/figures/preditivo_diario/` | 2.0 | Validação, diagnósticos e holdout; algumas tabelas alimentam o 3.0 e os resumos | Manter; reproduzíveis pelo 2.0. |
| `reports/tables/03_*.csv` e `reports/figures/03_*.png` | 3.0 | Cenários e comparações; tabelas também alimentam o 3.1, os resumos e abas da ferramenta, inclusive `03_tres_referencias_margem.csv` | Manter; reproduzíveis pelo 3.0. |
| `reports/tables/relaxacoes/` e `reports/figures/relaxacoes/` | 3.1 | Limiares, curvas, combinações e alternativas; os resumos leem limiares | Manter para consulta e geração dos resumos; reproduzíveis pelo 3.1. |
| `docs/storytelling/02-curva-de-demanda-modelo.md` e `03-storytelling-otimizacao-minerva.md` | `scripts/update_project_report.py` | Resumos dos resultados para leitura | Manter e atualizar pelo script, não editar os números manualmente. |
