PYTHON ?= .venv/bin/python
NBCONVERT = $(PYTHON) -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300
NOTEBOOKS = \
	notebooks/1.0-minerva-eda-preparacao.ipynb \
	notebooks/2.0-minerva-modelo-preditivo.ipynb \
	notebooks/3.0-minerva-otimizacao-precos.ipynb \
	notebooks/3.1-minerva-simulacao-relaxacoes.ipynb

.DEFAULT_GOAL := help
.PHONY: help requirements test lint format data notebooks report report-check docs clean

help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

requirements: ## Instala as dependências no ambiente .venv
	$(PYTHON) -m pip install -r requirements.txt

test: ## Roda os testes automatizados
	$(PYTHON) -m pytest -q

lint: ## Verifica formatação e lint do código em src/
	$(PYTHON) -m ruff format --check
	$(PYTHON) -m ruff check

format: ## Aplica as correções automáticas de lint e formatação
	$(PYTHON) -m ruff check --fix
	$(PYTHON) -m ruff format

data: ## Executa somente a etapa 1.0 (preparação e EDA)
	$(NBCONVERT) notebooks/1.0-minerva-eda-preparacao.ipynb

notebooks: ## Reexecuta as quatro etapas em ordem (usa Gurobi; leva tempo)
	@for nb in $(NOTEBOOKS); do $(NBCONVERT) $$nb || exit 1; done

report: ## Atualiza os resumos a partir dos artefatos persistidos
	$(PYTHON) scripts/update_project_report.py

report-check: ## Falha se os resumos estiverem defasados
	$(PYTHON) scripts/update_project_report.py --check

docs: ## Gera o site em site/ com verificação estrita de links
	$(PYTHON) -m mkdocs build --config-file docs/mkdocs.yml --strict

clean: ## Remove caches e arquivos compilados locais
	find . -path ./.venv -prune -o \( -name '__pycache__' -o -name '*.py[co]' \) -print | xargs rm -rf
	rm -rf .pytest_cache .ruff_cache
