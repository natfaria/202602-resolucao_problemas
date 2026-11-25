# Modelo matemático de otimização de preços

## 1. Decisão e objetivo

O modelo determina um preço por quilograma para cada um dos dez dias úteis de 03/11 a
14/11/2025. Os preços são escolhidos conjuntamente para maximizar a margem de contribuição
prevista nas duas semanas. A curva de demanda transforma cada preço em uma quantidade esperada
de vendas; o volume não é uma decisão independente.

A margem diária corresponde à receita após imposto, menos o custo dos quilos vendidos. A
maximização considera valores monetários acumulados, e não receita bruta, margem percentual ou
volume isoladamente. As restrições de estabilidade e volume conectam as decisões dos dez dias.

## 2. Entradas congeladas

A curva é carregada de `models/preditivo_diario/curva_demanda.json`. Seu núcleo é verificado por
`model_core_sha256`; a base de desenvolvimento é conferida pelo `training.data_sha256` registrado
no mesmo artefato. A otimização não reestima coeficientes nem modifica o faixa de preços observada no treino.
Os identificadores congelados são:

- núcleo preditivo: `d5b658c7654bee68f0cd706d7a75b846c0a41d9fe542e66f326a80fb6daa0385`;
- base de treino: `ed5fb2cba0b14c38317d2e2a44d830843c95b0bb5911f6ec30da7997520e9b1c`.

| Entrada | Definição no horizonte |
|---|---|
| Produto | `Produto_A` |
| Dias | Dez dias úteis, de 03/11 a 14/11/2025 |
| Semanas | 03 a 07/11 e 10 a 14/11, verificadas separadamente |
| Preço anterior observado | R$ 1.318,919594425694/kg, reconstruído em 31/10/2025 |
| Custo unitário | R$ 1.010,4468382320078/kg em todos os dias da instância, calculado em 31/10/2025 |
| Imposto | 7% sobre a receita, como hipótese explícita |
| Meta por semana | 165 kg |
| Tolerância principal | 30% abaixo e acima da meta: 115,5 a 214,5 kg |
| Sensibilidade de tolerância | 5%: 156,75 a 173,25 kg |
| Variação interna | Até R$ 2/kg entre decisões consecutivas, quando ativa |
| Limite da primeira mudança | Até R$ 2/kg entre o preço anterior e a primeira decisão, quando ativa |

O custo unitário da instância é **o custo unitário do último dia de treino**, igual nos dez dias:
$c_t=c$. A formulação aceita um custo $c_t$ por dia, mas a Minerva informa um custo fixo, e é esse
valor que a instância usa:

$$
c=\frac{\text{custo realizado em 31/10}}{\text{volume realizado em 31/10}}
=\frac{8232{,}07116996}{8{,}14696118438429}
=1010{,}4468382320078\ \text{R\$/kg}.
$$

O custo total desse dia não deve ser interpretado como custo por kg. O preço anterior é calculado
pela razão entre receita e volume da mesma data. Nenhum custo, preço ou volume realizado
no horizonte é usado para definir esses parâmetros. A instância não contém uma coluna de imposto;
portanto, a alíquota de 7% é uma premissa econômica, não uma medida reconstruída da fonte.

## 3. Conjuntos, parâmetros e variáveis

- $T=\{1,\ldots,10\}$ é o conjunto ordenado de decisões.
- $W=\{1,2\}$ contém as semanas; $T_1=\{1,\ldots,5\}$ e $T_2=\{6,\ldots,10\}$.
- $c(t)$ identifica o contexto do dia: segunda a quinta ou sexta.
- $p^0$ é o preço anterior observado ou o valor hipotético declarado no cenário.
- $c_t$ é o custo unitário do dia $t$; na instância, $c_t=c$ para todo $t$. $\tau=0{,}07$ é a alíquota sobre receita.
- $L_w$ e $U_w$ são os limites semanais obtidos da meta e tolerância.
- $\Delta=2$ limita as mudanças internas; $\Delta_0=2$ limita a primeira mudança.
- $[\underline p_{c(t)},\overline p_{c(t)}]$ é o faixa de preços observada no treino do contexto.
- $p_t>0$ é o preço contínuo escolhido para o dia $t$.
- $q_t$ é o volume derivado da curva; $g_t$ é a margem de contribuição prevista.

A ordem de $T$ representa decisões consecutivas. Assim, a sexta-feira e a segunda-feira seguinte
são adjacentes na restrição de variação; o limite não é multiplicado pelo número de dias corridos.

## 4. Demanda recebida do preditivo

A demanda diária em kg é:

$$
D_t(p)=SF\exp(\beta_0+\gamma_{c(t)})p^\beta,
$$

com $\beta=-12{,}364695401293016$, $\beta_0=91{,}59146121459447$ e
$SF=1{,}0912057454522903$. O efeito de contexto é zero de segunda a quinta e
$-1{,}3394398892280646$ na sexta. O fator $SF$ corrige a retransformação da escala logarítmica
para o nível de volume e participa das metas e da margem. Ele é a média dos resíduos exponenciados
nos 66 dias úteis do treino; os coeficientes usam todas as 76 observações de desenvolvimento.
A curva foi selecionada por WMAPE diário na validação cruzada temporal e admite previsões
somente de segunda a sexta.

Os coeficientes, o fator de correção e os limites de preço são lidos com a precisão do artefato.
Os limites aproximados são:

| Contexto | Menor preço observado (R$/kg) | Maior preço observado (R$/kg) |
|---|---:|---:|
| Segunda a quinta | 1.201,63 | 1.352,42 |
| Sexta | 1.208,37 | 1.365,49 |

Para a implementação, uma expressão numericamente mais estável da mesma curva é:

$$
D_t(p)=d_t^{ref}\left(\frac{p}{p^{ref}}\right)^\beta,
\qquad p^{ref}=1300,
\qquad d_t^{ref}=D_t(1300).
$$

O volume de referência é aproximadamente 20,5405369 kg de segunda a quinta e 5,3814640 kg na sexta.
A normalização não altera as previsões.

## 5. Formulação com todas as regras ativas

$$
\max_{p,q}\quad \sum_{t\in T}g_t
=\sum_{t\in T}\big[(1-\tau)p_t-c_t\big]q_t
$$

sujeito a:

$$
q_t=D_t(p_t),\qquad t\in T,
$$

$$
L_w\le\sum_{t\in T_w}q_t\le U_w,\qquad w\in W,
$$

$$
-\Delta\le p_t-p_{t-1}\le\Delta,\qquad t=2,\ldots,10,
$$

$$
-\Delta_0\le p_1-p^0\le\Delta_0,
$$

$$
\underline p_{c(t)}\le p_t\le\overline p_{c(t)},\qquad t\in T.
$$

A meta não exige exatamente 165 kg; exige o atendimento da faixa em **cada** semana. Substituir o
vínculo de demanda por $q_t\le D_t(p_t)$ permitiria recusar vendas e modificaria o significado do
problema. Não há variável de recusa nem controle de estoque nesta formulação.

## 6. Relaxações e condições iniciais

Cada cenário ativa ou remove quatro grupos de regras independentemente:

| Grupo | Mantido | Relaxado |
|---|---|---|
| Variação interna | $\lvert p_t-p_{t-1}\rvert\le2$, $t\ge2$ | Sem limite entre decisões internas |
| Metas semanais | $L_w\le\sum q_t\le U_w$ | Sem mínimo e sem máximo semanal |
| Limite da primeira mudança | $\lvert p_1-p^0\rvert\le2$ | Primeiro preço sem ligação ao histórico |
| Suporte de preço | Faixa observada do contexto | Domínio técnico de R$ 800 a R$ 2.000/kg |

A comparação principal reúne **15 cenários**: o caso original, as retiradas individuais dos grupos de primeira mudança, mudanças internas e faixa de preços, e as combinações de dois ou mais grupos. A retirada conjunta de mínimo e máximo semanal aparece apenas nas combinações com outras mudanças. A tabela de retiradas isoladas examina separadamente o mínimo e o máximo semanal. O preço histórico permanece como referência em todos esses casos. A demanda e a função objetivo permanecem
iguais em todos eles. Remover a variação interna não remove automaticamente a limite da primeira mudança.
As metas e o suporte original continuam sendo reportados como referências mesmo quando suas
restrições são removidas.

A sensibilidade do preço anterior usa $p^0\in\{1200,1250,1300,1318{,}919594425694\}$, mantendo a
limite da primeira mudança ativa e combinando as duas alternativas de variação interna, metas e suporte:
$4\times2^3=32$ cenários. Os valores hipotéticos não substituem o dado histórico do problema-base.
Sem limite da primeira mudança, o resultado não deve depender de $p^0$.

Na extrapolação, os limites de R$ 800 a R$ 2.000 são um domínio computacional positivo e finito;
não constituem uma região validada estatisticamente. O suporte no artefato permanece intacto.
Cada dia fora desse suporte recebe a marca `extrapolado`, e seus preços, volumes e margens são
interpretados como simulação condicionada à extensão da curva. Se um limite técnico ficar ativo,
isso deve ser informado na interpretação da solução.

## 7. Resolução contínua no Gurobi

A implementação está em `src/optimization/gurobi_solver.py`. A classe `Scenario` identifica as
regras de cada caso e um eventual preço inicial hipotético. A função `solve_scenario` recebe um
`PriceProblem` e devolve o resultado e suas verificações. Não há grade de preços nem variáveis
binárias.

São utilizadas as variáveis auxiliares $u_t=p_t/1300$, $q_t$ e receita líquida $r_t$. Como
$\beta<-1$, define-se $\rho=1+1/\beta\in(0,1)$ e escreve-se a receita de forma equivalente:

$$
q_t=d_t^{ref}u_t^\beta,
\qquad
r_t=(1-\tau)1300d_t^{ref}
\left(\frac{q_t}{d_t^{ref}}\right)^\rho.
$$

O objetivo é $\max\sum_t(r_t-c_tq_t)$. Receita e custo são escalados por mil durante a resolução e
retornam a reais nas saídas. A receita é côncava em volume, mas o conjunto completo de relações e
restrições de preço não é declarado convexo. As expressões não lineares são resolvidas pelo
Gurobi com limitantes globais e tolerância numérica explícita.

### Limites numéricos deduzidos do máximo semanal

Quando o máximo da semana está em vigor, $q_t\le U_w$ para todo dia dessa semana, pois os volumes são positivos e sua soma não pode superar $U_w$. Como a curva é decrescente, isso também implica:

$$
p_t\ge 1300\left(\frac{U_w}{d_t^{ref}}\right)^{1/\beta}.
$$

O código combina esses limites com os limites de preço e volume já conhecidos. São consequências das regras existentes e ajudam a busca sem excluir planos válidos. Se o máximo semanal for retirado, esses limites derivados deixam de ser aplicados. O mínimo semanal não implica um mínimo diário igual para todos os dias.

## 8. Premissas e limites de interpretação

1. Em cada rodada, os dez preços são planejados conjuntamente antes de observar as vendas futuras.
   No uso operacional combinado, executa-se a primeira semana e replaneja-se semanalmente;
   a segunda é cauda, recalculada com a instância atualizada. Os notebooks demonstram uma rodada
   isolada, sem automatizar o ciclo semanal. Veja o [esquema de uso](storytelling/03-storytelling-otimizacao-minerva.md).
2. A curva de demanda está congelada e descreve uma associação observacional; não é uma garantia
   de resposta causal à mudança de preço.
3. O volume previsto pode ser integralmente atendido. Estoque, capacidade, validade e ruptura são
   assumidos não limitantes porque não há dados para representá-los.
4. Na instância, o custo unitário é o do último dia de treino e vale nos dez dias ($c_t=c$). Custos fixos não entram no objetivo.
5. O imposto de 7% é constante e incide sobre a receita.
6. Não há efeito do preço de um dia sobre a demanda futura, nem efeitos cruzados entre produtos.
7. Os preços são contínuos; uma regra comercial de centavos exige incorporá-la ao modelo e
   verificar novamente os resultados.
8. O atendimento da faixa semanal é verificado na previsão central, sem garantia probabilística.
9. Extrapolar o suporte é permitido apenas nos cenários identificados, sem recalibrar o preditivo.

## 9. Saídas e verificação independente

Cada cenário registra regras ativas, condição inicial, hash da curva, status, tempo de execução,
melhor objetivo encontrado, limitante global e gap. Um plano encontrado com tempo esgotado pode atender às regras sem ser a melhor solução. A apresentação distingue plano válido, melhor solução confirmada dentro da tolerância, impossibilidade comprovada e busca encerrada sem encontrar plano. Ausência de solução encontrada também não equivale a
um certificado de inviabilidade.

Preços, demanda e margem são recalculados fora do solver. A verificação confere domínio técnico,
regras ativas, folgas semanais e resíduos de demanda, receita e objetivo. Somente planos que passam
nessa verificação podem ser apresentados. Casos inviáveis não recebem uma agenda recomendada.

## 10. Comparação gráfica com os dias de teste

A plano exibida é definida antes da leitura do teste: **sem limite da primeira mudança, mantendo variação
interna, metas e suporte**. Sua interpretação é condicionada à retirada da ligação com o histórico;
ela não substitui a conclusão do cenário com todas as regras ativas.

Depois do congelamento dos cenários e planos, o teste é carregado para um painel **2 × 5**, um
gráfico por dia. Cada painel contém a curva do contexto correto, o ponto do preço e volume
previstos pelo otimizador e o ponto real do teste. O preço real é receita realizada dividida pelo
volume realizado; o volume real é a quantidade observada. Os eixos indicam R$/kg e kg/dia, e os
painéis identificam data e semana. Os trechos externos ao suporte, quando mostrados, são tracejados.

Os pontos otimizados pertencem à curva por construção. A distância dos pontos reais à curva
informa o erro preditivo nos preços praticados, mas o teste não revela o volume que teria sido
vendido nos preços recomendados. Assim, a comparação não comprova ganho financeiro realizado.

## 11. Entradas persistidas e flexibilizações graduais

As entradas econômicas, operacionais e de calendário são publicadas em
`models/otimizacao/entradas_planejamento.json`, com referências e hashes da curva, do treino e das
restrições. `src/optimization/planning_inputs.py` salva e carrega esse contrato.

O estudo de flexibilizações recebe o artefato e resolve o mesmo objetivo sob limites alterados.
A primeira mudança e a variação interna podem ser ampliadas independentemente; piso e teto podem
ser alterados separadamente. Reduzir a meta nominal desloca os dois limites e não equivale a
ampliar uma folga. Os mínimos são delimitados por inviabilidade provada e plano verificado.
O procedimento está no notebook `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`.


## 12. Propriedades matemáticas e terminologia

Para $D(p)=Ap^\beta$, $A>0$, $p>0$ e $\beta<0$, tem-se $D''(p)=A\beta(\beta-1)p^{\beta-2}>0$. A demanda é convexa em preço. Com $x=\ln p$, $D(e^x)=Ae^{\beta x}$ também é convexa, enquanto $\ln D$ é afim em $x$. As curvas por contexto são paralelas em eixos log-log. A receita reescrita em volume é côncava para $\beta<-1$, mas o problema completo inclui relações não lineares de igualdade e não é declarado convexo.

Neste texto, regra ativa no cenário significa regra imposta. Uma restrição vinculante na solução tem folga nula dentro das tolerâncias numéricas; a positividade de preço não está vinculante no suporte positivo observado. Volume previsto não deve ser denominado volume realizado.

## 13. Sensibilidade das premissas

O notebook `3.0` reavalia demanda (80%/120%), custo unitário (95%/105%), imposto (0%/14%) e elasticidade nos limites HC3 do desenvolvimento. A mudança de elasticidade preserva o volume de referência em R$ 1.300/kg em cada contexto. Cada cenário tem curva e hash próprios em memória, sem sobrescrever o artefato central. Os valores são hipóteses de estresse, sem probabilidades atribuídas ou interpretação de intervalo preditivo conjunto.

A tabela distingue regras originais e primeira ligação removida. Além da reotimização, avalia o plano central fixo sob as novas premissas, registrando margem e atendimento das metas. Essa avaliação pressupõe primeira ligação removida. O teste não define as premissas. Resultados estão em `reports/tables/03_sensibilidade_premissas.csv` e no [storytelling da otimização](storytelling/03-storytelling-otimizacao-minerva.md).

A estimação segue Phillips (2021, cap. 4); retransformação e covariância seguem Duan (1983) e MacKinnon e White (1985). A resolução global segue a documentação Gurobi 13.0. Consulte as [referências completas](referencias-bibliograficas.md).


## 14. Comparação financeira com o realizado

Depois de salvar os planos, a comparação soma volume, receita bruta e margem por semana e no horizonte completo. A margem prevista é a mesma usada no objetivo. O resultado real é reconstruído como receita registrada menos imposto assumido de 7% e custo registrado no teste. Uma segunda referência mantém os preços e volumes reais e substitui o custo registrado pelo custo unitário fixo do planejamento multiplicado pelo volume real.

As diferenças são previsão menos referência real, em reais e percentual. O percentual usa a referência agregada do período, sem média de percentuais semanais, e fica ausente quando a referência não é positiva. Cenários sem plano não recebem valores financeiros previstos. Uma diferença positiva não comprova ganho realizado, pois o teste não observa vendas nos preços sugeridos.

A implementação está em `src/optimization/holdout_comparison.py`. O notebook de cenários publica `data/processed/minerva_referencia_real_teste.json`, com calendário, valores reais, premissas de custo e imposto e identificadores das entradas, teste e planos já salvos. O estudo gradual recebe esse arquivo somente após salvar suas alternativas, conferindo que corresponde às mesmas entradas e resultados do planejamento. Os arquivos de otimização permanecem inalterados durante a comparação com o teste.

Os resultados estão em `reports/tables/03_comparacao_financeira_cenarios.csv`, `reports/tables/03_referencia_real_teste.csv` e `reports/tables/relaxacoes/comparacao_financeira_alternativas_teste.csv`. Os gráficos mostram margem e receita nas duas semanas e no total, com as referências reais identificadas.


## 15. Leitura inicial: uma regra por vez

Antes das combinações e das comparações com o realizado, o painel inicial responde: quanto é necessário flexibilizar cada regra para conseguir um plano? Cada ponto parte das mesmas entradas originais. Somente um limite é alterado: máximo semanal, mínimo semanal, primeira mudança ou mudanças internas. A retirada completa do mínimo mantém o máximo; a retirada completa do máximo mantém o mínimo. O preço histórico, a curva, o custo, o imposto e as metas nominais são preservados.

Os intervalos de início de viabilidade são calculados por bisseção, com um valor comprovadamente inviável e outro com plano conferido. As curvas mostram a redução do mínimo e o aumento do máximo em kg, a primeira mudança em R$/kg e as mudanças internas em R$/kg. Em todos os painéis, avançar para a direita significa flexibilizar mais. A área inviável não recebe margem zero. O limite entre dias não tem teto; a busca vai até R$ 120/kg apenas para localizar o primeiro plano, e a primeira mudança tem a mesma faixa de busca.

A extrapolação é examinada sozinha, mantendo as demais regras. A referência com todas as regras retiradas aparece em gráfico separado, com preço e margem livres calculados pela mesma curva e conferidos com o Gurobi. Essa referência não integra o estudo de uma regra por vez.

Os resultados são publicados antes de ler o teste: `reports/tables/03_sensibilidade_uma_regra.csv`, `reports/tables/03_resumo_uma_regra.csv` e `data/processed/minerva_sensibilidade_isolada.json`. Os gráficos estão em `reports/figures/03_sensibilidade_uma_regra.png` e `reports/figures/03_otimo_livre.png`.


## 16. Organização da leitura e preço anterior hipotético

O fluxo principal do notebook de cenários apresenta o caso original, curvas graduais de uma regra por vez, o ótimo livre separado, a sensibilidade ao preço anterior e a comparação final com o teste. A figura dos dez dias, com curva, ponto otimizado e observação real, é preservada. Os gráficos de trajetórias misturadas e de combinações identificadas apenas por códigos não fazem parte desse fluxo.

Na sensibilidade ao preço anterior, somente esse valor muda; o limite inicial de R$ 2/kg, o limite entre dias de R$ 2/kg, os volumes semanais e a faixa de preços observada permanecem. São testados preços de R$ 1.200 a R$ 1.320/kg em passos de R$ 5/kg e o preço histórico exato. O cinza indica valores amostrados sem solução, com fronteiras aproximadas pela grade. Essa análise não mede intensidade de flexibilização e não substitui o histórico nos demais testes. Seus arquivos são `reports/tables/03_sensibilidade_preco_anterior.csv` e `data/processed/minerva_sensibilidade_preco_anterior.json`.

A comparação financeira visível usa pontos das curvas escolhidos antes de ler o teste, incluindo diferentes limites da primeira mudança e a referência livre separada. Ela é exportada para `reports/tables/03_comparacao_financeira_uma_regra.csv`. O arquivo geral das referências completas permanece disponível. O estudo combinado recebe as referências complementares e a análise de custo, imposto e demanda, preservando os arquivos e as entradas preditivas.
