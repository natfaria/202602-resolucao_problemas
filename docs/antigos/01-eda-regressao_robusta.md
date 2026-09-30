# A Curva de Demanda por Regressão Robusta: uma Segunda Rota até o Mesmo Destino

## O desafio

Existe um produto vendido diariamente, cujo preço pode ser ajustado todo dia. A pergunta central é:
se o preço subir ou descer, quanto o volume vendido reage? Essa relação — a curva de demanda,
descrita pela forma `Volume = A · Preço⁻ᴮ` — é o insumo que qualquer decisão de precificação diária
precisa antes de poder otimizar margem sujeita a metas de venda, ao longo de um horizonte de
planejamento de 2 semanas.

O histórico disponível para responder essa pergunta é curto: 76 dias de treino e 10 dias de teste,
nunca usados para decidir nada, apenas para checar se o modelo acerta fora da amostra. Nenhum dos 10
dias de teste cai num sábado ou domingo — um sinal concreto de que a decisão operacional de
precificação pode nem precisar de um preço de fim de semana. O próprio enunciado do desafio observa
dois pontos que orientam toda a análise a seguir: primeiro, que dias da semana diferentes vendem
volumes diferentes, e que essa diferença pode mascarar a relação real entre preço e volume se todos
os dias forem tratados como um bloco único; segundo, que alguns preços ou faixas de preço podem
gerar demandas fora do padrão — dias que, se pesarem demais no cálculo, distorcem a conclusão sobre o
quanto o cliente realmente reage a preço.

Este relatório percorre a resposta em três etapas estritamente ordenadas — que variáveis entram e
como os dias se agrupam; qual a estrutura de elasticidade dado esse agrupamento; e o modelo final —
cada uma sustentada por mais de um critério estatístico, com as vezes em que esses critérios
discordaram entre si registradas explicitamente, não escondidas atrás de um único número.

## Etapa 1 — Quais dias entram, e como se agrupam

Olhar a distribuição de volume por dia da semana sugere, de cara, que os dias não são todos iguais: a
mediana de Segunda-feira se destaca acima de qualquer outro dia útil; Terça, Quarta e Quinta ocupam
uma faixa parecida entre si; Sexta cai bem abaixo desse grupo; e Sábado e Domingo, juntos, têm tão
poucas observações que qualquer leitura sobre eles precisa ser cautelosa. Essa leitura é o ponto de
partida — tratada como hipótese a testar, não como conclusão.

**Pergunta 1 — todos os dias devem ficar, cada um com seu próprio nível de venda?** Um torneio
formal comparou cinco candidatos, todos com uma única sensibilidade a preço (a pergunta sobre
sensibilidade variável vem só na Etapa 2): nenhuma diferenciação por dia; um grupo por dia da semana;
a hipótese lida no gráfico (Segunda isolada, trio regular, Sexta isolada, Fim de Semana à parte); e
dois candidatos adicionais que testam diretamente se separar Segunda ou Sexta se paga — absorvendo
cada um deles no grupo vizinho mais próximo.

O candidato sem diferenciação nenhuma errou mais que o dobro de qualquer alternativa — confirma que
ignorar o dia da semana descarta a maior parte da informação disponível. Um candidato que absorve
Sexta dentro do Fim de Semana chamou atenção por um motivo enganoso: teve, isoladamente, o menor erro
de previsão fora da amostra de todo o torneio, mas também o pior critério de simplicidade (BIC) por
uma margem enorme — um modelo mal especificado para Sexta, cujo erro baixo é coincidência do teste
ter só um único dia de sexta-feira, não evidência de que a estrutura generaliza. Isso reforça um
ponto que reaparece mais de uma vez nesta análise: um holdout de apenas 10 dias não é confiável o
bastante para decidir estrutura sozinho.

Entre os dois candidatos que de fato importavam — manter Segunda separada ou absorvê-la no trio
regular —, o critério de simplicidade ficou **empatado**, sem preferência real por nenhum dos dois.

**Pergunta 2 — o Fim de Semana deveria ser excluído do treino da curva de preço inteiramente?**
Nunca antes considerada como opção formal, essa alternativa foi testada diretamente: ajustar a curva
só sobre os 66 dias úteis, e comparar o erro fora da amostra contra os candidatos que incluem o Fim
de Semana no treino — uma comparação justa, já que o teste real não contém nenhum dia de fim de
semana de qualquer forma. O erro ficou praticamente igual com ou sem esses dias no treino, e uma
validação cruzada repetida confirmou: a diferença entre as duas opções é bem menor que a variação
natural entre diferentes divisões de treino/validação. Como manter o Fim de Semana no treino não
custa nada em termos de precisão para os dias úteis, e é a única fonte de informação sobre o nível de
venda desse período, a decisão foi mantê-lo no treino — testada, não presumida.

**Pergunta 3 — como agrupar o que sobrar, além de ler um gráfico?** Duas ferramentas adicionais,
vindas diretamente dos dados: uma comparação par-a-par entre todos os sete dias da semana, controlando
por preço e corrigindo estatisticamente para o fato de estarem sendo feitas várias comparações
simultâneas; e um agrupamento hierárquico não supervisionado sobre os coeficientes de um modelo que
trata cada dia individualmente. As duas ferramentas confirmaram que Domingo e Sábado não se
distinguem entre si, e que Quarta e Quinta não se distinguem de Terça — mas **nenhuma delas confirmou
que Segunda se distingue de Terça, Quarta ou Quinta**, ao contrário da leitura inicial do gráfico.

Isso deixou uma tensão genuína: o critério de simplicidade (BIC) empatado, e duas ferramentas
independentes de comparação de nível não confirmando a separação de Segunda. A tensão foi resolvida
por uma validação cruzada repetida — muitas divisões aleatórias diferentes de treino e validação,
não uma única — perguntando não "esse coeficiente é individualmente significativo?" mas "separar
Segunda melhora a previsão fora da amostra de forma consistente?". A resposta foi sim, de forma
estável ao longo de repetidas divisões: manter Segunda separada prevê melhor os dias úteis fora da
amostra. Essas duas leituras não são contraditórias de verdade — respondem perguntas diferentes.
Significância par-a-par corrigida é um padrão de evidência exigente, que perde poder com poucas
observações por dia; contribuição preditiva real, medida por repetição fora da amostra, não depende
de significância individual para existir. Diante do empate e da ausência de confirmação pelas outras
duas ferramentas, a validação cruzada foi usada como critério de desempate — com a ressalva explícita
de que essa é a decisão mais frágil de toda a análise.

O nível do Fim de Semana, por outro lado, não teve ambiguidade nenhuma: dar a ele um patamar próprio
reduz o critério de simplicidade por uma margem grande frente a juntá-lo com Sexta, e uma reamostragem
do coeficiente produz um intervalo de confiança que exclui zero com folga. A mediana bruta do volume
observado nesses dias e a previsão da curva ajustada para esses mesmos dias, nos preços observados,
ficaram razoavelmente próximas entre si — uma diferença de cerca de 15%, não gritante — deixando em
aberto, para a etapa final, a escolha entre usar o coeficiente da regressão conjunta ou uma
estatística separada para esse grupo.

**Agrupamento de nível vencedor da Etapa 1**: Segunda isolada / Terça+Quarta+Quinta juntas / Sexta
isolada / Fim de Semana à parte — o mesmo agrupamento sugerido pela leitura inicial do gráfico, mas
sustentado agora por múltiplos critérios que nem sempre concordaram entre si.

## Etapa 2 — A sensibilidade a preço varia por grupo, ou é única?

Com o agrupamento de nível fechado, a pergunta muda de figura: dentro dessa estrutura, permitir que a
sensibilidade a preço varie por grupo melhora alguma coisa? Um teste conjunto de significância —
testando todos os termos de variação simultaneamente, em vez de olhar cada um isoladamente — mostrou
que, tomados em conjunto, esses termos carregam sinal estatístico real dentro do treino. Isso é mais
informação do que uma leitura anterior, baseada só em contar quantos coeficientes individuais passam
do limiar usual de significância, deixava transparecer.

Ainda assim, o critério de simplicidade prefere o modelo sem essa variação, e o erro fora da amostra
piora ao permiti-la. Uma reamostragem pareada comparando o erro de previsão dos dois modelos produziu
um intervalo de confiança para a diferença que contém zero e é bem largo — sem evidência de que a
variação melhore (ou piore) a previsão fora da amostra de forma distinguível do ruído. Esse é um caso
real de sinal que existe no ajuste, mas não se traduz em ganho de generalização: exatamente a
situação em que decidir só por significância estatística, sem olhar penalidade de complexidade e
desempenho fora da amostra, levaria à conclusão errada.

Isolando só as observações de Fim de Semana, um coeficiente de preço ajustado exclusivamente sobre
elas não é distinguível de zero, e a correlação entre preço e volume nesse subconjunto é praticamente
nula — consistente com um sinal de correlação invertido já notado isoladamente em um desses dois dias
em investigações anteriores. A diferença entre essa sensibilidade isolada e a sensibilidade única
compartilhada fica no limite da significância, não conclusiva sozinha, mas apontando na mesma direção
de tudo o mais.

**Decisão da Etapa 2**: sensibilidade a preço única para todos os grupos — decidida pelo critério de
simplicidade, confirmada pela reamostragem pareada do erro de previsão, e pela ausência de
sensibilidade própria identificável no Fim de Semana.

## Etapa 3 — O modelo final

Com o agrupamento e a sensibilidade a preço decididos, o ajuste final troca o método que minimiza
erro quadrático por um que reduz automaticamente o peso de resíduos grandes, proporcional ao seu
próprio tamanho, sem descartar nenhum dia do histórico — o cuidado que o próprio desafio pede ao
alertar sobre demandas fora do padrão, levado a sério numa amostra de apenas 76 dias.

Dentro da família de métodos que fazem esse tipo de reponderação automática, existem variantes
diferentes. Uma comparação por reamostragem entre a variante adotada e três alternativas — incluindo
uma baseada em mediana — mostrou que todas convergem para valores e intervalos de confiança que se
sobrepõem quase por completo: a escolha da variante específica não está decidindo o número final.

Um intervalo de confiança por reamostragem foi calculado para todos os coeficientes do modelo final,
não só a sensibilidade a preço — os grupos com menos dado (Sexta e, principalmente, Fim de Semana)
têm intervalos proporcionalmente largos, e essa incerteza precisa acompanhar qualquer decisão que use
esses números como se fossem exatos.

A última decisão em aberto — usar o coeficiente da regressão conjunta para o Fim de Semana, ou uma
estatística de locação separada mais simples — foi resolvida por validação cruzada dentro das
próprias observações de Fim de Semana: para cada dia retirado, comparar o erro de reajustar a
regressão sem aquele dia contra o erro de usar a mediana dos dias restantes. Usando a média desses
erros, a estatística separada pareceu discretamente melhor — mas essa média foi inteiramente
dominada por um único dia com erro extremo sob a regressão, o mesmo tipo de distorção que motivou
trocar o método de ajuste original pela família robusta em primeiro lugar. Usando uma mediana desses
mesmos erros — um resumo mais resistente a um único caso isolado, coerente com o resto desta análise
— a regressão conjunta se mostrou claramente melhor. Essa reversão entre média e mediana não é uma
inconsistência a esconder: é o mesmo argumento usado para adotar regressão robusta em vez de mínimos
quadrados, aplicado agora à própria validação. A decisão final mantém o Fim de Semana dentro do mesmo
ajuste conjunto, em vez de desacoplá-lo — removê-lo do ajuste desloca a sensibilidade a preço
compartilhada em cerca de 7%, uma contribuição real, ainda que modesta, e deixa os demais grupos
praticamente intactos.

Por fim, a estrutura e os coeficientes finais foram cotejados contra uma implementação de referência
construída de forma independente, por um caminho analítico totalmente diferente — uma investigação
mais ampla, que partiu de hipóteses de calendário mais largas (padrões por semana do mês, quinzena,
mês) antes de convergir para o dia da semana, e que investigou separadamente como tratar valores
extremos antes de chegar à mesma família de métodos robustos. Os dois caminhos, percorridos de forma
independente, convergiram para exatamente a mesma partição de dias e para coeficientes idênticos —
uma validação mais forte do que qualquer um dos dois caminhos sozinho poderia oferecer.

## O modelo escolhido para a curva de elasticidade

**Quatro grupos de dia — Segunda isolada; Terça, Quarta e Quinta juntas; Sexta isolada; Fim de
Semana à parte — cada um com seu próprio patamar de venda, todos compartilhando uma única
sensibilidade a preço, ajustados por regressão robusta sobre o volume observado, sem nenhum corte ou
tratamento prévio de valores extremos, e com o Fim de Semana mantido dentro do mesmo ajuste
conjunto.**

Cada peça dessa escolha passou por um teste que poderia, em princípio, tê-la derrubado:

- **Por que agrupar por dia da semana, e não tratar todos os dias como um bloco só**: o candidato sem
  nenhuma diferenciação errou mais que o dobro de qualquer alternativa testada.
- **Por que manter o Fim de Semana no treino, e não excluí-lo**: testado formalmente contra excluí-lo
  por completo — o erro de previsão nos dias úteis não muda de forma distinguível do ruído, e mantê-lo
  fornece a única informação disponível sobre o nível de venda desse período.
- **Por que Segunda continua separada**: esta é a decisão mais frágil da análise — o critério de
  simplicidade ficou empatado, e duas ferramentas independentes de comparação par-a-par não
  confirmaram a diferença isoladamente; só uma validação cruzada repetida, mostrando um ganho
  preditivo estável e reproduzível, decidiu a favor de mantê-la separada.
- **Por que o Fim de Semana entra como grupo próprio, mas sem sensibilidade a preço própria**: seu
  patamar de venda se mostrou estatisticamente distinto com folga; sua sensibilidade a preço,
  isolada, não se distingue de zero.
- **Por que uma única sensibilidade a preço, e não uma por grupo**: permitir variação mostrou sinal
  estatístico dentro do treino, mas nenhum ganho de previsão fora da amostra distinguível do ruído — e
  o critério de simplicidade prefere o modelo único.
- **Por que regressão robusta, e não o ajuste que minimiza erro quadrático simples**: o próprio
  desafio alerta que alguns dias podem gerar demandas fora do padrão; a variante específica escolhida
  dentro da família robusta não muda o resultado de forma relevante frente às alternativas testadas.
- **Por que o Fim de Semana permanece no ajuste conjunto, e não numa estatística separada**: uma
  validação cruzada dentro das próprias observações de Fim de Semana, resumida de forma resistente a
  um único caso extremo, favorece claramente mantê-lo dentro do ajuste conjunto.

## O que ainda fica em aberto

- **A separação de Segunda** é a decisão mais frágil de toda a análise: apoiada em evidência
  preditiva (validação cruzada), não em significância estatística isolada, que não a confirma.
- **Amostra pequena em todo lugar que importa**: 76 dias de treino, com grupos de apenas 11 a 14
  observações — o suficiente para produzir empates de critério e discordância entre ferramentas de
  comparação, como visto na decisão sobre Segunda.
- **Erro de previsão ainda alto** fora da amostra mesmo no modelo final — deve ser incorporado como
  incerteza real na etapa de precificação, não tratado como um número exato.
- **O Fim de Semana** não sustenta sensibilidade a preço própria, e sua previsão individual segue
  incerta mesmo com o melhor método disponível — qualquer decisão de precificação para esse período
  precisa carregar essa incerteza de forma explícita.
- **Um holdout único de dias de teste provou-se pouco confiável mais de uma vez** nesta análise — um
  candidato de agrupamento teve o melhor erro isolado de todo o torneio e, ao mesmo tempo, o pior
  critério de simplicidade, por uma margem enorme. Decisões estruturais não deveriam se apoiar nesse
  tipo de comparação isolada sozinha.
