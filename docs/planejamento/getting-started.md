# Instalação e reprodução

Execute na raiz do repositório. Use Python 3.10 ou superior; a revisão usa Python 3.13.
A fonte recebida deve estar em `data/raw/instance_desafio_minerva.xlsx`. A instalação não baixa
nem modifica essa planilha.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

A otimização exige Gurobi 13 e uma licença válida. `gurobipy` faz parte das dependências;
a disponibilidade da licença depende do ambiente. As etapas analíticas iniciais podem ser
lidas sem resolver os problemas de otimização.

## Ordem das etapas

Execute cada notebook com um kernel limpo. Reexecute as etapas posteriores quando uma fonte mudar.

```bash
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/1.0-minerva-eda-preparacao.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/2.0.1-minerva-modelo-preditivo.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.0-minerva-otimizacao-precos.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/3.1-minerva-simulacao-relaxacoes.ipynb --ExecutePreprocessor.timeout=300
.venv/bin/python scripts/update_project_report.py
```

O último comando atualiza os relatórios a partir dos artefatos persistidos, incluindo benchmark
e sensibilidade. Ele não ajusta modelos nem consulta diretamente o holdout.

## Verificações e site

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/update_project_report.py --check
.venv/bin/python -m mkdocs build --config-file docs/mkdocs.yml --strict
.venv/bin/python -m mkdocs serve --config-file docs/mkdocs.yml
```

`docs/hooks.py` incorpora figuras e tabelas diretamente de `reports/`. O HTML em `site/`
é gerado. Somente os quatro notebooks listados definem a entrega atual; modelos históricos
usados pelos testes ficam em `tests/fixtures/legacy/`.
