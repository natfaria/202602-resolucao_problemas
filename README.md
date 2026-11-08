# Planejamento de preços e demanda: Minerva

Projeto de modelagem matemática para prever demanda e escolher preços diários de `Produto_A`
em um horizonte de duas semanas, maximizando a margem de contribuição prevista sob restrições
comerciais. As etapas se comunicam por arquivos persistidos, com verificação de integridade.

**Conclusão principal:** o caso com todas as regras originais é inviável sob a previsão central. As recuperações mínimas, as sensibilidades e o uso em horizonte rolante estão no [storytelling da otimização](docs/storytelling/storytelling-otimizacao-minerva.md).

## Fluxo de execução

| Notebook | Entrega |
|---|---|
| [Preparação e EDA](notebooks/1.0-minerva-eda-preparacao.ipynb) | Dados auditados, desenvolvimento, holdout e hipóteses |
| [Demanda preditiva](notebooks/2.0.1-minerva-modelo-preditivo.ipynb) | Curva selecionada por WMAPE diário, smearing e suporte |
| [Otimização de referência](notebooks/3.0-minerva-otimizacao-precos.ipynb) | Modelo, diagnóstico, cenários pontuais, entradas e planos |
| [Flexibilizações graduais](notebooks/3.1-minerva-simulacao-relaxacoes.ipynb) | Mínimos, curvas e conjuntos parciais de preço, piso e teto com comparação financeira |

O preditivo publica `models/preditivo_diario/curva_demanda.json`. A otimização recebe esse
artefato e publica `models/otimizacao/entradas_planejamento.json`, com custo, imposto, preço
anterior, metas, limites e calendário. O estudo de flexibilizações recebe essas entradas e
carrega a curva nelas registrada. Se uma fonte mudar, as entradas devem ser geradas novamente. O teto
comercial do estudo é recebido de `models/otimizacao/limites_flexibilizacoes.json`: R$ 15/kg para
mudanças dentro do horizonte, com a primeira mudança examinada separadamente.

A preparação deve ser executada antes das etapas seguintes. Com o ambiente `.venv` instalado a
partir de `requirements.txt`, as etapas de previsão e decisão podem ser reproduzidas por:

```bash
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/2.0.1-minerva-modelo-preditivo.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.0-minerva-otimizacao-precos.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.1-minerva-simulacao-relaxacoes.ipynb --ExecutePreprocessor.timeout=300
```

A resolução utiliza Gurobi 13 via `gurobipy`. Cada notebook executa com um kernel limpo e seus
arquivos de entrada, sem depender de variáveis de outra sessão.

Os relatórios são atualizados após a execução por `.venv/bin/python scripts/update_project_report.py`.
O benchmark de calendário e a sensibilidade de premissas são análises adicionais; não alteram a curva central selecionada.

## Artefatos

- `data/raw/`: fontes originais.
- `data/interim/` e `data/processed/`: dados preparados, resultados e planos.
- `models/preditivo_diario/`: curva preditiva publicada.
- `models/otimizacao/`: entradas congeladas do planejamento.
- `reports/tables/` e `reports/figures/`: comparações e figuras da otimização de referência.
- `reports/tables/relaxacoes/` e `reports/figures/relaxacoes/`: estudo de flexibilizações.
- `src/optimization/`: contrato do planejamento, solver e estudo de flexibilizações.

## Verificação e documentação

```bash
.venv/bin/python -m pytest -q
```

O funcionamento, as premissas e a divisão das etapas estão em
[Planejamento do projeto](docs/planejamento/index.md). Cada plano exportado conserva sua curva,
suas entradas e suas condições operacionais. Margens são previsões condicionais ao modelo.


Para instalação e documentação, veja [Instruções de reprodução](docs/planejamento/getting-started.md).
O notebook `2.0-minerva-modelo-preditivo.ipynb` e as pastas `antigos/` são versões anteriores, fora da entrega atual.
