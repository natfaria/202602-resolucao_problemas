# Planejamento de preços e demanda: Minerva

Projeto da disciplina de resolução de problemas por modelagem matemática, com base no
[Desafio Minerva-Unifesp-ITA](docs/referencias/Minerva_Unifesp_ITA.pdf). O objetivo é escolher o
preço diário de `Produto_A` em um horizonte de dez dias úteis (03 a 14/11/2025) que maximiza a
margem de contribuição prevista, sob metas semanais de volume, limite de variação de preço entre
dias e a curva de demanda estimada a partir do histórico.

**Conclusão principal:** com todas as regras originais, não existe plano viável. O maior volume
previsto é 76,99 kg e 84,62 kg por semana, contra um mínimo de 115,5 kg. O plano de maior margem
exige relaxar o limite da primeira mudança de preço. As alternativas e as sensibilidades estão no
[storytelling da otimização](docs/storytelling/03-storytelling-otimizacao-minerva.md).

Para o contexto completo do enunciado, das premissas e do estado atual, leia
[contexto do desafio](docs/planejamento/contexto-desafio-minerva.md).

## Como rodar do zero

Pré-requisitos: Git, Python 3.10 ou superior (a revisão usa 3.13) e uma licença válida do Gurobi 13,
necessária para resolver a otimização.

**1. Clonar o repositório**

```bash
git clone git@github-mestrado:natfaria/202602-resolucao_problemas.git
cd 202602-resolucao_problemas
```

Se o alias SSH `github-mestrado` não estiver configurado, use a URL do GitHub do repositório.

**2. Criar o ambiente virtual**

```bash
python3 -m venv .venv
```

**3. Instalar as dependências**

```bash
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt
```

O `requirements.txt` instala também o próprio pacote `src` em modo editável (`-e .`).

**4. Verificar o Gurobi**

```bash
.venv/bin/python -c "import gurobipy; print('Gurobi', '.'.join(map(str, gurobipy.gurobi.version())))"
```

Deve aparecer `Gurobi 13.x`. Se a importação falhar, a licença não está disponível neste ambiente.

**5. Rodar os testes**

```bash
.venv/bin/python -m pytest -q
```

Devem passar todos os testes (99 no estado atual, em cerca de 25 segundos).

**6. Usar a ferramenta de planejamento**

```bash
.venv/bin/python -m streamlit run src/app/ferramenta_precos.py
```

Abra o endereço indicado no terminal (normalmente `http://localhost:8501`). As entradas da curva,
da planilha e das restrições já estão versionadas; não é preciso rodar os notebooks para usar a
ferramenta.

**7. (Opcional) Reproduzir o pipeline dos notebooks**

Os artefatos já estão no repositório. Reexecute as etapas apenas para reproduzir ou alterar
premissas. Cada etapa sobrescreve arquivos versionados, então o `git status` mostrará as mudanças.

- **a.** Preparação e EDA (rápido):
  ```bash
  .venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/1.0-minerva-eda-preparacao.ipynb --ExecutePreprocessor.timeout=300
  ```
- **b.** Curva preditiva (publica `models/preditivo_diario/curva_demanda.json`):
  ```bash
  .venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/2.0.1-minerva-modelo-preditivo.ipynb --ExecutePreprocessor.timeout=300
  ```
- **c.** Otimização de referência (publica `models/otimizacao/entradas_planejamento.json` e os planos; usa o Gurobi):
  ```bash
  .venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.0-minerva-otimizacao-precos.ipynb --ExecutePreprocessor.timeout=300
  ```
- **d.** Flexibilizações graduais (usa o Gurobi em muitas resoluções):
  ```bash
  .venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.1-minerva-simulacao-relaxacoes.ipynb --ExecutePreprocessor.timeout=300
  ```
- **e.** Atualizar os relatórios a partir dos artefatos:
  ```bash
  .venv/bin/python scripts/update_project_report.py
  ```

Para abrir os notebooks de forma interativa, use `.venv/bin/python -m jupyter lab`.

**8. (Opcional) Ver a documentação**

```bash
.venv/bin/python -m mkdocs serve --config-file docs/mkdocs.yml
```

## Visão geral do fluxo

O projeto é dividido em etapas que se comunicam por arquivos persistidos, com verificação de
integridade por hash:

```
1.0 EDA e preparação → 2.0.1 Curva preditiva → 3.0 Otimização de referência → 3.1 Flexibilizações
                                                         │
                                          Ferramenta Streamlit (usa as mesmas funções)
```

1. **Preparação (1.0):** valida a planilha, separa desenvolvimento e holdout e explora os dados.
2. **Curva preditiva (2.0.1):** ajusta e seleciona a curva de demanda por validação cruzada temporal.
   Publica `models/preditivo_diario/curva_demanda.json`.
3. **Otimização de referência (3.0):** resolve o plano de 10 dias com as regras originais, diagnostica
   a viabilidade, testa uma regra por vez e compara com o holdout. Publica as entradas do
   planejamento em `models/otimizacao/entradas_planejamento.json`.
4. **Flexibilizações (3.1):** mede quanto cada regra precisa ser relaxada e o efeito de combinações.
5. **Ferramenta:** interface para planejar com entradas definidas pelo usuário.

## Estrutura do repositório

```
├── .streamlit/       tema visual da ferramenta (cores e fonte)
├── data/
│   ├── raw/          fonte original (planilha do desafio), não modificada
│   ├── interim/      histórico limpo, desenvolvimento, holdout e restrições
│   └── processed/    dados de modelagem, resultados e planos
├── docs/             documentação (mkdocs) e referências
├── models/
│   ├── preditivo_diario/   curva de demanda publicada
│   └── otimizacao/         entradas congeladas e limites de flexibilização
├── notebooks/        as quatro etapas da entrega
├── reports/          tabelas e figuras geradas pelos notebooks
├── scripts/          utilitário de atualização dos relatórios
├── src/              código do produto (lógica, solver, ferramenta e interface)
│   ├── modeling/     curva de demanda e benchmarks
│   ├── optimization/ entradas, problema, solver, relaxações e ferramenta
│   └── app/          interface Streamlit da ferramenta e seus logos
└── tests/            testes automatizados e fixtures legadas
```

## Como usar cada componente

### Instalação

Use Python 3.10 ou superior. A revisão usa Python 3.13 e Gurobi 13 com licença válida.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

O passo a passo completo, com verificações, está em
[Instalação e reprodução](docs/planejamento/getting-started.md).

### Notebooks

Execute na ordem, cada um com um kernel limpo:

```bash
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/1.0-minerva-eda-preparacao.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/2.0.1-minerva-modelo-preditivo.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.0-minerva-otimizacao-precos.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.1-minerva-simulacao-relaxacoes.ipynb --ExecutePreprocessor.timeout=300
```

Ou, para abrir e explorar, `.venv/bin/python -m jupyter lab`. Atalho: `make data` executa só o 1.0.

| Notebook | O que responde |
|---|---|
| [1.0 Preparação e EDA](notebooks/1.0-minerva-eda-preparacao.ipynb) | Os dados são confiáveis? Como variam preço, volume e calendário? |
| [2.0.1 Demanda preditiva](notebooks/2.0.1-minerva-modelo-preditivo.ipynb) | Como preço e calendário explicam o volume? Qual curva foi escolhida? |
| [3.0 Otimização de referência](notebooks/3.0-minerva-otimizacao-precos.ipynb) | Quais regras impedem um plano? Qual plano maximiza a margem sob cada alteração? |
| [3.1 Flexibilizações](notebooks/3.1-minerva-simulacao-relaxacoes.ipynb) | Quanto cada regra precisa ser relaxada? O que acontece com combinações? |

Após reexecutar as etapas, atualize os relatórios:

```bash
.venv/bin/python scripts/update_project_report.py
```

Use `--check` para verificar se os relatórios estão defasados em relação aos artefatos, sem escrever
arquivos.

### Ferramenta de planejamento (Streamlit)

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

### Código-fonte (`src/`)

- `src/modeling/demand_curve.py`: carregamento, validação e previsão da curva publicada.
- `src/modeling/benchmarks.py`: benchmarks de referência para a previsão.
- `src/optimization/price_schedule.py`: problema de preço, horizonte, viabilidade e validação dos planos.
- `src/optimization/planning_inputs.py`: salva e carrega as entradas do planejamento com verificação de hash.
- `src/optimization/gurobi_solver.py`: solver Gurobi para cenários de regras.
- `src/optimization/relaxation_study.py`: mínimos de viabilidade e curvas de flexibilização.
- `src/optimization/holdout_comparison.py`: comparação dos planos com os dados reais do holdout.
- `src/optimization/ferramenta.py`: entradas, solução e análise de restrições para a ferramenta.

### Testes

```bash
.venv/bin/python -m pytest -q
```

Os testes validam a curva, o solver, as entradas congeladas, a comparação com o holdout e a
ferramenta. Modelos históricos usados apenas para compatibilidade ficam em `tests/fixtures/legacy/`.

Lint e formatação:

```bash
make lint      # ruff check e formato (hoje acusa formatação pendente em src/modeling/demand_curve.py)
make format    # aplica as correções automáticas
```

### Documentação

```bash
.venv/bin/python -m mkdocs serve --config-file docs/mkdocs.yml
.venv/bin/python -m mkdocs build --config-file docs/mkdocs.yml --strict
```

O ponto de entrada é [Planejamento e funcionamento](docs/planejamento/index.md), com a formulação
matemática em [modelo matemático](docs/planejamento/modelo-matematico-otimizacao-precos.md) e as
referências em [referências metodológicas](docs/referencias-bibliograficas.md).

## Artefatos

- `data/raw/`: fontes originais.
- `data/interim/` e `data/processed/`: dados preparados, resultados e planos.
- `models/preditivo_diario/`: curva preditiva publicada.
- `models/otimizacao/`: entradas congeladas do planejamento e limites de flexibilização.
- `reports/tables/` e `reports/figures/`: comparações e figuras da otimização de referência.
- `reports/tables/relaxacoes/` e `reports/figures/relaxacoes/`: estudo de flexibilizações.

Cada plano exportado conserva sua curva, suas entradas e suas condições operacionais. Somente os
quatro notebooks listados compõem a entrega.
