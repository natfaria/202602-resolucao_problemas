# Origem e uso das tabelas

A trilha atual é identificada pelos quatro notebooks do README. As tabelas preditivas atuais estão em `preditivo_diario/`; as tabelas operacionais produzidas pelo Gurobi terminam em `_gurobi.csv`, além de `03_comparacao_otimizador_teste.csv` e `03_sensibilidade_premissas.csv`. `relaxacoes/` contém os mínimos e as combinações graduais.

Os arquivos antigos `02_*`, `02b_*`, `021_*`, `022_*`, `031_*`, `03_diagnostico_aninhado.csv`, `03_envelope_oficial_diario.csv`, `03_relaxacoes_minimas.csv` e demais tabelas anteriores não identificadas pela trilha atual são históricos. Não os combine com a curva publicada em `models/preditivo_diario/`. O diagnóstico atual é `data/processed/minerva_diagnostico_infactividade.json`.

O relatório é gerado por `scripts/update_project_report.py` a partir dos artefatos atuais, com verificação de hashes. Uma mudança de premissas exige reexecução das etapas e atualização do relatório.
