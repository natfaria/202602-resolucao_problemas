# Relatório de EDA — Estrutura da Demanda e Seleção do Modelo OLS

Este relatório descreve a análise exploratória que conduz à especificação da curva de demanda do produto. A análise completa, com tabelas, gráficos e células executáveis, está no notebook [01-EDA-ols-validacao.ipynb](../notebooks/01-EDA-ols-validacao.ipynb).

O objetivo não é apenas ajustar uma regressão. A análise precisa responder, em sequência, quais variáveis de calendário realmente explicam diferenças de volume, como os dias podem ser agrupados, se a sensibilidade a preço precisa variar entre grupos e como transformar a previsão em escala logarítmica de volta para quilogramas. Cada decisão é tomada a partir dos dados disponíveis e acompanhada de sua limitação.

## Base de dados e estratégia analítica

O histórico contém 86 observações diárias. As 76 primeiras compõem o treino; as 10 últimas são mantidas separadas como referência exploratória. Como esse período final foi consultado ao longo da exploração de alternativas, ele não representa uma estimativa independente definitiva de erro fora da amostra. A análise usa-o apenas como evidência complementar; a validação realmente independente exigiria novos dias ainda não observados.

A variável de resposta é o volume realizado em quilogramas. O preço é calculado como receita dividida pelo volume. Como a relação de interesse é multiplicativa, a curva é estimada no espaço logarítmico:

\[
\ln(Volume) = \alpha_{grupo} + \beta\ln(Preço) + \varepsilon.
\]

Nessa formulação, \(\beta\) é a elasticidade-preço: uma variação percentual no preço está associada a uma variação percentual aproximada de \(\beta\) no volume. Os interceptos \(\alpha\) permitem que grupos de dias tenham patamares diferentes de demanda sem, necessariamente, receber elasticidades diferentes.

## O que as variáveis mostram antes do modelo

O primeiro passo da EDA examina os histogramas de volume, preço, custo por quilograma e receita. O preço apresenta uma faixa observada relativamente concentrada, enquanto volume e receita são assimétricos, com concentração em volumes menores e uma cauda para volumes altos. A média do volume supera a mediana, padrão coerente com essa assimetria.

Essa leitura tem três implicações. Primeiro, ela sustenta o uso de \(\ln(Volume)\) e \(\ln(Preço)\), que transforma uma relação multiplicativa em uma relação linear estimável. Segundo, ela delimita o domínio das previsões: uma curva de demanda só deve ser interpretada entre preços já observados no respectivo grupo. Terceiro, receita é mantida como variável descritiva, pois já incorpora preço e volume; incluí-la como explicativa da própria demanda criaria uma relação circular.

Os gráficos de dispersão preço–volume reforçam que a relação negativa é visível, mas não idêntica em todos os dias. Para tornar essa leitura visual mais clara, os mesmos pontos também são apresentados unidos em ordem crescente de preço dentro de cada grupo. Essa linha é apenas descritiva: não é uma curva estimada, não representa a sequência cronológica dos dias e não deve ser extrapolada.

## Antes dos clusters: qual sazonalidade permanece depois de controlar por preço?

A análise não parte do pressuposto de que o dia da semana é a única fonte de sazonalidade. Mês, quinzena, semana do mês e dia da semana são examinados com quatro gráficos para cada hipótese: distribuição e média de volume, além de distribuição e média de preço. A separação entre volume e preço é importante: uma diferença visual de volume poderia ser apenas consequência de preços praticados em faixas distintas.

Em seguida, cada hipótese é testada por OLS sobre \(\ln(Volume)\), controlando por \(\ln(Preço)\). O efeito adicional de mês não é identificado (p = 0,698), o efeito de quinzena também não (p = 0,579) e semana do mês tampouco (p = 0,852). Em todos esses casos, acrescentar os grupos de calendário piora o BIC. Não há evidência suficiente para manter essas variáveis no modelo.

O dia da semana é diferente. O teste conjunto apresenta p < 0,001 e a inclusão dos dias reduz o BIC de aproximadamente 246,50 para 140,76 no modelo que trata todos os dias individualmente. Portanto, a sazonalidade relevante no histórico é semanal: o dia da semana entra no modelo; mês, quinzena e semana do mês não entram.

## Como o agrupamento de dias é obtido

Com o dia da semana selecionado, a análise começa pelo modelo mais flexível, com um intercepto por dia e preço controlado. Quarta-feira é usada como referência para verificar se Terça e Quinta carregam diferenças identificáveis de nível.

As diferenças estimadas de Terça e Quinta em relação a Quarta não são estatisticamente distinguíveis de zero (p = 0,853 e p = 0,800, respectivamente). O teste F conjunto para as duas igualdades também não rejeita a hipótese de níveis iguais (p = 0,966). Esses resultados não provam igualdade absoluta; mostram que os dados não sustentam a complexidade extra de separar esses três dias.

Essa leitura é complementada por um torneio de partições. Separar Terça ou Quinta individualmente eleva o BIC sem ganho relevante de MAPE exploratório. O modelo dia a dia obtém MAPE ligeiramente menor em um único período curto, mas usa três parâmetros adicionais e tem BIC substancialmente pior. Essa pequena melhora isolada é interpretada como flexibilidade adicional, não como evidência suficiente de generalização.

O agrupamento de nível adotado é, portanto:

| Grupo | Dias |
|---|---|
| Segunda | Segunda-feira |
| TerQuaQui | Terça-feira, Quarta-feira e Quinta-feira |
| Sexta | Sexta-feira |
| FDS | Sábado e Domingo |

A fronteira entre FDS e Sexta recebe um teste específico. Forçar FDS e Sexta a compartilhar intercepto piora muito o BIC (130,78 para 172,18). O teste F aninhado para o intercepto adicional de FDS é 58,59, com p = 7,3e-11. Assim, FDS possui nível próprio de demanda, mesmo com apenas 10 observações.

As métricas do holdout exploratório produzem uma tensão que precisa ser registrada. Juntar FDS a Sexta reduz marginalmente RMSE e WMAPE nesse período, mas não há FDS entre os 10 dias e há apenas uma Sexta. A melhora pode decorrer do deslocamento do coeficiente de Sexta usado nessa única previsão, não de uma estrutura superior. BIC e teste F respondem diretamente à questão estrutural com toda a amostra de treino; por isso, FDS permanece como intercepto próprio. A previsão de FDS continua sem validação externa e deve ser usada com cautela se sábado e domingo fizerem parte do horizonte de decisão.

Na sensibilidade da inclinação, retirar FDS desloca a elasticidade para valores mais negativos em média: a diferença estimada é −2,294, com intervalo bootstrap de 95% entre −5,204 e 0,388. O intervalo ainda contém zero, mas está predominantemente no sentido negativo. Portanto, não há evidência suficiente para atribuir uma elasticidade exclusiva ao FDS; há, porém, uma sensibilidade relevante da elasticidade compartilhada à presença desse grupo.

## Elasticidade compartilhada ou elasticidades por cluster?

Com os quatro interceptos definidos, são comparadas duas hipóteses:

1. uma elasticidade única compartilhada por todos os clusters;
2. uma elasticidade própria para cada cluster, obtida por interações entre \(\ln(Preço)\) e os grupos.

Os gráficos log-log do notebook mostram as duas alternativas lado a lado. Nesse tipo de escala, uma curva de potência aparece como reta e sua inclinação é a elasticidade. Todos os segmentos são desenhados apenas na faixa de preço observada em seu próprio cluster; não há extrapolação visual.

O modelo com elasticidade única estima \(\beta = -12,46\). O modelo com interações melhora o ajuste dentro da amostra, como seria esperado por usar mais parâmetros, mas aumenta o BIC de 130,78 para 133,04. No período exploratório, também piora RMSE, WMAPE e MAPE. A elasticidade estimada especificamente para FDS chega a ser positiva, resultado incompatível com a interpretação econômica usual e baseado em somente dez observações. Esse é um sinal de falta de identificação, não evidência de que o FDS responda positivamente ao preço.

Assim, a elasticidade compartilhada é escolhida por parcimônia e estabilidade. Os interceptos diferenciam o nível de venda entre grupos; a inclinação comum evita atribuir reações de preço específicas a subconjuntos pequenos que não sustentam essa complexidade.

## Métricas de previsão e escala de decisão

As métricas são avaliadas em quilogramas, pois a decisão posterior envolve metas de volume. RMSE penaliza mais erros grandes em kg. WMAPE por volume, calculado como \(\sum|y-\hat y| / \sum y\), mede o erro sobre o volume total e dá maior peso aos dias de maior venda. MAPE por incidência atribui o mesmo peso a cada dia e, por isso, é mais sensível a volumes muito baixos. O viés agregado mede a direção do erro total: valores negativos indicam subestimação do volume somado.

No modelo OLS com elasticidade única e quatro interceptos, o período exploratório apresenta RMSE de 8,89 kg, WMAPE de 38,33% e MAPE de 56,07%. Essas métricas ajudam a descrever o desempenho observado, mas não são tratadas como medida final independente porque o mesmo período foi reutilizado durante a exploração.

## Previsão em quilogramas: correção de retransfomação

O ajuste ocorre em \(\ln(Volume)\), mas a previsão operacional é necessária em kg. Aplicar somente a exponencial à previsão em log tende a subestimar a média condicional quando os resíduos têm variância. Para corrigir essa retransfomação, o modelo principal usa o fator global de smearing de Duan:

\[
\widehat{Volume} = \exp(X\hat{\beta})\times\hat{S},
\qquad
\hat{S}=\frac{1}{n}\sum_{i=1}^{n}\exp(\hat\varepsilon_i).
\]

No ajuste completo, o fator global é aproximadamente \(\hat{S}=1,12\). Esse fator multiplica a previsão em kg sem alterar a elasticidade estimada. Em qualquer previsão futura ou validação, ele deve ser estimado apenas com os resíduos do treino disponível naquele momento.

## Pontos que divergem da curva

Valores extremos de volume ou preço, vistos isoladamente, não são automaticamente tratados como pontos anômalos. O diagnóstico correto avalia o resíduo depois de controlar simultaneamente por preço e cluster. Um ponto é destacado quando o volume observado fica muito acima ou abaixo do que a curva prevê para aquele preço e grupo.

O diagnóstico visual identifica 30/08, sábado, acima da curva; e 11/10, sábado, 19/10, domingo, e 23/10, quinta-feira, abaixo da curva. Esses dias não são removidos. Eles permanecem no ajuste e são tratados como informação histórica; o diagnóstico apenas torna explícito que podem influenciar a elasticidade OLS.

## Checagem de robustez por Huber

OLS atribui peso quadrático aos resíduos: um erro duas vezes maior pesa quatro vezes mais. A regressão de Huber mantém todas as observações, mas reduz gradualmente o peso de resíduos muito grandes. Para resíduos usuais, ela se comporta como OLS; a diferença aparece principalmente nos dias que divergem mais da curva.

Como checagem de robustez, Huber estima elasticidade de aproximadamente \(-14,10\), contra \(-12,46\) do OLS: deslocamento de cerca de 13%. Esse resultado é material e confirma que a escolha do estimador é uma fonte de incerteza metodológica. Ele não motiva remover dados, nem substitui automaticamente o modelo principal.

O bootstrap da diferença OLS–Huber inclui zero. Além disso, a validação temporal interna que favorece Huber foi definida depois de explorações anteriores e avalia 09/10 a 31/10, período que contém integralmente o episódio mais volátil observado. Ela funciona como teste de estresse tardio e tende a favorecer métodos que reduzem o peso de resíduos grandes; não possui confirmação em um novo holdout externo. Por essas razões, a evidência sustenta Huber como checagem obrigatória de robustez, mas não como base suficiente para substituir OLS como especificação principal.

## Modelo final e limites de uso

O modelo principal final é OLS em \(\ln(Volume)\), com quatro interceptos de nível, elasticidade compartilhada de aproximadamente \(-12,46\) e correção global de smearing de aproximadamente 1,12.

Usando TerQuaQui como referência, a forma estimada é:

\[
\ln(Volume) = 92{,}175 - 12{,}458\ln(Preço)
+ 0{,}338\,I_{Segunda}
- 1{,}255\,I_{Sexta}
- 2{,}883\,I_{FDS}.
\]

A previsão média em quilogramas é a exponencial dessa expressão multiplicada pelo fator de smearing. A equação deve ser usada apenas dentro da faixa de preços observada em cada grupo. Fora desse suporte, a previsão é extrapolação e não possui validação empírica neste histórico.

Três limites acompanham a decisão:

- A elasticidade possui incerteza material: OLS e Huber produzem valores diferentes, ainda que a amostra não prove uma superioridade definitiva entre os dois métodos.
- FDS possui nível próprio bem identificado no treino, mas não possui observações no período exploratório separado; sua previsão fora da amostra permanece incerta.
- A referência de erro fora da amostra já foi consultada durante a exploração. Uma avaliação final independente requer novos dados futuros.

O apêndice técnico do notebook documenta o teste de estresse temporal expansivo, LOO, bootstrap estratificado e sensibilidade do fator de smearing por cluster. Essas análises sustentam a cautela dos limites acima, sem alterar a decisão principal do relatório.
