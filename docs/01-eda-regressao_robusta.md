# A Curva de Demanda por Regressão Robusta: uma Segunda Rota até o Mesmo Destino

## O desafio

Existe um produto vendido diariamente, cujo preço pode ser ajustado todo dia. A pergunta central é:
se o preço subir ou descer, quanto o volume vendido reage? Essa relação — a curva de demanda,
descrita pela forma `Volume = A · Preço⁻ᴮ` — é o insumo que qualquer decisão de precificação diária
precisa antes de poder otimizar margem sujeita a metas de venda.

O histórico disponível para responder essa pergunta é curto: 76 dias de treino e 10 dias de teste,
nunca usados para decidir nada, apenas para checar se o modelo acerta fora da amostra. O próprio
enunciado do desafio observa dois pontos que orientam toda a análise a seguir: primeiro, que dias da
semana diferentes vendem volumes diferentes, e que essa diferença pode mascarar a relação real entre
preço e volume se todos os dias forem tratados como um bloco único; segundo, que alguns preços ou
faixas de preço podem gerar demandas fora do padrão — dias que, se pesarem demais no cálculo,
distorcem a conclusão sobre o quanto o cliente realmente reage a preço.

Esses dois avisos definem as duas perguntas que a análise precisa responder, nessa ordem: **como
agrupar os dias** (para não misturar padrões de venda diferentes num único número) e **como tratar
os dias fora do padrão** (para não deixar um punhado de dias extremos decidir sozinho a
sensibilidade a preço de todo o produto). Este relatório é a história de como essas duas perguntas
foram respondidas, de forma independente e autocontida, sem herdar nenhuma resposta pronta de
nenhuma outra análise.

## Primeiro obstáculo: agrupar por impressão visual não basta

Olhar a distribuição de volume por dia da semana sugere, de cara, que os dias não são todos iguais:
a mediana de Segunda-feira se destaca acima de qualquer outro dia útil; Terça, Quarta e Quinta
ocupam uma faixa parecida entre si; Sexta cai bem abaixo desse grupo; e Sábado e Domingo, juntos, têm
tão poucas observações que qualquer leitura sobre eles precisa ser cautelosa.

Essa leitura é útil como ponto de partida, mas não como conclusão — o próximo passo trata essa
divisão como **hipótese a testar**, não como fato já estabelecido. A forma escolhida para testar foi
um torneio formal de candidatos: cruzar "como agrupar o nível de venda" com "como agrupar a
sensibilidade a preço" e comparar as combinações que sobram com sentido estatístico, usando três
critérios decididos antes de rodar qualquer candidato — erro de previsão fora da amostra (MAPE),
BIC (a nota de simplicidade, que penaliza parâmetros que os dados não sustentam) e o número de
coeficientes efetivamente significativos.

Cinco candidatos entraram no torneio: nenhuma diferenciação por dia; um grupo por dia da semana, com
uma única sensibilidade a preço para todos; o mesmo agrupamento por dia, mas com sensibilidade
própria por dia; o agrupamento sugerido pela leitura visual, com sensibilidade única; e esse mesmo
agrupamento, mas com sensibilidade própria por grupo.

O candidato sem diferenciação nenhuma por dia errou mais que o dobro de qualquer outro — a primeira
confirmação de que ignorar o dia da semana descarta a maior parte da informação disponível. Entre os
quatro restantes, o candidato com uma sensibilidade a preço própria para cada dia (ou para cada
grupo) sempre piorou o erro fora da amostra e deixou a maioria dos seus parâmetros extras sem
significância estatística — sinal de que os dados sustentam níveis de venda diferentes por dia, mas
não sensibilidades a preço diferentes. E, entre os dois candidatos de sensibilidade única, o que
tinha o menor erro isolado fora da amostra não foi o escolhido: o BIC penalizou seus parâmetros
extras com força suficiente para colocá-lo atrás do agrupamento por grupos mais largos, cuja margem
de erro era praticamente igual. Com apenas 76 observações, o custo de cada parâmetro adicional
precisa ser levado a sério — e o BIC, diferente de outras métricas mais permissivas, é o critério que
faz exatamente isso.

O agrupamento vencedor — Segunda isolada, Terça/Quarta/Quinta juntas, Sexta isolada, Fim de Semana à
parte, todos compartilhando a mesma sensibilidade a preço — passou ainda por duas checagens
adicionais, isolando subconjuntos de dias com mais poder estatístico: confirmou-se que Quarta e
Quinta não são estatisticamente diferentes de Terça (a junção dos três não é conveniência, é o que
os dados sustentam quando testados diretamente), e que dar ao Fim de Semana um patamar de venda
próprio — sem sensibilidade a preço própria, por falta de dado suficiente para isso — reduz o BIC de
forma muito mais nítida do que juntá-lo à Sexta.

## Segundo obstáculo: o próprio método de ajuste pode estar distorcendo a resposta

Com o agrupamento decidido, a segunda pergunta do desafio entra em cena: dias fora do padrão têm peso
desproporcional num ajuste que minimiza erro quadrático — que é exatamente o que o método de ajuste
usado até aqui faz. A regressão robusta resolve isso trocando esse ajuste por um que reduz
automaticamente o peso de observações extremas, na proporção do próprio tamanho do resíduo, sem
descartar nenhum dia do histórico — um cuidado que pesa mais ainda com uma amostra de apenas 76
dias, onde cada dia descartado é dado que não volta.

Reajustar os cinco mesmos candidatos do torneio sob esse método (a norma de Huber, a mais simples e
estudada entre as opções robustas) reproduz a mesma hierarquia já vista: o candidato sem
diferenciação por dia continua errando mais que o dobro de qualquer outro, e os quatro candidatos
restantes ficam tecnicamente empatados em erro fora da amostra — a diferença entre eles cabe dentro
de menos de um ponto percentual. Esse método, porém, não fornece diretamente a mesma nota de
simplicidade usada na primeira etapa; o desempate entre os candidatos empatados precisou recorrer
diretamente à contagem de parâmetros, como substituto mais fraco. Mesmo assim, aponta na mesma
direção: o agrupamento por grupos mais largos, com sensibilidade única, continua sendo o mais
defensável, agora sob o método mais adequado à qualidade real dos dados disponíveis.

## Terceiro obstáculo: a escolha de uma variante específica poderia estar decidindo o resultado

Dentro da família de métodos que reduzem o peso de pontos extremos automaticamente, existem
variantes diferentes — algumas mais agressivas em descontar dias fora do padrão do que outras. Antes
de fechar a escolha, valia checar se a variante específica adotada estava, ela mesma, decidindo o
valor final da sensibilidade a preço, ou se era só um detalhe de implementação sem consequência
prática.

A comparação, feita via reamostragem repetida (bootstrap) do agrupamento vencedor sob quatro
variantes diferentes — a adotada e três alternativas, incluindo uma baseada em mediana em vez de
média —, mostrou que todas convergem para valores muito próximos entre si, com intervalos de
confiança que se sobrepõem quase por completo e uma variabilidade relativa semelhante entre as
quatro. Nem mesmo a variante de mediana, que teoricamente tolera a maior proporção de dados
extremos, se destacou como mais estável que as demais nesta amostra. Essa convergência é evidência
de que o ganho de trocar o método de ajuste original pela família de métodos robustos vem de reduzir
o peso de pontos extremos sem descartar dado nenhum — não da forma específica escolhida para fazer
esse desconto. A variante mais simples e mais estudada da família foi mantida por ser o padrão mais
direto dentro do conjunto testado, não por ter vencido uma disputa empírica que a amostra disponível
não tinha poder estatístico suficiente para decidir de forma definitiva.

## Uma checagem cruzada com um caminho analítico independente

Antes de fechar a conclusão, ela foi confrontada com uma segunda investigação sobre os mesmos dados,
conduzida por um caminho totalmente diferente: em vez de partir direto para um torneio compacto
decidido por BIC, essa outra investigação testou primeiro hipóteses de calendário mais amplas —
padrões por semana do mês, por quinzena, por mês — descartando cada uma antes de convergir,
separadamente, para o próprio dia da semana como o agrupamento relevante. Ela também investigou, de
forma extensa, se o próprio tratamento de dias fora do padrão (nesse caso, um corte fixo de valores
acima de um teto por dia da semana, decidido antes de qualquer modelo) estava mascarando ou
distorcendo a sensibilidade real a preço — concluindo, por um caminho de evidência diferente do
usado aqui, que sim, e chegando também à família de métodos robustos como alternativa.

Dois caminhos analíticos que não compartilham a mesma sequência de decisões, partindo de hipóteses
iniciais diferentes e aplicando critérios de comparação distintos ao longo do processo, convergiram
para exatamente o mesmo agrupamento de dias e para o mesmo valor de sensibilidade a preço, coeficiente
por coeficiente. Essa coincidência não é uma verificação isolada — é evidência mais forte do que
qualquer um dos dois caminhos, sozinho, conseguiria oferecer.

## O modelo escolhido para a curva de elasticidade

**Quatro grupos de dia — Segunda isolada; Terça, Quarta e Quinta juntas; Sexta isolada; Fim de
Semana à parte — cada um com seu próprio patamar de venda, todos compartilhando uma única
sensibilidade a preço, ajustados por regressão robusta (norma de Huber) sobre o volume observado,
sem nenhum corte ou tratamento prévio de valores extremos.**

Cada peça dessa escolha tem uma razão específica, e nenhuma foi aceita sem antes eliminar pelo menos
uma alternativa concreta:

- **Por que agrupar por dia da semana, e não tratar todos os dias como um bloco só**: o candidato sem
  nenhuma diferenciação errou mais que o dobro de qualquer alternativa testada — a diferença entre
  dias da semana carrega a maior parte da informação disponível sobre o volume.
- **Por que quatro grupos mais largos, e não um grupo por dia**: o BIC penaliza os parâmetros extras
  de um grupo por dia com força suficiente para superar sua vantagem marginal de erro fora da
  amostra — vantagem pequena demais, frente ao tamanho da amostra, para justificar a complexidade
  adicional.
- **Por que uma única sensibilidade a preço, e não uma por grupo**: permitir que a sensibilidade
  variasse por grupo piorou o erro fora da amostra em todos os testes e deixou a maioria dos
  parâmetros extras sem significância estatística — os dados sustentam níveis de venda diferentes,
  não reações a preço diferentes.
- **Por que o Fim de Semana entra como grupo próprio, mas sem sensibilidade a preço própria**: o
  patamar de venda do Fim de Semana se mostrou estatisticamente distinto com folga, mesmo com poucas
  observações — um patamar é mais fácil de confirmar com pouco dado do que uma sensibilidade a preço,
  que exigiria muito mais observações do que as disponíveis para esse grupo.
- **Por que regressão robusta, e não o ajuste que minimiza erro quadrático simples**: o próprio
  desafio alerta que alguns dias podem gerar demandas fora do padrão; um ajuste que dá peso total a
  todo ponto é vulnerável a exatamente esse tipo de dia, e reajustar o agrupamento vencedor sob esse
  método reproduziu a mesma conclusão, reduzindo o risco de que ela dependesse de um único método
  de ajuste.
- **Por que a variante específica de Huber, entre as opções robustas**: a comparação por
  reamostragem mostrou que a escolha entre variantes robustas não muda a sensibilidade estimada de
  forma relevante — a variante mais simples e mais estudada foi mantida por não haver ganho
  concreto em trocar por outra.
- **Por que manter todos os dias no treino, mesmo os mais extremos**: a amostra de 76 dias já é
  pequena; descartar qualquer dia reduz ainda mais o quanto o modelo tem para aprender, e a própria
  regressão robusta já cumpre o papel de reduzir a influência de pontos extremos sem exigir esse
  descarte.

## O que ainda fica em aberto

A escolha final não elimina algumas limitações, registradas para constar:

- O candidato descartado por parcimônia (um grupo por dia, sensibilidade única) teve, isoladamente,
  o menor erro fora da amostra do torneio original — por uma margem pequena. Com uma amostra maior,
  essa disputa poderia terminar de outro jeito.
- As diferenças de erro fora da amostra entre os candidatos não triviais, sob o método robusto
  final, são da mesma ordem de grandeza do ruído esperado com apenas 10 dias de teste.
- O Fim de Semana não recebe sensibilidade a preço própria em nenhum candidato testado, por falta de
  dado — uma decisão sustentada estatisticamente, mas que continua sendo uma lacuna de informação, não
  uma certeza.
- Sem uma nota de simplicidade diretamente comparável disponível para o método robusto, o desempate
  entre candidatos próximos em erro fora da amostra, nessa etapa, apoiou-se apenas na contagem de
  parâmetros — um critério mais fraco do que o usado na primeira etapa da análise.
