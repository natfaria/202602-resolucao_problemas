# Documentação do projeto Minerva

O ponto de entrada é [Planejamento e funcionamento](planejamento/index.md).
As instruções estão em [Instalação e reprodução](planejamento/getting-started.md).

A leitura narrativa está organizada em três documentos na pasta `storytelling/`:

- [Análise exploratória](storytelling/storytelling-eda-minerva.md).
- [Curva de demanda](storytelling/curva-de-demanda-modelo-2-0.md).
- [Otimização e horizonte rolante](storytelling/storytelling-otimizacao-minerva.md).

Na raiz do repositório:

```bash
.venv/bin/python scripts/update_project_report.py
.venv/bin/python -m mkdocs build --config-file docs/mkdocs.yml --strict
```

Os relatórios gerados usam as saídas dos quatro notebooks atuais. Os únicos modelos históricos
mantidos ficam em `tests/fixtures/legacy/` para testes de compatibilidade e regressão.
