# Documentação do projeto Minerva

O ponto de entrada é [Planejamento e funcionamento](planejamento/index.md).
As instruções estão em [Instalação e reprodução](planejamento/getting-started.md).

Na raiz do repositório:

```bash
.venv/bin/python scripts/update_project_report.py
.venv/bin/python -m mkdocs build --config-file docs/mkdocs.yml --strict
```

Os relatórios gerados usam as saídas dos quatro notebooks atuais. `antigos/` contém versões
históricas e não integra o site. Seus números não devem ser combinados com a curva atual.
