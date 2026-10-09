# Plano de execução: simulação de relaxações para recuperar a factibilidade com a melhor margem

## 1. Objetivo

O problema oficial (10 dias úteis, meta semanal de 165 kg ± 30%, variação de preço de R$ 2 entre
decisões consecutivas, suporte da curva rígido) é infactível. O objetivo desta etapa é descobrir
**onde relaxar, e quanto, para tornar o problema factível com a maior margem possível**, incluindo
combinações parciais de relaxações.

Esta etapa é **determinística**. Não há otimização sob incerteza: usa-se a curva central congelada, o
custo selecionado no Notebook 3 e a alíquota-base. Cenários de demanda ficam fora do escopo.

### Pergunta orientadora

> Para cada regra afrouxada isoladamente, qual é o menor afrouxamento que torna o problema factível,
> qual margem ele entrega e quanta margem adicional cada pedaço extra de folga compra? E quais
> combinações de relaxações parciais dominam as relaxações isoladas?

### Cuidado conceitual

Afrouxar uma regra nunca reduz a margem ótima. Portanto "a relaxação de maior margem" é sempre
"relaxar tudo". O estudo apresenta o **trade-off** entre folga concedida e margem obtida. A escolha do
ponto de operação depende de um limite de relaxação aceitável pelo negócio, que não sai do modelo.

## 2. Escopo e premissas

| Item | Decisão |
|---|---|
| Curva de demanda | `models/demand_curve_champion_livro.json`, central, sem reestimação |
| Suporte de preço | Rígido. Pode aparecer apenas como sensibilidade, rotulada como extrapolação |
| Custo | Previsão selecionada no Notebook 3 (`media_4_semanas`, R$ 988,84/kg) |
| Imposto | 7% (premissa), parâmetro genérico `tax_rate` |
| Horizonte | 10 dias úteis, 03/11 a 14/11/2025; preço anterior R$ 1.318,92 (31/10) |
| Incerteza | Fora do escopo |
| Regra de "dia" | Base: dia de decisão. Sensibilidade: dia corrido (ver 3.3) |

## 3. Regras a relaxar

### 3.1 Relaxações isoladas

| Id | Regra | Nominal | Observação |
|---|---|---|---|
| R1 | Variação diária entre decisões (Δ) | R$ 2 | Mínimo viável conhecido ≈ R$ 16,10 |
| R2 | Preço inicial (`|p1 − p0|`) | R$ 2 | Mínimo viável conhecido ≈ R$ 41,48 |
| R3 | Piso de volume semanal | 115,5 kg | Causa a infactibilidade |
| R4 | Teto de volume semanal | 214,5 kg | Não afeta a factibilidade; afeta a margem |
| R5 | Meta nominal (tolerância mantida em 30%) | 165 kg | Piso e teto deslocam-se juntos |

R3 e R4 separam os dois lados da tolerância simétrica. A tolerância simétrica é o efeito somado das
duas e pode ser reconstituída a partir delas.

### 3.2 Combinações

Relaxações parciais simultâneas (ex.: preço inicial × variação diária, variação diária × piso,
preço inicial × piso). Com três ou mais regras, fixar uma e variar as outras em fatias.

### 3.3 Definição de "dia" na regra de R$ 2

O enunciado fala em "dias consecutivos" sem definir. A leitura base é **dia de decisão**: cada par de
preços consecutivos na sequência varia no máximo R$ 2, inclusive sexta → segunda e 31/10 → 03/11.
A leitura alternativa é **dia corrido**: o limite é R$ 2 vezes o número de dias do calendário entre
decisões (sexta → segunda = R$ 6). Verificação preliminar mostra que o volume máximo alcançável passa
de 79,2 / 87,1 kg para 82,2 / 93,9 kg, ainda abaixo do piso. A interpretação muda os números, não a
conclusão de infactibilidade. Será rodada como cenário de sensibilidade e registrada como pergunta em
aberto para a Minerva.

## 4. Entregáveis

| Arquivo | Conteúdo |
|---|---|
| `src/optimization/relaxation_study.py` | Funções de relaxação, curvas e grades de combinação |
| `tests/test_relaxation_study.py` | Testes dos contratos principais |
| `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb` | Narrativa, curvas, combinações e conclusão |
| `reports/tables/03b_*.csv` | Tabelas de curvas, θ mínimos, combinações, ranking e convergência do multi-start (`03b_multistart.csv`) |
| `reports/figures/03b_*.png` | Curvas de sensibilidade, mapa de combinações, ranking |
| `data/processed/minerva_simulacao_relaxacoes.json` | Resultado consolidado com hash da curva |

## 5. Etapas de execução

### Etapa 0. Preparação e linha de base

1. Reproduzir os números já conhecidos do Notebook 3 como referência de regressão:
   - envelope oficial: 79,20 kg e 87,05 kg;
   - Δ diário mínimo ≈ R$ 16,0987, margem ≈ R$ 52.073;
   - salto inicial mínimo ≈ R$ 41,4756, margem ≈ R$ 46.421;
   - sem ligação inicial: margem ≈ R$ 59.294;
   - sem meta: margem ≈ R$ 37.888.
2. Registrar essas referências em teste, para detectar regressões ao generalizar o código.

### Etapa 1. Generalizar o problema

Estender `PriceProblem` e o otimizador, sem alterar o comportamento padrão:

1. Tolerância inferior e superior separadas (`tolerance_lower`, `tolerance_upper`), com padrão igual
   à tolerância atual.
2. Meta nominal como parâmetro relaxável por semana.
3. Limite de variação por transição (vetor), para suportar a leitura de dia corrido
   (`gap_dias` entre decisões).
4. Uma estrutura `Relaxation` que descreva todas as folgas de uma rodada (Δ diário, salto inicial,
   fator do piso, fator do teto, fator da meta nominal).
5. Função única `solve(problem, relaxation, n_starts=10)` que devolve: status, margem, plano diário,
   volumes semanais, folgas de cada restrição e restrições ativas, além da margem obtida por cada
   ponto inicial. Nunca devolve plano se infactível. O número de pontos iniciais é um parâmetro
   explícito, com padrão 10 (o código atual usa 8, valor sem justificativa técnica).

### Etapa 2. Mínimos de factibilidade (θ_min)

Para cada regra R1 a R5, isoladamente, calcular o menor afrouxamento que torna o problema factível
(bisseção sobre o diagnóstico de envelopes, já existente). Reportar também o valor em % do nominal.
Saída: `03b_theta_minimo.csv`.

### Etapa 3. Curvas de sensibilidade por regra

1. Para cada regra, criar uma grade de valores de θ a partir de θ_min até um valor máximo razoável:

   | Regra | Faixa sugerida |
   |---|---|
   | R1 Δ diário | R$ 2 a ~R$ 30 |
   | R2 preço inicial | R$ 2 a ~R$ 110 |
   | R3 piso | ~70 kg a 115,5 kg |
   | R4 teto | 214,5 kg a ~300 kg |
   | R5 meta nominal | de 165 kg até o valor em que deixa de afetar a margem |

2. Em cada ponto, resolver o problema e registrar margem, volumes semanais e restrições ativas.
3. Pontos abaixo de θ_min ficam marcados como infactíveis e **não são excluídos** da tabela.
4. Gerar um gráfico por regra e um painel comparativo. O eixo y é o mesmo em todos os painéis.
5. Calcular, por regra: margem em θ_min, margem no limite (regra removida), inclinação logo após
   θ_min e ponto em que a curva achata.

Saídas: `03b_curvas_relaxacao.csv`, `03b_curvas_relaxacao.png`.

### Etapa 4. Ranking comparável

Para responder "qual regra tem mais efeito sobre a margem":

1. **Critério A:** margem em θ_min (custo de "pagar" a infactibilidade).
2. **Critério B:** ganho de margem por 1% de afrouxamento em relação ao nominal, logo após θ_min.
3. **Critério C:** margem máxima atingível quando a regra é totalmente removida.

Apresentar os três lado a lado. Não somar penalidades de unidades diferentes em uma nota única.
Saída: `03b_ranking_relaxacoes.csv`.

### Etapa 5. Combinações

1. Grades bidimensionais: (R2 × R1), (R1 × R3), (R2 × R3), com piso e teto fixos nos demais.
2. Para cada ponto: factível ou não, margem e déficit total de volume quando infactível.
3. Mapa de calor da margem sobre o plano das duas regras, com a fronteira de factibilidade.
4. Fronteira de Pareto entre as relaxações (cada eixo na sua unidade), reaproveitando
   `pareto_relaxations`.
5. Para cada fronteira, destacar a combinação de maior margem dentro de orçamentos de relaxação
   ilustrativos (ex.: 25%, 50% e 100% do valor de θ_min de cada regra), deixando claro que o orçamento
   é uma hipótese a ser definida pelo negócio.

Saídas: `03b_combinacoes.csv`, `03b_pareto.csv`, `03b_mapa_combinacoes.png`.

### Etapa 6. Sensibilidades complementares

1. Regra de dia corrido (3.3): repetir etapas 2 e 3 e comparar com a leitura base.
2. Alíquota de 0%, 5% e 10% sobre as curvas das etapas 2 e 3 (0% descrito como margem antes de
   impostos).
3. Suporte relaxado (opcional): ver quanto ele pesaria, rotulado como extrapolação sem validade.

### Etapa 7. Verificações

1. Recomputar objetivo e todas as restrições de cada solução, independentemente do solver.
2. A margem deve ser **não decrescente** em θ para cada regra (relaxar nunca piora).
3. **Análise de multi-start.** Cada problema resolvido (todo ponto das curvas e das grades) usa
   **10 pontos iniciais** e semente fixa (`seed=42`), com a seguinte composição:
   - 3 determinísticos: trajetória de preços mais baixa alcançável, mais alta alcançável e a média
     das duas;
   - 7 sorteados, combinando as trajetórias baixa e alta com pesos aleatórios.

   Para cada ponto, registrar a margem obtida por cada início (ou "falhou"/"infactível" quando o
   início não converge para uma solução válida) em `03b_multistart.csv`. Critérios de aceitação:
   - a diferença entre a maior e a menor margem entre os inícios que convergem para solução válida
     deve ser menor que R$ 1,00;
   - pelo menos 80% dos inícios devem convergir para a melhor solução (dentro dessa tolerância);
   - o preço de cada dia na solução final não pode diferir mais de R$ 0,05 entre os inícios que
     atingem a melhor margem.

   Se algum ponto violar um desses critérios, aumentar o número de inícios para esse ponto (dobrando
   até um máximo de 40) e registrar o caso. Se ainda assim não houver convergência, marcar o ponto
   como "ótimo local não confirmado" e conferir com busca em grade de preços ou verificação
   independente (ex.: solver global opcional).
4. Nenhum plano diário pode ser emitido para um ponto infactível.
5. Conferir que os pontos de regressão da etapa 0 continuam reproduzidos.
6. Conferir que os resultados não dependem de estado de outro notebook.

### Etapa 8. Notebook e relatório

Seguir o protocolo do plano principal: antes de cada tabela ou gráfico, uma célula Markdown com a
pergunta, a justificativa e as limitações; depois, outra com a interpretação dos valores produzidos.
A conclusão deve separar o que vem dos dados históricos, o que é premissa operacional e o que é
resultado matemático, e deve listar o que depende de decisão do negócio.

## 6. Testes automatizados

Em `tests/test_relaxation_study.py`:

1. Os valores de referência da etapa 0 continuam reproduzidos.
2. Tolerâncias separadas com valores iguais reproduzem o resultado da tolerância simétrica.
3. Margem não decrescente ao afrouxar cada regra.
4. θ_min de cada regra torna o problema factível, e um valor ligeiramente menor, infactível.
5. Leitura de dia corrido amplia a variação sexta → segunda e não altera os demais passos.
6. Nenhum plano é devolvido em caso de infactibilidade.
7. O multi-start usa exatamente 10 inícios (3 determinísticos e 7 sorteados) e é reproduzível com a
   mesma semente.
8. Em um problema conhecido (por exemplo, o do salto inicial mínimo), as margens dos 10 inícios que
   convergem diferem em menos de R$ 1,00.

## 7. Critério de conclusão

A etapa está concluída quando: (a) os números de referência do Notebook 3 são reproduzidos; (b) cada
regra tem θ_min e uma curva de margem com eixos comparáveis; (c) existe um ranking com os três
critérios; (d) as combinações e a fronteira de Pareto estão calculadas; (e) a leitura de dia corrido e
a sensibilidade de imposto estão documentadas; (f) os testes passam; (g) o notebook roda do início ao
fim sem depender do estado de outros notebooks.

## 8. Decisões em aberto

1. Eixos em valor absoluto (R$, kg) ou em % do nominal nos gráficos? Sugestão: mostrar ambos, com
   o ranking em %.
2. Qual limite de relaxação o negócio aceita para cada regra? Define o orçamento da etapa 5.
3. A leitura de dia corrido é a leitura correta do enunciado? Consultar a Minerva.
4. Preços podem ser contínuos ou precisam respeitar incrementos comerciais?
5. Os fins de semana farão parte de horizontes futuros?

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Otimizador local (SLSQP) preso em solução subótima | Multi-start com 10 inícios e critérios de convergência (etapa 7, item 3); conferência por busca em grade de preços nos casos críticos |
| Ótimo no extremo do suporte, onde há poucos dados | Reportar a proximidade de cada preço ao limite do suporte em todas as soluções |
| Margem prevista pela curva não é margem realizada | Rotular como "prevista"; não comparar diretamente com margem do holdout |
| Elasticidade alta (−12,4) e curva observacional | Resultados condicionais à curva; nenhuma alegação causal |
| Ranking sensível às faixas escolhidas | Usar eixos em % e reportar três critérios, não um só |
