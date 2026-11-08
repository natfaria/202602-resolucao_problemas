# Plano do otimizador de margem

## 1. Resultado esperado

Produzir uma análise reproduzível que escolha os dez preços diários de `Produto_A` para 03/11 a
14/11/2025, maximize a margem de contribuição prevista e mostre o efeito das regras de volume,
estabilidade, ligação inicial e suporte de preço. Os resultados devem distinguir as condições
observadas das hipóteses usadas em cada simulação.

O desenvolvimento contém somente informações até 31/10/2025. O preditivo permanece congelado em
`models/preditivo_diario/curva_demanda.json`. Os dados realizados de novembro são usados apenas depois
da definição das políticas, para comparação descritiva e avaliação preditiva.

## 2. Entradas do problema

| Entrada | Regra |
|---|---|
| Demanda | Curva de potência, calendário, smearing e suporte lidos do artefato |
| Integridade | Conferir hash do núcleo da curva e da base de treino registrada |
| Preço anterior | Receita/volume do último dia de treino: R$ 1.318,919594425694/kg |
| Custo unitário | Custo/volume do último dia de treino: R$ 1.010,4468382320078/kg |
| Custo no horizonte | Mesmo custo unitário nos dez dias |
| Imposto | 7% sobre a receita, hipótese explícita diante da ausência da coluna na fonte |
| Meta semanal | 165 kg em cada uma das duas semanas |
| Tolerância | 30% na análise principal; 5% na sensibilidade |
| Variação interna | R$ 2/kg entre decisões consecutivas |
| Ligação inicial | R$ 2/kg entre o preço anterior e a primeira decisão |
| Preço | Contínuo, dentro do suporte por contexto quando essa regra estiver ativa |

O custo é uma premissa definida pelo último dia de treino, e não um método escolhido por
comparação de previsores. Não se utiliza custo realizado em novembro para selecionar preços.
Os valores são calculados a partir dos dados, sem copiar coeficientes arredondados ou retirar a
correção da retransformação da demanda.

## 3. Acréscimo ao EDA: faixas de preço

A relação preço-volume deve incluir uma análise por faixas de **R$ 25/kg**, usando apenas o
conjunto de desenvolvimento. A finalidade é reconhecer dispersão, cobertura e hipóteses; não é
selecionar automaticamente uma nova curva ou identificar efeito causal.

A análise deve apresentar:

- os pontos individuais de preço e volume;
- quantidade de observações por faixa;
- volume médio, mediano e intervalo interquartil;
- decomposição por calendário, sem impor agrupamentos definitivos ao EDA;
- cobertura temporal de cada faixa, para reconhecer concentração em semanas ou meses;
- indicação de faixas e recortes com poucas observações.

A interpretação deve distinguir associação agregada, composição de calendário e concentração
em períodos específicos. Uma faixa com volume médio alto e pouca cobertura não deve ser
interpretada como evidência suficiente de um regime de demanda. O acréscimo preserva os dados
canônicos e o preditivo congelado.

## 4. Formulação e execução

A formulação está descrita em `modelo-matematico-otimizacao-precos.md`. O objetivo soma a receita
líquida de imposto menos o custo do volume previsto. A igualdade com a curva de demanda impede
que o volume seja escolhido independentemente do preço.

A implementação usa `Scenario` e `solve_scenario`, de `src/optimization/gurobi_solver.py`, com o
contrato de entradas `PriceProblem`. A normalização $u=p/1300$ e a representação exata da receita
em função de volume melhoram a escala numérica. O modelo é contínuo e usa restrições não lineares
nativas; não depende de uma grade de preços.

A execução deve:

1. carregar e validar somente as entradas anteriores ao horizonte;
2. documentar objetivo, restrições e premissas antes dos resultados;
3. resolver o cenário com todas as regras ativas;
4. calcular os limites de volume alcançáveis para explicar eventual inviabilidade;
5. executar os cenários de relaxação e as sensibilidades;
6. recalcular cada solução fora do solver;
7. congelar os planos, parâmetros e resultados;
8. carregar o teste apenas para a comparação final.

## 5. Matriz principal de relaxações

Quatro grupos são tratados de forma independente:

| Grupo | Regra mantida | Regra removida |
|---|---|---|
| Variação interna | Mudança de até R$ 2 entre dias do horizonte | Sem limite interno |
| Metas semanais | Faixa mínima e máxima em cada semana | Sem ambas as metas |
| Ligação inicial | Primeiro preço a até R$ 2 do preço anterior | Primeiro preço livre dessa ligação |
| Suporte observado | Faixa de preços do contexto | Domínio técnico de R$ 800 a R$ 2.000/kg |

As combinações geram **16 cenários**, incluindo:

- relaxar somente a variação interna;
- relaxar a variação interna e as metas;
- combinar essas condições com a retirada da ligação inicial;
- repetir as combinações com extrapolação do suporte observado;
- manter todas as regras e remover todas as quatro regras como referências de comparação.

A retirada da variação interna não remove a primeira ligação. O preço anterior observado não é
alterado silenciosamente para obter uma solução factível. As tabelas mostram quais regras estão
ativas e reportam os volumes em relação às faixas originais, mesmo quando as metas são removidas.

Comparações de margem devem usar o mesmo custo, imposto e curva. A diferença entre o melhor e
o pior plano factível não é apresentada como ganho sobre a operação histórica.

## 6. Preço inicial e tolerância

A análise do preço inicial considera quatro condições:

$$
p^0\in\{1200,1250,1300,1318{,}919594425694\}\ \text{R\$/kg}.
$$

A ligação inicial permanece ativa nessa análise. Cada valor é combinado com as duas condições de
variação interna, metas e suporte, totalizando **32 cenários**. Os valores hipotéticos são
identificados como tais; o valor observado continua sendo a referência do problema-base.

A sensibilidade da tolerância compara a faixa principal de 30% com a faixa de 5%, mantendo os
outros parâmetros explícitos. A análise deve mostrar se o efeito financeiro vem de permitir menos
volume, mais volume ou recuperar a viabilidade; aumentar a tolerância altera os dois lados da faixa.

## 7. Extrapolação e suporte estatístico

Nos cenários de extrapolação, o domínio R$ 800–2.000/kg substitui somente os limites operacionais
de preço da otimização. O suporte original e o hash do artefato não são modificados.

Os resultados devem informar quantos dias estão fora do suporte e marcar essas observações nos
planos e gráficos. Os limites técnicos são usados para manter um problema finito e positivo;
não significam que a regressão tenha sido validada nessa faixa. Eventual solução na fronteira
técnica precisa ser identificada. Curvas e pontos extrapolados são simulações condicionais.

## 8. Gráfico de curva, plano e realizado

O plano usado na comparação é definido antes de consultar o teste: **retirar a ligação inicial e
manter a variação interna, as metas semanais e o suporte observado**. Sua apresentação é
condicionada a essa alteração operacional. Se não existir uma solução validada desse cenário,
não se substitui o plano por outro escolhido com base nos resultados reais.

A figura deve ter **duas linhas e cinco colunas**, representando os dez dias do horizonte. Cada
painel deve conter:

- a curva preditiva correspondente ao calendário daquele dia;
- o ponto do preço escolhido e do volume previsto pelo otimizador;
- o ponto real de teste: preço observado por receita/volume e volume realizado;
- data, semana, eixos em R$/kg e kg/dia, e legenda;
- trechos tracejados para eventual extensão da curva fora do suporte.

Essa disposição mantém visíveis os dez dias mesmo quando vários preços ótimos coincidem. O
ponto otimizado pertence à curva por construção. A posição do ponto real permite avaliar a
previsão nos preços observados; não mede o volume contrafactual nos preços recomendados.

## 9. Qualidade, interpretação e entregáveis

Para cada cenário, registrar:

- condição inicial e regras ativas;
- status de término, melhor objetivo, bound, gap e tempo;
- preços, volumes, custos, impostos e margens diárias, quando houver plano validado;
- totais semanais e folgas em relação às faixas de referência;
- quantidade de dias extrapolados;
- resíduos de demanda, receita e margem recalculados fora do solver;
- identificação dos dados e do núcleo preditivo usados.

Um término por limite de tempo com plano válido é distinguido de uma solução certificada dentro
da tolerância. Não encontrar plano não prova inviabilidade. Cenários certificados como inviáveis
permanecem na comparação com seu diagnóstico, sem uma agenda apresentada como recomendação.

Os entregáveis são o notebook de otimização executado, tabelas e metadados dos cenários, planos
validados, figuras de sensibilidade e o painel diário comparando curva, otimização e teste.
Toda narrativa deve explicar o problema e interpretar os resultados produzidos dentro de seu
próprio contexto.

A etapa está concluída quando o custo do último dia é reproduzido, as 16 combinações e as 32
condições de preço inicial são identificáveis, a tolerância de 5% é comparável à principal, os
planos são verificados e o teste permanece fora da definição de parâmetros e políticas.

## 10. Entradas persistidas e estudo de flexibilizações

O notebook `3.0-minerva-otimizacao-precos.ipynb` exporta
`models/otimizacao/entradas_planejamento.json` antes de otimizar. O arquivo reúne custo, imposto,
preço anterior, regras, horizonte e referências verificáveis à curva, ao treino e às restrições.

O notebook `3.1-minerva-simulacao-relaxacoes.ipynb` recebe esse artefato para calcular mínimos de
viabilidade, curvas graduais e combinações parciais. O estudo mantém o preço anterior real e separa
a mudança inicial da variação interna. Sua execução não usa o holdout e não exige estado de memória
da otimização de referência. O método e as saídas estão em `plano-simulacao-relaxacoes.md`.
