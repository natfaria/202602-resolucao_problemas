# Modelos históricos usados somente em testes

Estes quatro artefatos preservam os casos de regressão e compatibilidade já existentes:

- `demand_curve_champion.json`: partição de calendário histórica.
- `demand_curve_champion_livro.json`: contrato de artefato versão 1 e referência da otimização anterior.
- `demand_curve_uncertainty_livro.json`: cenários vinculados ao núcleo histórico.
- `curva_demanda_preditivo.json`: curva da versão preditiva anterior, comparada à atual nos testes do Gurobi.

Os arquivos foram transferidos de `models/` sem alterar seus conteúdos. Não são entradas
dos quatro notebooks atuais. A curva de execução está em `models/preditivo_diario/curva_demanda.json`.
