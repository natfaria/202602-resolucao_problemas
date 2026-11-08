# Origem e uso das tabelas

A trilha atual é identificada pelos quatro notebooks do README. As tabelas preditivas atuais estão em `preditivo_diario/`; as tabelas operacionais produzidas pelo Gurobi terminam em `_gurobi.csv`, além de `03_comparacao_otimizador_teste.csv` e `03_sensibilidade_premissas.csv`. `relaxacoes/` contém os mínimos e as combinações graduais.

As tabelas exploratórias `01_*` são produzidas pelo notebook de preparação. Foram removidas
as tabelas de versões anteriores que não fazem parte da trilha atual. O diagnóstico de
viabilidade está em `data/processed/minerva_diagnostico_infactividade.json`.

O relatório é gerado por `scripts/update_project_report.py` a partir dos artefatos atuais, com verificação de hashes. Uma mudança de premissas exige reexecução das etapas e atualização do relatório.
