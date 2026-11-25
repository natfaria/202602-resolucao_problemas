# Planejamento de preços e demanda: Minerva

Projeto da disciplina de resolução de problemas por modelagem matemática, com base no
[Desafio Minerva-Unifesp-ITA](docs/referencias/Minerva_Unifesp_ITA.pdf). O objetivo é escolher o
preço diário de `Produto_A` em um horizonte de dez dias úteis (03 a 14/11/2025) que maximiza a
margem de contribuição prevista, sob metas semanais de volume, limite de variação de preço entre
dias e a curva de demanda estimada a partir do histórico.

**Conclusão principal:** com todas as regras originais, não existe plano viável. O maior volume
previsto é 76,99 kg na primeira semana e 84,62 kg na segunda, contra um mínimo de 115,5 kg por
semana. O plano de maior margem exige relaxar o limite da primeira mudança de preço. Os resultados
e as limitações de cada etapa estão nos [resumos](docs/storytelling/) e nos notebooks.

Documentação complementar: [contexto do desafio](docs/contexto-desafio-minerva.md),
[modelo matemático](docs/modelo-matematico-otimizacao-precos.md) e
[referências](docs/referencias-bibliograficas.md).

## Como rodar do zero

Pré-requisitos: Git, Python 3.10 ou superior (o projeto foi executado com Python 3.13) e uma
licença válida do Gurobi 13, necessária para resolver a otimização.

**1. Clonar o repositório**

```bash
git clone git@github-mestrado:natfaria/202602-resolucao_problemas.git
cd 202602-resolucao_problemas
```

Se o alias SSH `github-mestrado` não estiver configurado, use a URL do GitHub do repositório.

**2. Criar o ambiente e instalar as dependências**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt
```

O `requirements.txt` instala também o próprio pacote `src` em modo editável (`-e .`).

**3. Verificar o Gurobi**

```bash
.venv/bin/python -c "import gurobipy; print('Gurobi', '.'.join(map(str, gurobipy.gurobi.version())))"
```

Deve aparecer `Gurobi 13.x`. Se a importação falhar, a licença não está disponível neste ambiente.

**4. Rodar os testes**

```bash
.venv/bin/python -m pytest -q
```

Devem passar todos os 80 testes, em cerca de 10 segundos.

**5. Usar a ferramenta de planejamento**

```bash
.venv/bin/python -m streamlit run src/app/ferramenta_precos.py
```

Abra o endereço indicado no terminal (normalmente `http://localhost:8501`). As entradas da curva,
da planilha e das restrições já estão versionadas; não é preciso rodar os notebooks para usar a
ferramenta.

**6. (Opcional) Reproduzir o pipeline dos notebooks**

Os artefatos já estão no repositório. Reexecute as etapas apenas para reproduzir ou alterar
premissas. Cada etapa sobrescreve arquivos versionados, então o `git status` mostrará as mudanças.
Execute na ordem, cada uma com um kernel limpo:

```bash
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/1.0-minerva-eda-preparacao.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/2.0-minerva-modelo-preditivo.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.0-minerva-otimizacao-precos.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.1-minerva-simulacao-relaxacoes.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python scripts/update_project_report.py
```

Os notebooks 3.0 e 3.1 usam o Gurobi em muitas resoluções. Para abrir os notebooks de forma
interativa, use `.venv/bin/python -m jupyter lab`.

**7. (Opcional) Ver a documentação**

```bash
.venv/bin/python -m mkdocs serve --config-file docs/mkdocs.yml
```

### Comandos do Makefile

| Comando | O que faz |
|---|---|
| `make help` | Lista os comandos disponíveis |
| `make requirements` | Instala as dependências em `.venv` |
| `make test` | Roda os testes |
| `make lint` | Verifica formatação e lint de `src/` |
| `make format` | Aplica as correções automáticas |
| `make data` | Reexecuta somente o notebook 1.0 |
| `make notebooks` | Reexecuta os quatro notebooks em ordem (usa Gurobi) |
| `make report` | Atualiza os resumos a partir dos artefatos |
| `make report-check` | Falha se os resumos estiverem defasados |
| `make docs` | Gera o site em `site/` com verificação estrita de links |
| `make clean` | Remove caches e arquivos compilados locais |

## Visão geral do fluxo

O projeto é dividido em etapas que se comunicam por arquivos persistidos, com verificação de
integridade por hash:

```
1.0 EDA e preparação → 2.0 Curva preditiva → 3.0 Otimização de referência → 3.1 Flexibilizações
                                                         │
                                          Ferramenta Streamlit (usa as mesmas funções)
```

1. **Preparação (1.0):** valida a planilha, separa desenvolvimento e holdout e explora os dados.
2. **Curva preditiva (2.0):** ajusta e seleciona a curva de demanda por validação cruzada temporal.
   Publica `models/preditivo_diario/curva_demanda.json`.
3. **Otimização de referência (3.0):** resolve o plano de 10 dias com as regras originais, diagnostica
   a viabilidade, testa uma regra por vez e compara com o holdout. Publica as entradas do
   planejamento em `models/otimizacao/entradas_planejamento.json`.
4. **Flexibilizações (3.1):** mede quanto cada regra precisa ser relaxada e o efeito de combinações.
5. **Ferramenta:** interface para planejar com entradas definidas pelo usuário.

## Notebooks

| Notebook | O que responde |
|---|---|
| [1.0 Preparação e EDA](notebooks/1.0-minerva-eda-preparacao.ipynb) | Os dados são confiáveis? Como variam preço, volume e calendário? |
| [2.0 Demanda preditiva](notebooks/2.0-minerva-modelo-preditivo.ipynb) | Como preço e calendário explicam o volume? Qual curva foi escolhida? |
| [3.0 Otimização de referência](notebooks/3.0-minerva-otimizacao-precos.ipynb) | Quais regras impedem um plano? Qual plano maximiza a margem sob cada alteração? |
| [3.1 Flexibilizações](notebooks/3.1-minerva-simulacao-relaxacoes.ipynb) | Quanto cada regra precisa ser relaxada? O que acontece com combinações? |

Resumos das etapas em [docs/storytelling/](docs/storytelling/): [exploração](docs/storytelling/01-storytelling-eda-minerva.md),
[curva de demanda](docs/storytelling/02-curva-de-demanda-modelo.md) e
[otimização e flexibilizações](docs/storytelling/03-storytelling-otimizacao-minerva.md).

## Ferramenta de planejamento (Streamlit)

Interface para planejar preços com entradas informadas pelo usuário. Execute a partir da raiz:

```bash
.venv/bin/python -m streamlit run src/app/ferramenta_precos.py
```

Entradas:

- preço anterior, limite da primeira mudança e limite entre dias consecutivos;
- meta semanal e tolerâncias abaixo e acima da meta;
- custo por kg (único) ou custo por dia, no painel recolhível "Custo por dia";
- imposto sobre a receita;
- regras a relaxar: primeira mudança, variação entre dias, mínimo semanal, máximo semanal e faixa de
  preços observada.

Saídas: status do cálculo, margem total, venda prevista, volumes semanais, o limite mais restritivo com
o ganho ao relaxá-lo sozinho, tabela diária de preços, volumes, vendas, impostos e margens, resumo
semanal, gráficos e download do plano em CSV. Quando não existe plano, a tela mostra o maior volume
alcançável por semana.

A lógica está em `src/optimization/ferramenta.py`, e a interface só chama essas funções. As margens
são previsões condicionais à curva congelada.

## Código-fonte (`src/`)

- `src/modeling/demand_curve.py`: carregamento, validação e previsão da curva publicada.
- `src/modeling/benchmarks.py`: benchmarks de referência para a previsão.
- `src/optimization/price_schedule.py`: problema de preço, horizonte, viabilidade e validação dos planos.
- `src/optimization/planning_inputs.py`: salva e carrega as entradas do planejamento com verificação de hash.
- `src/optimization/gurobi_solver.py`: solver Gurobi para cenários de regras.
- `src/optimization/relaxation_study.py`: mínimos de viabilidade e curvas de flexibilização.
- `src/optimization/assumption_sensitivity.py`: sensibilidade a demanda, custo, imposto e elasticidade.
- `src/optimization/holdout_comparison.py`: comparação dos planos com os dados reais do holdout.
- `src/optimization/diagnostico.py`: menor flexibilização de cada regra que permite um plano.
- `src/optimization/ferramenta.py`: entradas, solução e análise de restrições para a ferramenta.

## Testes e qualidade

```bash
.venv/bin/python -m pytest -q
make lint
```

Os testes validam a curva, o solver, as entradas congeladas, a comparação com o holdout, a
sensibilidade, os benchmarks e a ferramenta. O lint cobre `src/`, pelas regras do `pyproject.toml`.

## Artefatos

O [inventário dos artefatos](docs/inventario-artefatos.md) relaciona as fontes, os consumidores,
os resultados reproduzíveis e as figuras históricas preservadas para avaliação.

- `data/raw/`: fonte original (planilha do desafio), não modificada.
- `data/interim/`: holdout e restrições, separados pela etapa 1.0.
- `data/processed/`: base de modelagem, resultados e planos.
- `models/preditivo_diario/`: curva preditiva publicada.
- `models/otimizacao/`: entradas congeladas do planejamento e limites de flexibilização.
- `reports/tables/` e `reports/figures/`: tabelas e figuras geradas pelos notebooks, com
  `reports/tables/relaxacoes/` e `reports/figures/relaxacoes/` para o estudo de flexibilizações.

Cada plano exportado conserva sua curva, suas entradas e suas condições operacionais. Somente os
quatro notebooks listados compõem a entrega.

## Estrutura do repositório

```
├── .streamlit/       tema visual da ferramenta (cores e fonte)
├── data/
│   ├── raw/          fonte original (planilha do desafio), não modificada
│   ├── interim/      holdout e restrições
│   └── processed/    dados de modelagem, resultados e planos
├── docs/             contexto, modelo matemático, resumos das etapas e referências
├── models/
│   ├── preditivo_diario/   curva de demanda publicada
│   └── otimizacao/         entradas congeladas e limites de flexibilização
├── notebooks/        as quatro etapas da entrega
├── reports/          tabelas e figuras geradas pelos notebooks
├── scripts/          atualização dos resumos a partir dos artefatos
├── src/              código do produto (lógica, solver, ferramenta e interface)
│   ├── modeling/     curva de demanda e benchmarks
│   ├── optimization/ entradas, problema, solver, relaxações e ferramenta
│   └── app/          interface Streamlit da ferramenta e seus logos
└── tests/            testes automatizados
```
