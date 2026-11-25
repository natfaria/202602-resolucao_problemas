# Curva de demanda: resumo da etapa 2.0

<!-- Gerado por scripts/update_project_report.py; atualize os artefatos, não os números à mão. -->

Resumo da etapa do notebook 2.0 (`notebooks/2.0-minerva-modelo-preditivo.ipynb`). Ela estima,
por validação cruzada temporal, como o preço e o calendário explicam o volume diário em dias úteis,
e publica a curva usada pelo otimizador em `models/preditivo_diario/curva_demanda.json`.

## Resultado

- Modelo escolhido: `P3`, curva de potência com elasticidade compartilhada e um
  nível de demanda por contexto de calendário.
- Elasticidade estimada: `-12,3647`. Mantido o calendário, 1% a mais no preço reduz o
  volume previsto em cerca de 11,58%.
- Na sexta, o nível previsto é cerca de 26,2% do nível de segunda a quinta, no mesmo preço.
- Erro na validação cruzada: WMAPE diário médio de 36,85%.
- Holdout de dez dias úteis: WMAPE diário de 37,24% e semanal de
  18,55%. Nas duas semanas, o modelo subestima o volume total.
- Referência sem preço (média do mesmo dia da semana): WMAPE diário médio de 59,70%.

## Limites

- A relação é observacional. Ela não mede o efeito causal do preço nem considera estoque,
  promoções, concorrência ou preço de lista.
- Os erros descrevem desempenho observado. Não garantem que as metas semanais serão atingidas.
- A curva vale apenas para dias úteis e para a faixa de preços observada no treino:

- Segunda a Quinta: de R$ 1.201,63 a R$ 1.352,42/kg.
- Sexta: de R$ 1.208,37 a R$ 1.365,49/kg.

- O holdout foi usado uma única vez, depois do congelamento da curva. Uma nova avaliação final
  exige observações posteriores.

## Onde estão os detalhes

- `notebooks/2.0-minerva-modelo-preditivo.ipynb`: validação, comparação de
  candidatos, diagnósticos e holdout.
- [Modelo matemático](../modelo-matematico-otimizacao-precos.md): formulação usada pelo otimizador.
- [Referências](../referencias-bibliograficas.md).
