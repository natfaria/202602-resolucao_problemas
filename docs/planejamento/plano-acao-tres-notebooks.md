# Fluxo analítico e entregas do projeto

## Finalidade

Entregar uma análise reproduzível de demanda e uma ferramenta de planejamento de preços para
`Produto_A` em dez dias úteis. O preço diário é escolhido para maximizar a margem prevista,
considerando calendário, imposto, custo, metas semanais e mudanças de preço.

## Etapas e responsabilidades

| Etapa | Notebook | Responsabilidade |
|---|---|---|
| Exploração e preparação | `1.0-minerva-eda-preparacao.ipynb` | Auditar dados, produzir variáveis, separar desenvolvimento e holdout e examinar hipóteses |
| Demanda preditiva | `2.0.1-minerva-modelo-preditivo.ipynb` | Selecionar a curva por validação cruzada temporal, calibrar smearing e publicar o artefato |
| Otimização de referência | `3.0-minerva-otimizacao-precos.ipynb` | Definir objetivo, restrições e premissas; resolver casos de referência e exportar as entradas |
| Flexibilizações graduais | `3.1-minerva-simulacao-relaxacoes.ipynb` | Quantificar mínimos de viabilidade, curvas de margem e combinações parciais de regras |

A numeração identifica as etapas. A otimização de referência apresenta casos pontuais e regras
mantidas ou removidas. O estudo de flexibilizações mede quanto alterar cada limite e o efeito de
alterações simultâneas. Ambos usam o mesmo solver e as mesmas fontes.

## Contratos de dados

1. A preparação publica `data/processed/minerva_modelagem_treino.csv`,
   `data/interim/minerva_restricoes.csv` e o holdout isolado.
2. O preditivo publica `models/preditivo_diario/curva_demanda.json`, com coeficientes, calendário,
   smearing, suporte de preço, informações de seleção e hashes.
3. A otimização recebe a curva, o treino registrado e as restrições. Publica
   `models/otimizacao/entradas_planejamento.json`, que congela custo, imposto, preço anterior,
   metas, tolerâncias, limites de mudança, calendário e referências às fontes.
4. O estudo de flexibilizações recebe esse artefato. A curva é carregada do caminho registrado,
   e os hashes da curva, do treino, das restrições e das próprias entradas são conferidos.

Cada notebook pode executar com seus arquivos de entrada e um kernel limpo. A atualização de uma
fonte exige regenerar os artefatos das etapas posteriores; entradas incompatíveis são rejeitadas.
Nenhum coeficiente deve ser transcrito manualmente entre as etapas.

## Protocolo preditivo

A validação cruzada temporal tem seis origens semanais, ajuste expansivo e horizonte de duas
semanas. O WMAPE diário nos dias úteis é o critério principal; RMSE, viés e WMAPE semanal são
complementares. Os coeficientes usam todas as observações anteriores à origem. O smearing usa
somente resíduos dos dias úteis daquele ajuste. O domínio publicado é segunda a sexta.

## Premissas econômicas e operacionais

- Custo unitário igual a custo realizado dividido pelo volume do último dia de treino, mantido
  durante o horizonte.
- Preço anterior igual a receita dividida pelo volume da mesma data, com sua referência temporal.
- Imposto de 7% sobre a receita como premissa explícita.
- Metas e tolerância principal lidas da instância; tolerância de 5% examinada como sensibilidade.
- Mudanças entre decisões consecutivas; a primeira transição é uma regra separada.
- Preços contínuos e volumes definidos pela curva, incluindo seu smearing.
- Demanda prevista atendida integralmente; sem estoque, capacidade ou efeitos entre dias.
- Extrapolação somente em cenários explicitamente identificados na otimização de referência.

## Avaliação e verificação

O preditivo salva o modelo antes de avaliar o holdout. A otimização salva as decisões antes da
comparação gráfica com preços e volumes reais. O estudo de flexibilizações não lê o holdout.
A comparação observacional não revela o volume que teria sido vendido sob preços alternativos.

As soluções são recomputadas fora do solver. Todo plano deve conservar a identificação da curva,
das entradas e das regras alteradas. Inviabilidade provada, solução factível sem certificado e
ausência de solução encontrada são resultados distintos.

## Documentação de cada etapa

- [Modelo matemático e econômico](modelo-matematico-otimizacao-precos.md).
- [Otimização de referência e cenários](plano-otimizador-margem.md).
- [Flexibilizações graduais](plano-simulacao-relaxacoes.md).
