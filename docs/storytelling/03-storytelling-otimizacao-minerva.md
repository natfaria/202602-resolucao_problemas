# Otimização de preços: resumo das etapas 3.0 e 3.1

<!-- Gerado por scripts/update_project_report.py; atualize os artefatos, não os números à mão. -->

Resumo das etapas de otimização de referência (`notebooks/3.0-minerva-otimizacao-precos.ipynb`)
e de flexibilizações (`notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`). O planejamento
escolhe um preço por dia útil, de 03 a 14/11/2025, para maximizar a margem prevista pela curva
`P3-power-grouped-dias-uteis`, sujeito às regras da instância.

## Resultado

- **Sem flexibilização não há plano.** O maior volume previsto é 76,99 kg
  na primeira semana e 84,62 kg na segunda. O mínimo é
  115,50 kg por semana, e o máximo, 214,50 kg.
- **Flexibilizar um limite por vez:**
  - Limite da primeira mudança: é preciso chegar a R$ 44,39/kg para existir plano.
    Sem esse limite, a margem prevista é R$ 48.917,58.
  - Variação entre dias consecutivos: plano a partir de R$ 24,67/kg, com margem de
    R$ 43.847,13 no menor limite viável.
  - Mínimo semanal: plano a partir de 76,99 kg por semana, com margem de
    R$ 33.336,94.
  - Máximo semanal: sozinho, não permite plano até o limite testado.
- **Referência teórica:** sem as regras operacionais e com extrapolação da faixa de preços, a
  margem máxima é R$ 50.432,89. Esse caso não cumpre as
  regras originais.
- **Premissas:** com as premissas alteradas (demanda, custo, imposto e elasticidade), a margem
  reotimizada fica entre R$ 19.120,76 e R$ 85.227,21.

## Limites

- A alíquota de 7% é hipótese do projeto; a planilha não traz imposto.
- O custo unitário é constante nos dez dias e igual ao do último dia do treino.
- Estoque, capacidade, validade e transferência de compras entre dias não são modelados.
- A margem é prevista pela curva congelada. O realizado não mostra o volume que seria vendido
  nos preços sugeridos, então a comparação com novembro não mede ganho real.
- Um plano ótimo vale para as entradas e tolerâncias da instância; não garante o resultado real.

## Onde estão os detalhes

- `notebooks/3.0-minerva-otimizacao-precos.ipynb`: caso original, uma regra por vez
  e comparação com o holdout.
- `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`: menores flexibilizações,
  combinações e alternativas comparadas.
- [Modelo matemático](../modelo-matematico-otimizacao-precos.md): formulação das restrições.
