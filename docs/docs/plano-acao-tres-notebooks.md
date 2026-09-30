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

- Cada notebook deve ser construído a partir da fonte bruta, do enunciado do desafio e das
  referências bibliográficas listadas neste plano.
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
- Somente referências bibliográficas e o enunciado do desafio podem fundamentar escolhas
  metodológicas; nenhuma referência cruzada a testes anteriores deve aparecer no documento final.

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
6. Comparar o esquema real com o PDF: o enunciado menciona imposto realizado, mas a planilha atual
   não possui essa coluna. Registrar a diferença sem criar valores artificiais.
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
| `P0` | `ln(volume) ~ ln(preco)` | Baseline de potência sem calendário |
| `P1` | `ln(volume) ~ ln(preco) + fim_semana` | Calendário mínimo |
| `P2` | `ln(volume) ~ ln(preco) + C(dia_semana)` | Níveis diários completos |
| `P3` | `ln(volume) ~ ln(preco) + grupo_calendario` | Partição parcimoniosa motivada pelo treino |
| `P4` | campeão de calendário + `indice_tempo` | Sensibilidade a mudança temporal |
| `E1` | `ln(volume) ~ preco + calendário campeão` | Forma exponencial como challenger |
| `L1` | `volume ~ preco + calendário campeão` | Diagnóstico linear; rejeitar se gerar volume negativo |

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
3. Usar uma janela inicial suficientemente grande para estimar os candidatos; a proposta é começar
   com 55 observações e prever cada observação seguinte em esquema expanding window.
4. Em cada passo, ajustar o modelo apenas com o passado.
5. Recalcular dentro de cada janela toda estatística dependente do treino, inclusive smearing,
   médias, limites e transformações ajustadas.
6. Registrar previsão, erro, data, dia da semana, preço e versão do candidato para cada origem.
7. Calcular métricas globais e por semana; não escolher pelo melhor dia isolado.

### 5.3 Seleção champion-challenger

Executar em duas rodadas para evitar uma combinação excessiva de alternativas:

1. **Rodada de calendário:** comparar `P0`, `P1`, `P2` e `P3` com a mesma forma de potência e
   elasticidade compartilhada.
   Incluir também uma segunda partição agrupada que separe segunda-feira de terça a quinta. As duas
   distinções de calendário devem ser reestimadas pelo mesmo protocolo, sem herdar resultados ou
   parâmetros já calculados.
2. **Rodada de forma funcional:** usando a estrutura de calendário vencedora, comparar potência,
   exponencial e linear.
3. **Rodada opcional de tendência:** desafiar o campeão com `indice_tempo` apenas se a EDA tiver
   mostrado mudança persistente e a variável melhorar a validação temporal.

Regras de decisão:

- o challenger deve melhorar a métrica primária de maneira consistente, não apenas em um ponto;
- se a diferença for pequena, manter o modelo com menos parâmetros;
- rejeitar modelos com comportamento operacional inválido, como volumes negativos;
- não promover interações `preço × calendário` com a amostra atual, salvo evidência excepcional e
  explicitamente documentada;
- registrar todos os modelos tentados para evitar seleção informal posterior.

Antes dessas rodadas, ajustar e reportar a regressão preço-volume na leitura mais direta do
enunciado, em escala original, e um baseline sem calendário em escala log-log. Esses modelos
documentam a proposta mínima do desafio e devem ser comparados, pelas mesmas métricas temporais, com
as especificações enriquecidas pelo calendário.

### 5.4 Ajuste do campeão nos 76 dias

1. Ajustar o modelo escolhido em todo o período de desenvolvimento.
2. Calcular coeficientes, intervalos e matriz de covariância robusta HC3.
3. Calcular o fator de smearing de Duan usando apenas os resíduos do desenvolvimento.
4. Registrar a faixa de preços observada para cada contexto aceito pelo modelo.
5. Gerar a equação explícita na escala logarítmica e a função de previsão em kg.
6. Salvar a especificação antes de carregar o holdout.

### 5.5 Diagnósticos obrigatórios

1. Resíduos contra valores ajustados e contra preço.
2. Resíduos ao longo do tempo e por calendário.
3. QQ-plot como diagnóstico, sem exigir normalidade perfeita para previsão.
4. Heterocedasticidade e uso de erros robustos quando necessário.
5. Autocorrelação residual e estatística de Durbin-Watson.
6. Alavancagem, distância de Cook e leave-one-out da elasticidade.
7. Comparação OLS versus Huber sem remover observações.
8. Sensibilidade com e sem FDS para medir sua influência na elasticidade compartilhada.
9. Verificação de colinearidade entre preço e variáveis de calendário ou tendência.
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
4. Calcular WMAPE, RMSE, viés e erro de volume semanal.
5. Verificar se todos os preços do holdout pertencem ao suporte do treino.
6. Registrar que o período não contém FDS e, portanto, não valida essa parte da curva.
7. Não alterar o modelo com base no resultado. Qualquer alteração posterior transforma o holdout em
   validação de desenvolvimento e deve ser registrada como nova versão.

### 5.8 Artefato da curva

`models/demand_curve_champion.json` deve conter, no mínimo:

- fórmula e versão da especificação;
- coeficientes e nomes das variáveis;
- fator de smearing;
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
- Curva campeã e sua interpretação econômica.
- Previsões temporais internas e do holdout.
- Diagnósticos de resíduos, influência e robustez.
- Artefatos JSON independentes do notebook.
- Tabela que transforma preço e contexto em volume central, conservador e otimista.
- Limites explícitos para utilização pelo otimizador.

### 5.10 Critério de conclusão

O Notebook 2 está concluído quando `predict_volume(preço, contexto)` pode ser executada a partir do
artefato salvo, reproduz as previsões documentadas, bloqueia extrapolações e fornece cenários de
incerteza sem reabrir a seleção do modelo.

## 6. Notebook 3: otimização matemática de preços

### 6.1 Pergunta narrativa

> Dada a curva de demanda congelada, qual sequência diária de preços produz a maior margem esperada
> sem violar metas de volume e estabilidade comercial?

### 6.2 Contrato de entrada

O notebook deve consumir apenas:

- `demand_curve_champion.json`;
- `demand_curve_uncertainty.json`;
- calendário do horizonte de duas semanas;
- meta e tolerância semanal da aba `meta_vol_variacao_preco`;
- variação máxima permitida entre dias consecutivos;
- faixa de preço validada;
- custo unitário previsto ou uma premissa definida antes do horizonte;
- último preço conhecido antes do primeiro dia da otimização.

O custo realizado do período futuro não pode ser utilizado para escolher preços. Em um backtest,
ele só pode aparecer depois da recomendação, para uma avaliação ex post claramente identificada.

### 6.3 Definições matemáticas

Para cada dia `t` do horizonte:

- variável de decisão: preço `p_t`;
- demanda prevista: `q_t(p_t, contexto_t)`;
- custo unitário previsto: `c_t`;
- margem esperada: `(p_t - c_t) × q_t`.

Se uma coluna confiável de imposto ficar disponível, a função objetivo deverá descontá-la de forma
explícita. Com a planilha atual, a medida é contribuição após custo realizado/previsto, não margem
líquida completa.

Objetivo central:

```text
maximizar  soma_t [(p_t - c_t) × q_t(p_t, contexto_t)]
```

Restrições obrigatórias:

```text
meta_semana × (1 - tolerancia) <= soma_t q_t <= meta_semana × (1 + tolerancia)

|p_t - p_(t-1)| <= variacao_maxima

preco_min_contexto <= p_t <= preco_max_contexto
```

A restrição de variação também deve ligar o primeiro dia do horizonte ao último preço histórico ou
operacional conhecido.

### 6.4 Estratégia de solução

1. Formular inicialmente um problema não linear contínuo, pois a curva de potência é suave e o
   horizonte possui poucas variáveis.
2. Resolver com múltiplos pontos iniciais para reduzir o risco de aceitar um ótimo local.
3. Verificar a solução com recomputação independente do objetivo e de todas as restrições.
4. Se o solver contínuo apresentar instabilidade, discretizar a faixa permitida de preço e resolver
   por busca estruturada ou programação dinâmica.
5. Fixar tolerâncias numéricas e critérios de convergência no código.
6. Nunca permitir que o solver ultrapasse o suporte validado da curva.

### 6.5 Baselines de decisão

Comparar a política otimizada com alternativas compreensíveis:

1. manter o último preço observado;
2. usar preço constante que tenta cumprir a meta;
3. repetir uma política média histórica por dia da semana;
4. ótimo sem meta semanal;
5. ótimo com meta, mas sem limite de variação;
6. ótimo completo com todas as restrições.

Esses baselines mostram de onde vem o ganho e quanto cada restrição custa em margem.

### 6.6 Cenários de demanda

Resolver o problema para:

- cenário central;
- cenário conservador de volume;
- cenário otimista de volume;
- amostras adicionais de parâmetros ou resíduos, se o custo computacional permitir.

Uma solução é mais defensável quando permanece factível em cenários plausíveis. Caso a solução
central viole a meta no cenário conservador, o notebook deve mostrar a probabilidade ou frequência
da violação e oferecer uma alternativa mais robusta.

### 6.7 Análises de sensibilidade exigidas pelo desafio

#### Impacto da meta semanal

1. Resolver sem meta.
2. Resolver com a meta nominal.
3. Variar a meta em uma grade operacionalmente relevante.
4. Mostrar margem, volume, preço médio e restrições ativas.
5. Identificar quando a meta se torna inviável dentro do suporte de preços.

#### Impacto da variação máxima de preço

1. Resolver sem limite de variação.
2. Resolver com o limite da instância.
3. Testar limites mais rígidos e mais flexíveis.
4. Quantificar perda de margem e alteração da trajetória de volume.
5. Destacar quais dias ficam presos ao limite de mudança.

#### Impacto da incerteza da curva

1. Comparar políticas ótimas dos três cenários de volume.
2. Aplicar cada política aos demais cenários.
3. Avaliar margem mínima, média e dispersão.
4. Selecionar uma recomendação central e uma recomendação conservadora.

### 6.8 Validações do otimizador

1. Todas as restrições devem ter folga calculada e status de atendimento.
2. A meta deve ser verificada por semana, não apenas no total das duas semanas.
3. A variação deve ser validada entre todos os pares consecutivos, inclusive na fronteira inicial.
4. A previsão deve ser recalculada a partir do artefato, não de valores copiados do notebook.
5. O objetivo deve ser recalculado linha a linha após a solução.
6. Diferentes pontos iniciais devem produzir a mesma solução ou soluções com objetivo equivalente.
7. Cenários inviáveis devem gerar diagnóstico explícito, nunca uma tabela aparentemente válida.
8. Testes automatizados devem cobrir limites de preço, metas, variação e reprodução do objetivo.

### 6.9 Storytelling dos resultados

O notebook deve terminar com quatro visões:

1. tabela diária com preço, volume previsto, custo, margem e variação de preço;
2. resumo semanal com meta, intervalo permitido, volume previsto e margem;
3. gráfico da trajetória de preços e volumes ao longo das duas semanas;
4. gráfico de sensibilidade mostrando o custo das restrições e a incerteza da demanda.

A conclusão deve separar claramente:

- o que é consequência dos dados históricos;
- o que é premissa operacional;
- o que é resultado matemático do otimizador;
- o que ainda precisa de validação futura.

### 6.10 Entregáveis do Notebook 3

- Plano diário de preços em `data/processed/minerva_plano_precos.csv`.
- Resultado completo da execução em JSON, com entradas, versão da curva e status das restrições.
- Comparação com baselines.
- Sensibilidade à meta, ao limite de variação e à incerteza da demanda.
- Figuras finais em `reports/figures/`.
- Recomendação operacional central e alternativa conservadora.

### 6.11 Critério de conclusão

O Notebook 3 está concluído quando a sequência recomendada pode ser reproduzida apenas com os
artefatos salvos, todas as restrições são verificadas numericamente e o impacto de cada restrição
fica quantificado.

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
      +--> sequência diária de preços
      +--> volumes e margens esperados
      +--> sensibilidade às restrições
      +--> recomendação central e conservadora
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

1. Definir a premissa de custo futuro e o preço inicial do horizonte.
2. Implementar `src/optimization/price_schedule.py`.
3. Criar testes de objetivo, metas, limites e inviabilidade.
4. Construir o Notebook 3.
5. Rodar sensibilidades e preparar as figuras finais.

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
| Divergência PDF versus planilha | Restrição incorreta | Ler parâmetros da instância e registrar a divergência |

## 10. Decisões que precisam ser fechadas antes do Notebook 3

1. Qual custo unitário estará disponível antes de cada dia do horizonte?
2. A tolerância válida é sempre a informada na planilha da instância?
3. O imposto deve entrar na margem quando a coluna não está presente?
4. Qual preço anterior deve limitar o primeiro dia do horizonte?
5. Os preços podem ser contínuos ou precisam respeitar incrementos comerciais?
6. A operação aceita uma solução que cumpre a meta no cenário central, ou exige proteção no cenário
   conservador?
7. Sábados e domingos farão parte de horizontes futuros, apesar de não aparecerem no holdout atual?

Essas decisões não impedem os Notebooks 1 e 2, mas alteram a formulação da otimização.

## 11. Definição de pronto do projeto analítico

O fluxo completo estará pronto quando:

- a planilha original permanecer imutável;
- os dados processados forem reproduzíveis por código em `src/`;
- a EDA não utilizar o holdout para criar hipóteses;
- a curva for escolhida por validação temporal e permanecer parcimoniosa;
- a previsão em kg corrigir a retransformação e bloquear extrapolação;
- a incerteza for entregue ao otimizador em cenários reproduzíveis;
- a otimização respeitar meta, tolerância, suporte e variação diária;
- os efeitos das duas restrições pedidas pelo desafio forem quantificados;
- testes automatizados validarem os contratos principais;
- limitações causais e de cobertura forem apresentadas sem ambiguidade.

## 12. Referências do projeto

- Desafio Minerva-Unifesp-ITA, em `docs/Minerva_Unifesp_ITA.pdf`, especialmente as seções de
  relação volume-preço, definição do problema, arquivo de dados e ferramenta desejada.
- Robert L. Phillips, *Pricing and Revenue Optimization*, em
  `docs/referencias/dokumen.pub_pricing-and-revenue-optimization-second-edition-9781503614260.pdf`,
  capítulos 3 a 5, com destaque para modelos de demanda, estimação da resposta a preço, seleção
  champion-challenger, colinearidade, endogeneidade e otimização.
- Pavan Nithin Mullapudi, *Pricing Optimization across Domains*, em
  `docs/referencias/IJERET-V6I3P103.pdf`, para a arquitetura econometria + pesquisa operacional e
  para variáveis adicionais usadas em pricing.
