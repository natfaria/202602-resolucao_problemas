# Tabelas geradas

Cada tabela é gravada por um notebook. Os resumos em `docs/storytelling/` leem apenas estas tabelas
e os artefatos de `models/` e `data/processed/`.

| Origem | Arquivos | Conteúdo |
|---|---|---|
| Notebook 1.0 | `01_*` | Faixas de preço e volume, sazonalidade, catálogo de variáveis e de modelos |
| Notebook 2.0 | `preditivo_diario/` | Validação cruzada, comparação de candidatos, benchmark, coeficientes e holdout |
| Notebook 3.0 | `03_*` | Caso original, uma regra por vez, preço anterior, tolerância, premissas e holdout |
| Notebook 3.1 | `relaxacoes/` | Menores flexibilizações, curvas, combinações, alternativas e comparação com o holdout |

O relatório dos resumos é gerado por `scripts/update_project_report.py`, que confere os hashes dos
artefatos antes de escrever. Uma mudança de premissas exige reexecutar as etapas e atualizar os resumos.
