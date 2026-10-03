# Plano de ação: EDA, curva de demanda e otimização de preços

## 1. Objetivo do plano

Este documento organiza a solução do desafio Minerva em três notebooks com responsabilidades
separadas e contratos explícitos entre as etapas:

1. entender e preparar os dados sem escolher o modelo pelo resultado do teste;
2. estimar e validar uma curva de resposta preço-volume;
3. usar a curva congelada em um modelo matemático de otimização de preços.

O fluxo deve responder à pergunta central do desafio: qual sequência de preços diários maximiza a
margem acumulada em duas semanas, respeitando a meta semanal de volume e o limite de variação de
preço entre dias consecutivos?

O modelo estatístico não é o resultado final da solução. Sua função é entregar ao otimizador uma
estimativa auditável de volume para cada combinação admissível de preço e contexto do dia, além de
uma medida de incerteza.

## 2. Princípios metodológicos

### 2.1 Separação entre exploração, estimação e decisão

- A EDA formula hipóteses e verifica a qualidade e o suporte dos dados.
- A modelagem decide a especificação por validação temporal, não apenas por gráficos, p-valores ou
  ajuste dentro da amostra.
- A otimização não reabre a seleção estatística. Ela recebe uma curva já congelada e resolve a
  decisão operacional.

### 2.2 Somente informações disponíveis no momento da decisão

Uma variável explicativa só pode entrar no modelo de demanda se estiver disponível antes da
definição do preço. Receita realizada, margem realizada e qualquer informação futura não podem ser
usadas como preditores. O preço médio realizado, calculado como receita dividida por volume, deve
ser documentado como aproximação do preço efetivamente oferecido.

### 2.3 Validação temporal e controle de vazamento

- O período de 01/08/2025 a 31/10/2025 é o conjunto de desenvolvimento.
- O período de 03/11/2025 a 14/11/2025 é o holdout oficial fornecido pelo desafio.
- Toda criação e seleção de variáveis deve ocorrer dentro do conjunto de desenvolvimento.
- A seleção de modelos deve usar janelas temporais expansivas dentro desse período.
- O holdout só deve ser executado depois que fórmula, variáveis, métricas e critérios de escolha
  estiverem congelados.
- Com a amostra disponível, o holdout é uma avaliação final interna ao material fornecido, não uma
  validação externa independente. Uma validação externa genuína exigirá dados futuros ainda não
  observados.

### 2.4 Parcimônia compatível com a amostra

O treino possui 76 observações, incluindo apenas cinco sábados e cinco domingos. A quantidade de
parâmetros deve permanecer pequena. O modelo principal deve compartilhar a elasticidade entre os
grupos de calendário; inclinações específicas por dia ou cluster só podem ser consideradas como
sensibilidade e não como ponto de partida.

### 2.5 Escala da decisão

As métricas principais devem ser calculadas em quilogramas porque a restrição operacional é uma
meta semanal de volume. WMAPE, RMSE e viés agregado são mais úteis para essa decisão do que o MAPE
isolado, que fica instável quando o volume realizado é muito baixo.

### 2.6 Sem extrapolação silenciosa

Cada previsão e cada preço recomendado devem respeitar a faixa de preços observada no contexto
correspondente. O otimizador não deve explorar regiões nas quais a curva não possui suporte
empírico.

### 2.7 Independência narrativa e protocolo de explicação

- Cada notebook deve ser construído a partir da fonte bruta, do documento do Desafio
  Minerva-Unifesp-ITA e das referências bibliográficas listadas neste plano.
- Resultados, conclusões, escolhas de variáveis, testes e figuras de notebooks ou tentativas
  anteriores não podem ser usados como evidência nem mencionados na narrativa. Os notebooks antigos
  servem apenas como arquivo histórico e não são fonte metodológica.
- Antes de cada teste, tabela ou gráfico, uma célula Markdown deve declarar a pergunta respondida,
  justificar por que a análise é adequada e registrar suas principais limitações ou hipóteses.
- Depois de cada resultado, outra célula Markdown deve interpretar os valores efetivamente
  produzidos, separar associação de causalidade e explicar a consequência para a próxima etapa.
- Justificativas e interpretações devem permanecer em Markdown, não escondidas em comentários ou
  mensagens de código. Após cada execução integral, o texto deve ser conferido contra os resultados
  atualizados.
- Somente referências bibliográficas e o documento da Minerva podem fundamentar escolhas
  metodológicas. O Notebook 2 pode usar o EDA do Notebook 1 para formar o catálogo empírico de
  variáveis candidatas, mas deve reestimar e justificar cada decisão com sua própria amostra de
  desenvolvimento; resultados de outras tentativas não podem ser importados como evidência.

## 3. Organização proposta no Cookiecutter Data Science

### 3.1 Notebooks

| Ordem | Arquivo proposto | Responsabilidade |
|---|---|---|
| 1 | `notebooks/1.0-minerva-eda-preparacao.ipynb` | Auditoria, preparação, suporte dos dados e hipóteses candidatas |
| 2 | `notebooks/2.0-minerva-curva-demanda-validacao.ipynb` | Seleção, estimação, diagnóstico e congelamento da curva |
| 3 | `notebooks/3.0-minerva-otimizacao-precos.ipynb` | Formulação matemática, solução, cenários e análise das restrições |

Os notebooks antigos permanecem em `notebooks/antigos/` apenas como arquivo histórico. Eles não
devem ser importados, funcionar como dependência ou fornecer resultados e conclusões aos novos
notebooks.

### 3.2 Dados e artefatos

```text
data/raw/
    instance_desafio_minerva.xlsx              # fonte original imutável

data/interim/
    minerva_historico_limpo.csv                 # dados limpos, ainda próximos da fonte
    minerva_treino.csv                          # desenvolvimento até 31/10
    minerva_holdout.csv                         # avaliação oficial, isolada

data/processed/
    minerva_modelagem_treino.csv                # variáveis canônicas para a modelagem
    minerva_previsoes_holdout.csv                # previsões finais sem ajuste posterior
    minerva_plano_precos.csv                    # recomendação diária do otimizador

models/
    demand_curve_champion.json                  # parâmetros e metadados da curva selecionada
    demand_curve_uncertainty.json               # cenários ou quantis de erro
    model_selection_summary.json                # candidatos, métricas e regra de escolha

reports/figures/
    01_*.png                                    # figuras da EDA
    02_*.png                                    # figuras de modelagem e diagnóstico
    03_*.png                                    # resultados e sensibilidades da otimização
```

### 3.3 Evolução do código exploratório para `src/`

O Notebook 1 é uma análise exploratória autocontida: leitura, auditoria e criação inicial de
variáveis permanecem visíveis nas células, facilitando a revisão das hipóteses. A promoção para
`src/` acontece apenas quando uma transformação ou regra estiver estabilizada e precisar ser
reutilizada pela modelagem, previsão ou otimização.

Em qualquer etapa, scripts existentes produzidos e aprovados na fase anterior podem ser consumidos.
Um script novo, porém, nunca deve antecipar a decisão que o próprio notebook está avaliando: ele só
pode ser criado ao final da fase, depois que especificação, regras e diagnósticos estiverem
congelados. Assim, `src/` é produto final reproduzível do notebook, e não fonte de uma conclusão
pré-definida.

| Módulo | Evolução planejada |
|---|---|
| `src/dataset.py` | Futuramente, leitura e validação estabilizadas para execução reproduzível |
| `src/features.py` | Futuramente, variáveis aprovadas para modelagem e inferência |
| `src/modeling/train.py` | Janelas expansivas, ajuste dos candidatos e tabela de comparação |
| `src/modeling/demand_curve.py` | Especificações candidatas, ajuste final, smearing, suporte e artefato JSON |
| `src/modeling/predict.py` | Previsões centrais, cenários e validação de suporte |
| `src/optimization/price_schedule.py` | Formulação, solução e validação do problema de preços |

O módulo `src/optimization/` será criado quando o terceiro notebook for implementado.

## 4. Notebook 1: EDA e preparação

### 4.1 Pergunta narrativa

> A base possui qualidade, variação de preço e cobertura de calendário suficientes para estimar uma
> curva de demanda útil à decisão de preço?

O notebook deve contar a história da observação bruta até um conjunto pequeno e previamente
justificado de modelos candidatos. Ele não escolhe a curva final.

### 4.2 Abertura e contrato analítico

1. Apresentar a pergunta de decisão e o papel da etapa preditiva.
2. Registrar o horizonte de duas semanas e as restrições descritas no desafio.
3. Declarar as unidades: volume em kg, receita e custo em R$, preço e custo em R$/kg.
4. Fixar os períodos de desenvolvimento e holdout.
5. Definir que o notebook não inspecionará distribuições, relações ou métricas do holdout.
6. Definir uma semente aleatória única para procedimentos reprodutíveis.

### 4.3 Leitura e auditoria da fonte

1. Ler as abas `base_dados` e `meta_vol_variacao_preco` diretamente de
   `data/raw/instance_desafio_minerva.xlsx`.
2. Validar nomes, tipos e presença das colunas obrigatórias.
3. Confirmar que `Produto` identifica um único SKU ou separar o fluxo por SKU se surgirem novos
   produtos.
4. Verificar datas duplicadas, ordem cronológica, lacunas, valores ausentes e valores não positivos.
5. Verificar se receita, custo e volume possuem unidades consistentes.
6. Comparar o esquema real com `docs/referencias/Minerva_Unifesp_ITA.pdf`: o documento da Minerva
   menciona imposto realizado, mas a planilha atual não possui essa coluna. Registrar a diferença
   sem criar valores artificiais.
7. Ler meta, tolerância e variação máxima da própria planilha, sem fixar percentuais no código.
8. Registrar a divergência entre a tolerância textual descrita no PDF e o valor da instância da
   planilha; a instância deve alimentar o cálculo, e a divergência deve aparecer no relatório.

### 4.4 Variáveis derivadas canônicas

Criar diretamente no Notebook 1 e documentar em Markdown. A promoção para `src/features.py` só
ocorre depois que uma transformação for aprovada para reutilização:

| Variável | Fórmula ou origem | Uso |
|---|---|---|
| `preco_kg` | receita realizada / volume realizado | Variável de decisão histórica e explicativa central |
| `custo_kg` | custo realizado / volume realizado | Margem e premissa futura; não entra automaticamente na demanda |
| `margem_unitaria_ex_post` | `preco_kg - custo_kg` | Descrição histórica, nunca preditor de demanda |
| `ln_volume` | log do volume positivo | Resposta da curva de potência |
| `ln_preco` | log do preço positivo | Elasticidade na curva de potência |
| `dia_semana` | derivado da data | Contexto conhecido antes da decisão |
| `fim_semana` | sábado ou domingo | Alternativa parcimoniosa de calendário |
| `inicio_mes` | dias 1 a 7, conforme hipótese do documento da Minerva | Candidato de nível solicitado pelo desafio |
| `mes`, `quinzena`, `semana_mes` | derivados da data | Hipóteses exploratórias, não entradas obrigatórias |
| `indice_tempo` | sequência cronológica | Candidato simples para mudança de nível ao longo do período |
| `inicio_semana` | data de referência semanal | Agregação e métricas semanais |

Não criar lags de volume como variável padrão. No horizonte do desafio, os preços das duas semanas
podem ser definidos conjuntamente e os volumes futuros intermediários ainda não são conhecidos.

### 4.5 Diagnóstico da amostra e do suporte

1. Contar observações por mês, semana e dia da semana.
2. Exibir mínimo, máximo, média e dispersão de preço e volume.
3. Mostrar a faixa de preço por contexto de calendário.
4. Verificar se há variação de preço suficiente para estimar resposta; ausência de dispersão impede
   identificar elasticidade.
5. Destacar a baixa cobertura de FDS e qualquer região de preço representada por poucos pontos.
6. Investigar se volumes observados podem estar censurados por ruptura de estoque. Como não existe
   informação de estoque, registrar que vendas podem não representar toda a demanda potencial.
7. Verificar se o preço médio diário pode combinar transações em preços diferentes. Se não houver
   preço de lista, registrar essa limitação de mensuração.

### 4.6 História exploratória

Os gráficos devem responder perguntas em uma sequência lógica:

1. **Como volume, preço e custo evoluem no tempo?**
   - séries temporais alinhadas;
   - identificação visual de regimes, picos e mudanças de faixa.
2. **Qual é a distribuição das variáveis?**
   - histogramas e estatísticas robustas;
   - justificativa para transformações logarítmicas.
3. **O calendário altera apenas o volume ou também o preço praticado?**
   - distribuições de volume e preço por dia da semana;
   - análise de mês, quinzena e semana do mês apenas como hipótese.
4. **Existe relação preço-volume dentro do suporte observado?**
   - dispersão em escala original e log-log;
   - pontos coloridos por calendário;
   - nenhuma linha descritiva apresentada como curva causal.
5. **Quais observações merecem investigação?**
   - sinalização, não remoção, de valores extremos;
   - contextualização de que um extremo marginal não é necessariamente um resíduo extremo.

### 4.7 Catálogo prévio de modelos candidatos

Ao final da EDA, congelar um conjunto pequeno de candidatos para o Notebook 2:

| Código | Especificação | Finalidade |
|---|---|---|
| `MIN_PRECO_LINEAR` | `volume ~ preco` | Modelo mínimo linear |
| `MIN_PRECO_EXPONENCIAL` | `ln(volume) ~ preco` | Modelo mínimo exponencial |
| `MIN_PRECO_LOGLOG` | `ln(volume) ~ ln(preco)` | Modelo mínimo de elasticidade constante |
| `CAL1_UTIL_FDS` | modelo mínimo + `fim_semana` | Calendário com dois níveis |
| `CAL2_SETE_DIAS` | modelo mínimo + `C(dia_semana)` | Níveis diários completos |
| `CAL3_SEGQUI_SEX_FDS` | modelo mínimo + grupos segunda–quinta, sexta e FDS | Partição parcimoniosa principal |
| `CAL4_SEG_TERQUI_SEX_FDS` | modelo mínimo + segunda, terça–quinta, sexta e FDS | Sensibilidade à segunda-feira |

`grupo_calendario` só poderá ser usado se sua regra for definida com o conjunto de desenvolvimento
e antes da avaliação final. Nenhum candidato terá elasticidade específica por grupo na seleção
principal.

### 4.8 Critérios pré-registrados para o Notebook 2

1. WMAPE em kg como métrica primária.
2. RMSE em kg e viés agregado como métricas secundárias.
3. Erro do volume semanal como métrica operacional complementar.
4. Preferência pelo modelo mais simples quando o ganho do challenger for pequeno ou inconsistente.
5. Elasticidade de preço com sinal economicamente coerente.
6. Previsões positivas dentro do suporte observado.
7. BIC e testes estatísticos como evidência auxiliar, não como única regra de seleção.

### 4.9 Entregáveis do Notebook 1

- Base limpa de desenvolvimento e arquivo isolado de holdout.
- Base processada com variáveis canônicas.
- Dicionário de variáveis, unidades e momento de disponibilidade.
- Figuras numeradas da EDA em `reports/figures/`.
- Tabela dos modelos candidatos e critérios de escolha.
- Lista explícita de limitações e dados adicionais desejáveis: estoque, promoções, preço de
  concorrentes, clima, feriados específicos e preço de lista.

### 4.10 Critério de conclusão

O Notebook 1 está concluído quando outra pessoa consegue reproduzir os arquivos de modelagem a
partir da planilha original, entender por que cada variável foi criada e verificar que nenhuma
decisão utilizou o comportamento do holdout.

## 5. Notebook 2: curva de demanda e validação

### 5.1 Pergunta narrativa

> Qual é a especificação mais simples que prevê volume em kg de forma estável para preços e dias do
> calendário observados?

O notebook começa com candidatos congelados, executa a seleção temporal, diagnostica o vencedor e
produz um artefato que o otimizador pode consumir sem depender do notebook.

### 5.2 Validação temporal interna

1. Carregar somente `minerva_modelagem_treino.csv` durante a seleção.
2. Ordenar cronologicamente e proibir embaralhamento aleatório.
3. Usar três folds semanais expansivos e não sobrepostos: 39 observações de treino e 13 de validação,
   depois 52/13 e, por fim, 65/11. O primeiro fold funciona também como teste de estresse devido à
   amostra ligeiramente inferior à referência de 40 observações para preço apenas.
4. Em cada fold, ajustar o modelo apenas com semanas passadas e validar nas duas semanas seguintes;
   nunca embaralhar observações nem treinar com datas posteriores à validação.
5. Recalcular dentro de cada janela toda estatística dependente do treino, inclusive smearing,
   médias, limites e transformações ajustadas.
6. Registrar previsão, erro, data, dia da semana, preço e versão do candidato para cada origem.
7. Calcular, para todos os candidatos e exatamente sobre as mesmas previsões, `WMAPE`, `MAE`,
   `RMSE`, erro absoluto mediano, `sMAPE`, `RMSLE`, viés em kg e viés percentual.
8. Calcular também WMAPE semanal, erro absoluto do volume semanal e erro percentual do volume
   acumulado. O MAPE convencional pode ser exibido apenas como diagnóstico, com alerta explícito de
   instabilidade quando o volume observado estiver próximo de zero.
9. Manter WMAPE como métrica primária por refletir o erro total em kg sem dividir cada observação por
   volumes muito baixos. RMSE mede a penalização dos grandes erros; MAE e erro mediano mostram o erro
   típico; viés identifica subestimação ou superestimação sistemática. Nenhuma métrica poderá ser
   escolhida depois de conhecidos os resultados.
10. Estimar a incerteza das métricas por reamostragem em blocos semanais quando a quantidade de
    semanas permitir. Não escolher pelo melhor dia, semana ou métrica isolada.

### 5.3 Construção incremental e seleção champion-challenger

Toda justificativa deve ser refeita no próprio Notebook 2 usando apenas o conjunto de
desenvolvimento. O EDA do Notebook 1 fornece hipóteses candidatas — calendário, mês, quinzena,
semana do mês e tendência —, enquanto o documento da Minerva fornece a hipótese de início do mês.
Resultados, p-valores, parâmetros ou conclusões de outras tentativas não podem ser importados nem
tratados como evidência.

#### 5.3.1 Justificativa inferencial dos agrupamentos

Antes de comparar as partições simplificadas, ajustar um modelo saturado de dia da semana,
controlando por preço, para verificar quais diferenças de nível são sustentadas pela amostra atual.

1. Estimar coeficientes, intervalos de confiança e p-valores com covariância robusta HC3.
2. Definir antes dos resultados os contrastes de interesse: sábado versus domingo; terça versus
   quarta versus quinta; segunda versus terça–quinta; sexta versus os demais dias úteis.
3. Aplicar testes de Wald robustos aos contrastes individuais e conjuntos, reportando p-valores
   brutos e corrigidos pelo método de Holm para multiplicidade.
4. Reportar também tamanho do efeito na escala de volume, intervalo de confiança e número de
   observações por dia. P-valor sem tamanho de efeito não justifica uma decisão operacional.
5. Não interpretar p-valor alto como prova de igualdade. Um agrupamento somente poderá ser descrito
   como equivalência se uma margem prática tiver sido definida antes do teste e o intervalo estiver
   contido nessa margem. Sem margem operacional disponível, o agrupamento deve ser justificado por
   parcimônia e validação temporal, não por uma alegação de igualdade estatística.
6. Usar esses resultados apenas para formular candidatos. A promoção do agrupamento continua
   dependendo de desempenho fora da amostra interna e estabilidade.

#### 5.3.2 Sequência incremental de variáveis

Executar duas sequências transparentes, preservando as mesmas observações e uma elasticidade
compartilhada dentro de cada comparação de calendário ou variável adicional.

**Sequência A — modelo mínimo e estrutura de calendário levantada no EDA:**

1. **`MIN_PRECO_*` — preço apenas:** comparar linear, exponencial e log-log como em Phillips 4.2.1.
2. **`CAL1_UTIL_FDS` — fim de semana:** adicionar o indicador de fim de semana.
3. **`CAL3_SEGQUI_SEX_FDS` — sexta-feira:** manter segunda a quinta agrupadas e separar sexta e FDS.
4. **`CAL4_SEG_TERQUI_SEX_FDS` — segunda-feira:** separar segunda de terça a quinta.
5. **`CAL2_SETE_DIAS` — calendário saturado:** liberar os níveis individuais de dia da semana.

**Sequência B — variáveis adicionais do EDA e do documento da Minerva:**

1. **`BASE_CALENDARIO` — calendário:** manter apenas a estrutura vencedora da Sequência A.
2. **`ADD_INICIO_MES` — início do mês:** adicionar `inicio_mes`, hipótese do documento da Minerva.
3. **`ADD_TENDENCIA` — tendência:** adicionar `indice_tempo`, hipótese da série temporal do EDA.
4. **`ADD_MES` — mês:** adicionar indicadores de mês levantados no EDA.
5. **`ADD_QUINZENA` — quinzena:** adicionar o indicador de segunda quinzena levantado no EDA.
6. **`ADD_SEMANA_MES` — semana do mês:** adicionar os níveis de `semana_mes` levantados no EDA.
7. **`ADD_INICIO_MES_TENDENCIA`:** avaliar conjuntamente início do mês e tendência.

Na Sequência B, definir antes da comparação uma zona de desempenho equivalente: WMAPE até 2 pontos
percentuais acima do melhor resultado e RMSE até 5% acima do menor RMSE. Entre candidatos nessa
zona, preferir menos parâmetros e usar AICc e BIC apenas como apoio de parcimônia na mesma escala.

Produzir uma tabela incremental única com, no mínimo:

- código, fórmula e bloco de variáveis acrescentado;
- número de parâmetros e observações;
- coeficiente de preço, sinal, intervalo HC3 e p-valor;
- p-valor Wald HC3 do bloco acrescentado, bruto e ajustado quando aplicável;
- R² ajustado e BIC como diagnósticos dentro de modelos com a mesma variável resposta;
- WMAPE, MAE, RMSE, erro absoluto mediano, sMAPE, RMSLE, viés em kg e viés percentual;
- WMAPE semanal, erro absoluto semanal e erro percentual do volume acumulado;
- variação de cada métrica em relação ao modelo imediatamente anterior;
- previsão mínima, estabilidade do sinal de preço e validade operacional.

BIC não deve ser comparado diretamente entre modelos com variáveis resposta em escalas diferentes.
R², R² ajustado e p-valores são diagnósticos do ajuste; a decisão preditiva deve priorizar a
validação temporal.

#### 5.3.3 Rodadas de decisão

Executar as rodadas abaixo para evitar uma combinação excessiva de alternativas:

1. **Rodada de forma funcional mínima:** comparar `MIN_PRECO_LINEAR`, `MIN_PRECO_EXPONENCIAL` e
   `MIN_PRECO_LOGLOG`, todos usando apenas preço.
2. **Rodada de calendário:** aplicar `CAL1_UTIL_FDS`, `CAL2_SETE_DIAS`, `CAL3_SEGQUI_SEX_FDS` e
   `CAL4_SEG_TERQUI_SEX_FDS` às formas funcionais, mantendo as mesmas observações e métricas.
3. **Rodada de variáveis adicionais:** comparar `BASE_CALENDARIO` e todos os candidatos `ADD_*`,
   deixando explícita a origem de cada hipótese no EDA ou no documento da Minerva e aplicando a zona
   de desempenho equivalente definida antes dos resultados.
4. **Rodada de elasticidade:** somente depois de definir efeitos principais, calendário, forma
   funcional e eventual tendência, comparar elasticidade compartilhada com interações
   `ln(preço) × contexto`. A inclinação única usada nas rodadas anteriores é uma restrição de trabalho
   para selecionar variáveis de nível, não uma conclusão antecipada.

Regras de decisão:

- o challenger deve melhorar WMAPE e apresentar comportamento coerente nas métricas secundárias,
  não apenas vencer em um ponto ou em uma métrica escolhida posteriormente;
- se a diferença for pequena, manter o modelo com menos parâmetros;
- p-valores e testes de bloco podem apoiar a interpretação, mas não substituem validação temporal,
  tamanho de efeito, estabilidade e plausibilidade econômica;
- rejeitar modelos com comportamento operacional inválido, como volumes negativos;
- testar interações `preço × calendário` apenas na rodada dedicada, respeitando o princípio
  hierárquico de manter os respectivos efeitos principais; não estimar sete elasticidades diárias
  com a amostra atual;
- registrar todos os modelos tentados para evitar seleção informal posterior.

Antes dessas rodadas, ajustar e reportar a regressão preço-volume na leitura mais direta do
documento da Minerva, em escala original, e um baseline sem calendário em escala log-log. Esses
modelos documentam a proposta mínima do desafio e devem ser comparados, pelas mesmas métricas
temporais, com as especificações enriquecidas pelo calendário.

#### 5.3.4 Elasticidade compartilhada versus elasticidades por contexto

A ordem metodológica é: selecionar primeiro as variáveis de nível e a forma funcional; somente
depois verificar se o efeito de preço precisa variar por contexto. Isso respeita o princípio de
hierarquia: uma interação não deve ser selecionada antes dos efeitos principais que a compõem.

Usando a partição de calendário vencedora como análise principal, comparar:

1. **`ELAST_COMPARTILHADA` — inclinação compartilhada:**
   `ln(volume) ~ ln(preço) + contexto`.
2. **`ELAST_POR_CONTEXTO` — inclinações por contexto:**
   `ln(volume) ~ ln(preço) * contexto`.

No caso de `CAL3_SEGQUI_SEX_FDS`, `ELAST_POR_CONTEXTO` adiciona somente `ln(preço) × sexta` e
`ln(preço) × fim_de_semana`. As elasticidades resultantes são a inclinação-base e as somas da
inclinação-base com cada interação. Repetir a comparação condicionada a `CAL4_SEG_TERQUI_SEX_FDS` apenas como análise de
sensibilidade, para verificar se a conclusão depende da separação da segunda-feira. Não escolher
livremente entre todas as combinações depois de observar os resultados.

Premissas e verificações obrigatórias:

1. **Suporte comparável:** estimar e representar as curvas apenas na interseção das faixas de preço
   dos contextos. Centralizar `ln(preço)` em um preço de referência comum pertencente a essa
   interseção, reduzindo colinearidade sem alterar as inclinações.
2. **Inferência robusta:** testar conjuntamente
   `H0: interação_sexta = interação_fim_de_semana = 0` por Wald HC3. Reportar também contrastes
   individuais, intervalos HC3 e p-valores corrigidos por Holm.
3. **Magnitude operacional:** traduzir cada elasticidade para a variação prevista de volume diante de
   uma alteração comercial de preço definida antes dos resultados. Diferenças estatísticas devem ser
   acompanhadas de tamanho de efeito e intervalo de confiança.
4. **Equivalência:** p-valor alto não demonstra elasticidades iguais. Se houver uma margem prática de
   equivalência, defini-la antes do teste e verificar se o intervalo da diferença está integralmente
   dentro dela. Sem essa margem, concluir apenas ausência de evidência suficiente para heterogeneidade.
5. **Validação temporal:** executar `ELAST_COMPARTILHADA` e `ELAST_POR_CONTEXTO` nas mesmas janelas expansivas e calcular todas as
   métricas congeladas, globalmente, por contexto e por semana. O ganho não pode depender de uma única
   data ou apenas do ajuste nos 76 dias.
6. **Complexidade:** comparar BIC e AICc, pois os dois candidatos usam a mesma resposta e observações
   e são aninhados. Tratar `ΔBIC < 2` como inconclusivo; diferenças entre 2 e 6 como evidência moderada;
   e diferenças superiores a 6 como evidência mais forte, sempre em conjunto com validação temporal.
7. **Estabilidade:** acompanhar elasticidades em cada janela expansiva, bootstrap por blocos
   semanais, leave-one-out, distância de Cook, VIF e número de mudanças de sinal.
8. **Cobertura:** reportar quantidade de observações e amplitude de preço por contexto. Sexta e fim de
   semana não podem receber a mesma confiança da categoria com maior cobertura.
9. **Visualização ajustada:** traçar retas em `ln(preço) × ln(volume)` e curvas na escala original,
   com bandas de confiança, mesmo preço de referência e somente suporte comum. O gráfico complementa,
   mas não substitui, testes e validação.
10. **Inclinação positiva:** não interpretar automaticamente uma elasticidade positiva como demanda
    crescente. Verificar intervalo, bootstrap, influência, endogeneidade e estabilidade. Uma
    inclinação positiva ou com frequentes mudanças de sinal torna a curva daquele contexto inadequada
    para otimização sem pooling, regularização ou restrição monotônica previamente justificada.

Promover `ELAST_POR_CONTEXTO` apenas se ele melhorar de forma consistente a validação temporal, apresentar ganho de
BIC ou AICc compatível com os parâmetros adicionais, produzir diferenças operacionalmente relevantes
e manter elasticidades negativas e estáveis. Se o teste for significativo, mas a previsão piorar,
manter `ELAST_COMPARTILHADA` para o objetivo preditivo e registrar a heterogeneidade como limitação. Se a previsão
melhorar sem precisão inferencial, classificar o resultado como preditivo e incerto, sem alegação
estrutural.

### 5.4 Ajuste do campeão nos 76 dias

1. Ajustar o modelo escolhido em todo o período de desenvolvimento.
2. Calcular coeficientes, intervalos e matriz de covariância robusta HC3.
3. Calcular o fator de smearing de Duan usando apenas os resíduos do desenvolvimento.
4. Registrar a faixa de preços observada para cada contexto aceito pelo modelo.
5. Gerar a equação explícita na escala logarítmica e a função de previsão em kg.
6. Registrar se a elasticidade final é compartilhada ou específica por contexto, com todas as
   fórmulas necessárias para reconstruí-la.
7. Salvar a especificação antes de carregar o holdout.

### 5.5 Diagnósticos obrigatórios

1. Resíduos contra valores ajustados e contra preço.
2. Resíduos ao longo do tempo e por calendário.
3. QQ-plot como diagnóstico, sem exigir normalidade perfeita para previsão.
4. Heterocedasticidade e uso de erros robustos quando necessário.
5. Autocorrelação residual e estatística de Durbin-Watson.
6. Alavancagem, distância de Cook e leave-one-out da elasticidade.
7. Comparação OLS versus Huber sem remover observações.
8. Sensibilidade com e sem FDS para medir sua influência na estrutura de elasticidade selecionada.
9. Verificação de colinearidade entre preço, variáveis de calendário, tendência e interações.
10. Discussão de endogeneidade: preço pode refletir demanda antecipada e variáveis omitidas. Sem
    instrumento ou teste de preço, a curva deve ser apresentada como resposta preditiva
    observacional, não como efeito causal definitivamente identificado.

### 5.6 Incerteza para a otimização

O desafio alerta que uma previsão pontual pode ser limitadora. O Notebook 2 deve fornecer:

1. previsão central com smearing;
2. distribuição empírica dos erros produzidos na validação temporal;
3. fatores de cenário conservador, central e otimista na escala de volume;
4. intervalo de parâmetros ou bootstrap por blocos semanais como análise de sensibilidade;
5. alerta de maior incerteza em contextos com pouca cobertura, especialmente FDS.

Os cenários devem preservar positividade e ser simples o suficiente para utilização no modelo de
otimização.

### 5.7 Avaliação no holdout oficial

1. Confirmar que o artefato do campeão já foi salvo.
2. Carregar `minerva_holdout.csv` pela primeira vez no novo fluxo.
3. Gerar previsões sem reestimar parâmetros ou smearing.
4. Calcular o mesmo painel congelado da validação interna: WMAPE, MAE, RMSE, erro absoluto mediano,
   sMAPE, RMSLE, viés em kg e percentual, WMAPE semanal e erro do volume acumulado.
5. Verificar se todos os preços do holdout pertencem ao suporte do treino.
6. Registrar que o período não contém FDS e, portanto, não valida seu intercepto nem uma eventual
   elasticidade específica de fim de semana.
7. Não alterar o modelo com base no resultado. Qualquer alteração posterior transforma o holdout em
   validação de desenvolvimento e deve ser registrada como nova versão.

### 5.8 Artefato da curva

`models/demand_curve_champion.json` deve conter, no mínimo:

- fórmula e versão da especificação;
- coeficientes e nomes das variáveis;
- indicação de elasticidade compartilhada ou variável, elasticidade por contexto, intervalos e teste
  conjunto das interações;
- fator de smearing;
- suporte comum utilizado para comparar inclinações e preço de referência da centralização;
- faixa de preço por contexto;
- período e número de linhas de treino;
- hash da base processada e do código relevante;
- métricas de validação temporal e do holdout;
- sinalização de que a relação é observacional;
- versão dos pacotes usados.

`models/demand_curve_uncertainty.json` deve conter os multiplicadores ou quantis usados nos cenários
de volume.

### 5.9 Entregáveis do Notebook 2

- Ranking auditável dos candidatos.
- Tabela detalhada dos três folds temporais, resumo de WMAPE de treino e validação, *gap*, dispersão
  e pior janela para cada candidato.
- Tabela incremental com variáveis adicionadas, p-valores robustos dos blocos, tamanhos de efeito,
  métricas de erro e variações contra o modelo anterior.
- Tabela de contrastes de calendário com correção de Holm e interpretação que não confunda ausência
  de significância com equivalência.
- Comparação `ELAST_COMPARTILHADA × ELAST_POR_CONTEXTO` com Wald HC3, BIC, AICc, métricas temporais, elasticidades por contexto e
  estabilidade de sinal.
- Gráficos das inclinações no suporte comum, com bandas de confiança nas escalas logarítmica e
  original.
- Curva campeã e sua interpretação econômica.
- Previsões temporais internas e do holdout.
- Diagnósticos de resíduos, influência e robustez.
- Artefatos JSON independentes do notebook.
- Tabela que transforma preço e contexto em volume central, conservador e otimista.
- Limites explícitos para utilização pelo otimizador.

### 5.10 Critério de conclusão

O Notebook 2 está concluído quando os agrupamentos estão justificados por contrastes refeitos no
próprio documento, a tabela incremental apresenta todas as métricas congeladas, a escolha entre
elasticidade compartilhada e variável está documentada por inferência, complexidade e validação, e
`predict_volume(preço, contexto)` pode ser executada a partir do artefato salvo, reproduz as
previsões documentadas, bloqueia extrapolações e fornece cenários de incerteza sem reabrir a seleção
do modelo.

## 6. Notebook 3: otimização matemática de preços

### 6.1 Pergunta narrativa

> Por que a formulação oficial é infactível, quais restrições entram em conflito e qual é a menor
> alteração operacional necessária para recuperar a viabilidade antes de maximizar a margem?

O caso oficial, com preço inicial de 31/10/2025, variação máxima de R$ 2,00 e metas semanais, deve
ser resolvido primeiro sem remover restrições. A infactibilidade esperada é um resultado do desafio,
mas não encerra a análise: o notebook deve localizar suas fontes, quantificar os déficits e comparar
formas mínimas de superá-la.

### 6.2 Contrato de entrada

O notebook deve consumir apenas:

- `demand_curve_champion_livro.json`, produzido pelo Notebook 2.1;
- `demand_curve_uncertainty_livro.json`, produzido pelo Notebook 2.1;
- calendário do horizonte de duas semanas;
- meta e tolerância semanal da aba `meta_vol_variacao_preco`;
- variação máxima permitida entre dias consecutivos;
- faixa de preço validada por contexto no artefato da curva;
- histórico de custo somente até 31/10/2025;
- último preço conhecido em 31/10/2025;
- alíquota de imposto de 7%, informada pela equipe do desafio.

O Notebook 2.1 permanece a fonte de verdade da curva. `src/modeling/demand_curve.py` deve apenas
validar e reproduzir o artefato, incluindo compatibilidade com o contrato de hash da versão 1. O
otimizador não pode redefinir coeficientes, suporte, *smearing* ou cenários. Se uma família completa
de curvas for acrescentada, seus parâmetros devem ser exportados pelo Notebook 2.1 em novo artefato,
mantendo inalterado o núcleo da curva campeã.

O custo realizado do período futuro não pode ser utilizado para escolher preços. Em um backtest,
ele só pode aparecer depois da recomendação, para uma avaliação ex post claramente identificada.

### 6.3 Imposto, custo e margem

Para cada dia `t` do horizonte:

- variável de decisão: preço `p_t`;
- demanda prevista: `q_t(p_t, contexto_t)`;
- custo unitário previsto: `c_t` em R$/kg;
- alíquota sobre a receita: `tau = 0,07`;
- margem esperada: `[(1 - tau) × p_t - c_t] × q_t`.

`Custo Realizado (R$)` é o custo total do volume vendido no dia. O custo unitário histórico deve ser
calculado como:

```text
custo_kg_t = custo_realizado_rs_t / volume_realizado_kg_t
```

Para resumir uma janela, a média correta é ponderada por volume:

```text
custo_kg_ponderado = soma(custo_realizado_rs) / soma(volume_realizado_kg)
```

A janela do custo não será escolhida por conveniência. O Notebook 3 deve comparar, usando somente o
desenvolvimento, os seguintes previsores de custo constante para as duas semanas seguintes:

1. último custo unitário observado;
2. média ponderada da última semana;
3. média ponderada das últimas duas semanas;
4. média ponderada das últimas quatro semanas;
5. média ponderada expansiva;
6. média móvel exponencial parcimoniosa.

A escolha deve usar validação temporal com origem móvel: em cada corte, estimar o custo apenas com o
passado e prever o custo ponderado agregado das duas semanas seguintes. MAE em R$/kg será a métrica
primária; RMSE e viés serão secundários. Candidatos com MAE até 5% acima do melhor serão considerados
equivalentes; entre eles, vencerá o mais simples, com menor viés absoluto e maior estabilidade entre
janelas. A regra escolhida será congelada antes do acesso aos custos do holdout.

Como referências, sem antecipar a seleção, o desenvolvimento apresenta aproximadamente R$ 981,22/kg
na média ponderada completa, R$ 988,85/kg nas últimas quatro semanas, R$ 1.003,66/kg nas últimas duas
semanas, R$ 1.004,97/kg na última semana e R$ 1.010,45/kg no último dia.

Objetivo após selecionar a premissa de custo:

```text
maximizar  soma_t [((1 - 0,07) × p_t - c_t) × q_t(p_t, contexto_t)]
```

Além dos 7% centrais, executar sensibilidade com alíquotas de 0%, 5% e 10%. O caso de 0% deve ser
descrito como margem antes de impostos, nunca como margem líquida.

### 6.4 Formulação oficial estrita

O horizonte oficial contém as dez datas de 03/11/2025 a 14/11/2025. O preço anterior é
`p_0 = R$ 1.318,92/kg`, observado em 31/10/2025.

Restrições obrigatórias:

```text
meta_semana × (1 - tolerancia) <= soma_t q_t <= meta_semana × (1 + tolerancia)

|p_1 - p_0| <= variacao_maxima

|p_t - p_(t-1)| <= variacao_maxima

preco_min_contexto <= p_t <= preco_max_contexto
```

Na instância, cada semana possui meta de 165 kg, tolerância de 30% e faixa admissível de 115,5 a
214,5 kg. O PDF menciona 5%; a otimização principal deve usar os 30% da planilha e tratar 5% como
sensibilidade documentada. A variação máxima é R$ 2,00 entre decisões consecutivas, inclusive na
fronteira entre 31/10 e 03/11.

O suporte de preço permanece uma restrição rígida em todas as análises. Relaxá-lo equivaleria a
extrapolar a curva e não será aceito como estratégia de recuperação.

### 6.5 Diagnóstico das fontes de infactibilidade

Antes de maximizar margem, o notebook deve construir os envelopes mínimo e máximo de preços
alcançáveis sob suporte, preço inicial e variação. Como a curva campeã é estritamente decrescente no
suporte, esses envelopes determinam os limites de volume possíveis em cada semana.

O diagnóstico preliminar da curva central indica máximos de aproximadamente 79,2 kg e 87,1 kg,
contra o mínimo contratual de 115,5 kg. O notebook deve recalcular e registrar:

- volume mínimo e máximo alcançável por semana;
- déficit para a meta mínima, em kg e percentual;
- dias presos ao limite de variação ou ao suporte;
- restrições ativas e respectivas folgas;
- efeito incremental de adicionar preço inicial, variação e meta à formulação;
- cenário de demanda em que cada conflito ocorre.

A fonte deve ser atribuída à combinação de restrições, não a uma regra isolada. Para isso, executar
uma sequência aninhada: suporte; suporte mais preço inicial; suporte mais preço inicial e variação;
e, por fim, todas as restrições com a meta semanal.

### 6.6 Estratégias de recuperação da viabilidade

Cada alternativa deve ser resolvida em duas etapas: primeiro minimizar exatamente a relaxação
escolhida; depois fixar esse mínimo e maximizar a margem. Assim, o solver não recebe liberdade para
relaxar uma regra além do necessário apenas para melhorar o objetivo financeiro.

#### 6.6.1 Desconsiderar o preço inicial

Remover somente a ligação `|p_1 - p_0| <= 2`, mantendo R$ 2,00 entre as dez decisões. Reportar o
salto entre 31/10 e 03/11, os volumes, a margem e a consequência operacional.

#### 6.6.2 Aumentar a variação entre dias

Substituir o limite fixo por uma variável `Delta` e resolver `minimizar Delta` sujeito às metas,
suporte e preço inicial. Depois, fixar o menor `Delta` viável e maximizar a margem.

#### 6.6.3 Liberar apenas a transição inicial

Calcular o menor `Delta_inicial` em `|p_1 - p_0| <= Delta_inicial`, preservando R$ 2,00 nos demais
pares. Essa alternativa separa a entrada no horizonte da estabilidade dentro das duas semanas.

#### 6.6.4 Relaxar meta ou tolerância

Com preço inicial e R$ 2,00 mantidos, calcular separadamente:

- folga mínima em kg para o limite inferior de cada semana;
- menor meta nominal comum que torna as duas semanas viáveis;
- menor tolerância percentual comum necessária para a meta de 165 kg.

#### 6.6.5 Relaxações combinadas

Construir uma fronteira de Pareto entre salto inicial, variação diária e folga de volume. Não somar
penalidades de unidades diferentes para produzir uma escolha arbitrária. A decisão final deve
comparar alterações operacionais transparentes, margem e exposição à incerteza.

### 6.7 Estratégia numérica

1. Formular inicialmente um problema não linear contínuo, pois a curva de potência é suave e o
   horizonte possui poucas variáveis.
2. Executar o teste determinístico de viabilidade antes do solver de margem.
3. Resolver cada problema com múltiplos pontos iniciais e semente fixa.
4. Verificar a solução com recomputação independente do objetivo e de todas as restrições.
5. Se o solver contínuo apresentar instabilidade, discretizar a faixa permitida de preço e resolver
   por busca estruturada ou programação dinâmica.
6. Fixar tolerâncias numéricas e critérios de convergência no código.
7. Nunca permitir que o solver ultrapasse o suporte validado da curva.
8. Nunca gerar plano diário quando o status permanecer infactível.

### 6.8 Baselines e sensibilidades

Comparar a política otimizada com alternativas compreensíveis:

1. manter o último preço observado;
2. usar preço constante que tenta cumprir a meta;
3. ótimo sem meta semanal;
4. ótimo sem preço inicial;
5. ótimo sem limite de variação;
6. ótimo após cada relaxação mínima;
7. preços históricos do holdout, somente na avaliação ex post.

Variar a meta entre 80%, 90%, 100%, 110% e 120% de 165 kg; testar limites de preço de R$ 0, R$ 1,
R$ 2, R$ 5, R$ 10 e ilimitado; e repetir as políticas para as premissas baixa, central e alta de
custo e imposto. Políticas infactíveis devem permanecer nas tabelas com diagnóstico, não ser
silenciosamente excluídas.

### 6.9 Incerteza e famílias de curvas

Resolver o problema para:

- cenário central;
- cenário conservador de volume;
- cenário otimista de volume;
- família de curvas por parâmetros bootstrap, se exportada pelo Notebook 2.1.

Os multiplicadores existentes representam incerteza de nível, não elasticidades diferentes. Para
uma família completa, o Notebook 2.1 deve salvar intercepto, elasticidade, efeitos de calendário e
*smearing* de cada réplica válida. O Notebook 3 calculará, para cada curva, a frequência de
viabilidade, o déficit, a relaxação mínima e a margem. O otimizador não pode inventar parâmetros que
não tenham sido produzidos pela etapa estatística.

### 6.10 Validações do otimizador

1. Todas as restrições devem ter folga e status calculados.
2. A meta deve ser verificada separadamente por semana.
3. A variação deve incluir a fronteira entre 31/10 e 03/11 no caso oficial.
4. Custo e imposto devem ser recompostos linha a linha na margem.
5. A previsão deve vir do artefato, não de coeficientes copiados.
6. Objetivo e restrições devem ser recalculados após a solução.
7. Diferentes pontos iniciais devem produzir solução equivalente.
8. O problema oficial deve retornar infactível enquanto suas regras permanecerem inalteradas.
9. Cada solução recuperada deve informar qual regra mudou e quanto mudou.
10. O holdout não pode participar da escolha da regra de custo nem da política de preços.

### 6.11 Storytelling dos resultados

O notebook deve terminar com, no mínimo:

1. auditoria do imposto e da seleção temporal da premissa de custo;
2. tabela do problema oficial com volumes alcançáveis, déficits e restrições ativas;
3. tabela das relaxações mínimas e da fronteira de Pareto;
4. plano diário somente para alternativas factíveis;
5. resumo semanal com meta, volume, margem e folgas;
6. gráficos de trajetória, fontes de infactibilidade e custo das relaxações;
7. matriz que aplica cada política aos cenários de demanda, custo e imposto.

A conclusão deve separar claramente:

- o que é consequência dos dados históricos;
- o que é premissa operacional;
- o que é resultado matemático do otimizador;
- qual restrição foi relaxada em cada alternativa;
- o que ainda precisa de validação futura.

### 6.12 Entregáveis do Notebook 3

- Diagnóstico em `data/processed/minerva_diagnostico_infactividade.json`.
- Plano diário das alternativas factíveis em `data/processed/minerva_plano_precos.csv`.
- Resultado completo em `data/processed/minerva_otimizacao_resultado.json`.
- Tabela de seleção temporal da premissa de custo.
- Tabela de relaxações mínimas e fronteira de Pareto.
- Comparação com baselines e cenários de demanda, custo e imposto.
- Figuras finais em `reports/figures/`.
- Recomendação operacional condicionada à alteração aceita nas regras.

### 6.13 Critério de conclusão

O Notebook 3 está concluído quando reproduz a infactibilidade oficial, identifica suas fontes,
calcula as menores relaxações de cada alternativa, seleciona custo sem vazamento temporal, aplica o
imposto de 7%, gera planos apenas para problemas factíveis e permite reproduzir todos os resultados
a partir dos artefatos salvos.

## 7. Fluxo entre os notebooks

```text
Planilha original
      |
      v
Notebook 1: qualidade, variáveis e hipóteses
      |
      +--> dados de treino processados
      +--> holdout isolado
      +--> candidatos e critérios congelados
      |
      v
Notebook 2: validação temporal e curva campeã
      |
      +--> curva de demanda em JSON
      +--> suporte de preço
      +--> cenários de incerteza
      +--> métricas e diagnósticos
      |
      v
Notebook 3: otimização matemática
      |
      +--> diagnóstico das fontes de infactibilidade
      +--> custo previsto e imposto congelados
      +--> relaxações mínimas e fronteira de Pareto
      +--> planos factíveis, volumes e margens esperados
      +--> recomendação condicionada à regra alterada
```

## 8. Ordem de implementação

### Etapa 1: exploração e contrato dos dados

1. Construir o Notebook 1 de forma autocontida, com leitura, auditoria e variáveis visíveis.
2. Revisar a sazonalidade, o suporte e as hipóteses candidatas.
3. Persistir os conjuntos e catálogos necessários para a etapa seguinte.
4. Somente depois da revisão, promover para `src/` as transformações que o Notebook 2 precisará
   reproduzir em treino e inferência.

### Etapa 2: protocolo estatístico

1. Generalizar `src/modeling/demand_curve.py` para receber especificações candidatas.
2. Implementar expanding window e métricas em `src/modeling/train.py`.
3. Implementar previsão e cenários em `src/modeling/predict.py`.
4. Criar testes de smearing, suporte, serialização e ausência de vazamento.
5. Construir o Notebook 2 e congelar o artefato.

### Etapa 3: decisão ótima

1. Corrigir a compatibilidade do leitor com o hash da versão 1 emitida pelo Notebook 2.1.
2. Selecionar temporalmente a regra de previsão do custo unitário, sem usar o holdout.
3. Congelar imposto de 7%, preço inicial e restrições da instância.
4. Implementar os envelopes de viabilidade e `src/optimization/price_schedule.py`.
5. Criar testes de margem, metas, suporte, preço inicial, variação e infactibilidade.
6. Implementar as relaxações mínimas e a fronteira de Pareto.
7. Construir o Notebook 3 e executar sensibilidades de demanda, custo e imposto.
8. Se necessária uma família completa, promover as réplicas bootstrap do Notebook 2.1 para um
   artefato adicional sem alterar a curva campeã.

### Etapa 4: revisão integrada

1. Executar os três notebooks do início ao fim em ambiente limpo.
2. Confirmar que nenhum notebook depende do estado de execução de outro.
3. Rodar testes automatizados.
4. Conferir hashes, versões e caminhos dos artefatos.
5. Revisar se todas as afirmações respeitam as limitações da amostra.

## 9. Riscos e mitigação

| Risco | Consequência | Mitigação |
|---|---|---|
| Amostra pequena | Sobreajuste e coeficientes instáveis | Poucos candidatos, inclinação compartilhada e validação temporal |
| Apenas dez observações de FDS | Nível e elasticidade pouco precisos | Agrupamento parcimonioso, sensibilidade e alerta de incerteza |
| Preço médio derivado de receita/volume | Erro de mensuração ou simultaneidade | Documentar como proxy e solicitar preço de lista quando possível |
| Preço definido antecipando demanda | Endogeneidade | Linguagem observacional, diagnóstico e futuro teste de preço |
| Ausência de estoque | Vendas podem estar censuradas | Registrar limitação e solicitar estoque/ruptura |
| Holdout já consultado | Avaliação otimista | Seleção interna temporal, transparência e futura validação externa |
| Transformação logarítmica | Viés ao retornar para kg | Smearing estimado somente no treino de cada ajuste |
| Otimizador extrapolar a curva | Recomendações sem suporte | Limites de preço obrigatórios por contexto |
| Uso de custo futuro realizado | Vazamento na decisão | Premissa de custo congelada antes do horizonte |
| Janela de custo escolhida informalmente | Margem baseada em custo defasado ou ruidoso | Seleção temporal entre previsores simples e sensibilidade |
| Imposto ausente na planilha | Margem superestimada | Usar 7% informado pela equipe e testar 0%, 5% e 10% |
| Problema oficial infactível | Solver sem solução ou relaxação oculta | Diagnóstico por envelopes e relaxações mínimas em duas etapas |
| Penalidades de unidades diferentes | Escolha arbitrária entre preço e volume | Fronteira de Pareto em vez de soma ponderada ad hoc |
| Multiplicadores tratados como família de curvas | Incerteza de elasticidade subestimada | Exportar parâmetros bootstrap pelo Notebook 2.1 quando necessário |
| Divergência PDF versus planilha | Restrição incorreta | Ler parâmetros da instância e registrar a divergência |

## 10. Decisões fechadas e pendências operacionais

Decisões já fechadas para o Notebook 3:

1. imposto central de 7% sobre a receita, com sensibilidades de 0%, 5% e 10%;
2. preço inicial de R$ 1.318,92/kg em 31/10/2025;
3. tolerância principal de 30% lida da instância e 5% como sensibilidade do texto do PDF;
4. custo histórico calculado por `custo_realizado_rs / volume_realizado_kg`;
5. regra de previsão do custo escolhida por validação temporal, não por janela arbitrária;
6. problema oficial mantido estrito antes de qualquer relaxação;
7. suporte da curva nunca relaxado.

Pendências que não impedem o diagnóstico, mas condicionam a recomendação operacional final:

1. preços podem ser contínuos ou precisam respeitar incrementos comerciais?
2. qual alternativa de recuperação é comercialmente preferível: salto inicial, maior variação,
   menor meta ou maior tolerância?
3. a operação exige proteção no cenário conservador ou aceita uma política central com exposição
   explícita ao risco?
4. sábados e domingos farão parte de horizontes futuros, apesar de não aparecerem no holdout atual?

## 11. Definição de pronto do projeto analítico

O fluxo completo estará pronto quando:

- a planilha original permanecer imutável;
- os dados processados forem reproduzíveis por código em `src/`;
- a EDA não utilizar o holdout para criar hipóteses;
- a curva for escolhida por validação temporal e permanecer parcimoniosa;
- a previsão em kg corrigir a retransformação e bloquear extrapolação;
- a incerteza for entregue ao otimizador em cenários reproduzíveis;
- a infactibilidade oficial for reproduzida e explicada por restrições identificáveis;
- as menores relaxações de preço e volume forem calculadas antes da maximização da margem;
- custo e imposto forem definidos sem vazamento e submetidos a sensibilidade;
- todo plano recomendado respeitar suporte e a formulação relaxada explicitamente declarada;
- os efeitos da meta e da variação pedidas pelo desafio forem quantificados;
- testes automatizados validarem os contratos principais;
- limitações causais e de cobertura forem apresentadas sem ambiguidade.

## 12. Referências do projeto

- Desafio Minerva-Unifesp-ITA, em `docs/referencias/Minerva_Unifesp_ITA.pdf`, especialmente as seções de
  relação volume-preço, definição do problema, arquivo de dados e ferramenta desejada.
- Robert L. Phillips, *Pricing and Revenue Optimization*, em
  `docs/referencias/dokumen.pub_pricing-and-revenue-optimization-second-edition-9781503614260.pdf`,
  capítulos 3 a 5, com destaque para modelos de demanda, estimação da resposta a preço, seleção
  champion-challenger, colinearidade, endogeneidade e otimização.
- Pavan Nithin Mullapudi, *Pricing Optimization across Domains*, em
  `docs/referencias/IJERET-V6I3P103.pdf`, para a arquitetura econometria + pesquisa operacional e
  para variáveis adicionais usadas em pricing.
