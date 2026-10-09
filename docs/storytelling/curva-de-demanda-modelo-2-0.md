# Como chegamos à curva de demanda: a história do modelo 2.0

> **Para quem é este documento.** Para quem precisa entender *por que* o modelo de demanda tem a forma que tem, sem ler o código. Cada capítulo parte de um gráfico ou de uma tabela, mostra o que se enxergou ali, que hipótese nasceu disso, como ela foi testada e o que se decidiu. Todos os números vêm dos notebooks `1.0-minerva-eda-preparacao` e `2.0-minerva-curva-demanda-validacao` e das tabelas em `reports/tables/`. O capítulo 15 usa também o notebook `2.1-minerva-curva-demanda-metodo-livro`, para registrar a decisão do grupo pelo método analítico.

---

## Capítulo 0. A história em um minuto

1. O preço praticamente **não muda** de um dia da semana para outro. O volume, sim, muda muito. Por isso a pergunta deixa de ser “qual preço?” e passa a ser “**onde o volume varia?**”.
2. Quatro recortes de calendário foram testados (mês, quinzena, semana do mês e dia da semana). Só o **dia da semana** muda o nível de vendas de forma clara e persistente.
3. O boxplot do volume por dia mostra três patamares: segunda a quinta (cerca de 20 a 30 kg), sexta (cerca de 7 kg) e fim de semana (1 a 2 kg). Dentro do primeiro patamar, **terça e quarta são praticamente iguais**.
4. Os testes estatísticos confirmam a leitura visual: terça = quarta = quinta (p de Holm = 1,00), sexta é bem menor e o fim de semana tem pouca amostra para qualquer conclusão fina.
5. A **segunda-feira** é o caso difícil: o teste diz que ela vende 1,40 vez mais que terça a quinta, mas separá-la **não melhora a previsão** fora da amostra. A decisão foi tomada pela validação temporal, não pelo p-valor.
6. O modelo final é uma **curva de potência** com elasticidade única, três níveis de calendário e quatro parâmetros. No holdout oficial (dez dias que o modelo nunca viu) o erro ponderado (WMAPE) foi de 36,28%, e o erro de volume semanal, de 16,77%.
7. O grupo decidiu seguir este **método analítico** (notebook 2.0) e não o método do livro (notebook 2.1). Os dois chegam à **mesma curva**, com coeficientes idênticos; a diferença está no caminho e na justificativa (capítulo 15).

---

## Capítulo 1. O ponto de partida: uma pergunta e um cofre

**A pergunta.** Dado um preço candidato e o dia da semana, quantos quilos esperamos vender? A resposta alimenta o otimizador (notebook 3.0), que escolhe preços diários respeitando metas semanais de volume e limites de variação entre dias consecutivos.

**Os dados.** A planilha tem 86 observações diárias de um único produto, com volume (kg), receita e custo. O preço por kg foi reconstruído como receita dividida por volume. Não há valores ausentes, datas duplicadas nem valores não positivos.

**O cofre.** Antes de qualquer gráfico, a base foi separada por data:

| Conjunto | Período | Observações | Uso |
|---|---|---:|---|
| Desenvolvimento | 01/08/2025 a 31/10/2025 | 76 | Exploração, hipóteses, seleção e ajuste |
| Holdout oficial | 03/11/2025 a 14/11/2025 | 10 | Aberto **uma única vez**, no fim |

Essa ordem importa para a credibilidade da história: **nenhuma hipótese deste documento foi formulada olhando o holdout**. Ele só foi aberto depois de a fórmula, os coeficientes e os cenários de incerteza serem congelados em arquivo com hash.

**Duas trilhas, uma escolha.** O projeto tem duas formas de chegar à curva: o método analítico (notebook 2.0), contado aqui, e o método do livro de Phillips (notebook 2.1). O grupo decidiu seguir o analítico. O capítulo 15 compara os dois.

---

## Capítulo 2. A primeira pista: o preço quase não varia

**O que olhamos.** Os gráficos de barras do notebook 1.0 mostram, para cada recorte, a média de volume e a média de preço lado a lado (figura abaixo, painéis da direita).

![Volume e preço por dia da semana](../../../reports/figures/01_sazonalidade_dia_semana.png)

**O que vimos.** As barras de preço têm praticamente a mesma altura em todos os dias:

| Dia | Preço médio (R$/kg) |
|---|---:|
| Segunda | 1.278,28 |
| Terça | 1.277,31 |
| Quarta | 1.275,01 |
| Quinta | 1.275,24 |
| Sexta | 1.274,34 |
| Sábado | 1.256,38 |
| Domingo | 1.280,66 |

O preço varia de R$ 1.188,86 a R$ 1.365,49/kg, mas o desvio-padrão é só **3,1% da média**. O volume, no mesmo período, tem desvio-padrão de **89,6% da média**, indo de 0,59 a 100 kg.

**Hipótese.** Se o preço é quase o mesmo em todos os dias e o volume muda muito, a diferença de vendas entre dias não pode ser explicada pelo preço. Há uma **estrutura de demanda ligada ao tempo** que precisa ser descrita.

**Cuidado que a história pede.** “O preço varia pouco” não é o mesmo que “o preço não importa”. Dentro de cada dia útil, a correlação entre preço e volume é negativa (Pearson de -0,63 a -0,87). A faixa estreita de preços, porém, significa que a elasticidade é estimada a partir de variações pequenas, o que ajuda a explicar a incerteza que aparecerá no capítulo 9.

> **Decisão do capítulo.** Concentrar a investigação na **variação temporal do volume** e, em paralelo, manter o preço como variável central da curva.

---

## Capítulo 3. Onde o volume varia? Quatro hipóteses de calendário

**O que fizemos.** Para cada recorte de tempo, geramos boxplots (dispersão) e barras (média) de volume e de preço: mês, quinzena, semana do mês e dia da semana. Os gráficos formam hipóteses, não escolhem variáveis.

**O que vimos nos três primeiros recortes.** Há diferenças visuais de volume, mas elas **andam junto com o preço**:

| Recorte | Volume médio | Preço médio | Leitura |
|---|---|---|---|
| Agosto / Setembro / Outubro | 19,72 / 17,15 / 25,83 kg | R$ 1.263,06 / 1.295,95 / 1.266,17 | Setembro vendeu menos com o preço mais alto; Outubro tem o ponto de 100 kg e a maior dispersão |
| 1ª quinzena | 25,94 kg | R$ 1.258,76 | Vendeu mais **e** com preço menor |
| 2ª quinzena | 16,56 kg | R$ 1.290,45 | Vendeu menos **e** com preço maior |
| Semanas 2 e 3 do mês | 28,12 e 26,32 kg | R$ 1.252,85 e 1.262,24 | Vendeu mais com preço menor |
| Semanas 4 e 5 do mês | 13,50 e 12,14 kg | R$ 1.304,85 e 1.302,90 | Vendeu menos com preço maior |

Esses padrões **não podem ser lidos como sazonalidade pura**: um grupo pode ter vendido mais simplesmente por ter recebido preço menor. Já o dia da semana separa níveis de volume de modo persistente **sem** diferença equivalente de preço (capítulo 2).

![Mês: boxplots e médias de volume e preço](../../../reports/figures/01_sazonalidade_mes.png)

![Quinzena: boxplots e médias de volume e preço](../../../reports/figures/01_sazonalidade_quinzena.png)

![Semana do mês: boxplots e médias de volume e preço](../../../reports/figures/01_sazonalidade_semana_mes.png)

**Como testamos.** Cada recorte foi acrescentado a um modelo-base que já contém o preço, `ln(volume) ~ ln(preço)`. O teste F pergunta se o calendário acrescenta ajuste além do preço; o BIC penaliza o número de parâmetros (quanto menor, melhor).

| Hipótese | Grupos | Menor grupo (n) | p-valor do teste F | ΔBIC | Leitura |
|---|---:|---:|---:|---:|---|
| Mês | 3 | 23 | 0,698 | +7,90 | Não melhora o baseline |
| Quinzena | 2 | 37 | 0,579 | +4,01 | Não melhora o baseline |
| Semana do mês | 5 | 7 | 0,852 | +15,87 | Não melhora o baseline |
| **Dia da semana** | 7 | 5 | **1,1 × 10⁻²³** | **-105,74** | Ganho de ajuste muito forte |

> **Decisão do capítulo.** Dia da semana é a única hipótese de calendário que sobrevive ao controle pelo preço. Mês, quinzena e semana do mês ficam documentados, mas fora do modelo. Ainda não sabemos **como agrupar** os sete dias.

---

## Capítulo 4. Lendo o boxplot: quem se parece com quem?

**O que olhamos.** O boxplot do volume por dia da semana (painel superior esquerdo da mesma figura do capítulo 2). A caixa vai do 1º ao 3º quartil, a linha central é a mediana e o tamanho da caixa mostra a dispersão.

| Dia | n | Mín. | Q1 | Mediana | Q3 | Máx. | Média | Amplitude interquartil |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Segunda | 13 | 12,19 | 25,10 | 31,31 | 36,67 | 69,35 | 32,58 | 11,57 |
| Terça | 13 | 7,40 | 16,44 | 22,01 | 23,21 | 58,39 | 24,45 | 6,77 |
| Quarta | 13 | 11,03 | 16,17 | 19,14 | 28,48 | 100,00 | 28,25 | 12,31 |
| Quinta | 13 | 2,82 | 15,16 | 27,36 | 35,40 | 67,68 | 28,64 | 20,24 |
| Sexta | 14 | 1,84 | 4,25 | 6,83 | 8,10 | 17,94 | 7,72 | 3,85 |
| Sábado | 5 | 0,59 | 2,00 | 2,46 | 2,55 | 3,68 | 2,26 | 0,55 |
| Domingo | 5 | 0,59 | 0,59 | 0,61 | 1,34 | 2,08 | 1,04 | 0,75 |

Volumes em kg. A tabela reproduz os números por trás das caixas do gráfico.

**O que vimos, em quatro leituras.**

1. **Três patamares.** Segunda a quinta têm medianas entre 19 e 31 kg. A sexta cai para uma mediana de 6,83 kg e as caixas quase não encostam nas dos dias anteriores. O fim de semana fica entre 0,6 e 2,5 kg.
2. **Terça e quarta são quase gêmeas.** O 1º quartil é praticamente igual (16,44 e 16,17 kg) e as medianas (22,01 e 19,14 kg) estão a menos de 3 kg uma da outra, dentro da dispersão de ambas. A média da quarta (28,25 kg) é puxada para cima por um único dia de 100 kg, o que mostra por que olhamos a mediana.
3. **A quinta se sobrepõe às duas.** Sua caixa é a mais larga (15,16 a 35,40 kg) e cobre tanto a de terça quanto a de quarta.
4. **A segunda está um degrau acima.** Seu 1º quartil (25,10 kg) já supera o 3º quartil da terça (23,21 kg). Ela é mais parecida com a quinta do que com terça e quarta.

**Hipóteses que nasceram do boxplot** (formuladas antes de qualquer teste):

| # | Hipótese | Origem visual |
|---|---|---|
| H1 | Terça, quarta e quinta têm o mesmo nível de demanda | Caixas sobrepostas, medianas próximas |
| H2 | A segunda poderia ser agrupada a elas | Mesma ordem de grandeza e sobreposição com a quinta |
| H3 | A sexta tem nível próprio, bem menor | Caixa isolada, mediana de 6,83 kg |
| H4 | Sábado e domingo compartilham um nível mínimo | Ambos entre 0,6 e 2,5 kg |

O gráfico, porém, **não dá p-valor**. Olho treinado enxerga padrão, mas também enxerga padrão onde há só acaso. Daí o próximo passo.

---

## Capítulo 5. Do olho ao p-valor: testando as hipóteses do boxplot

**Como testamos.** Ajustamos uma curva de potência com **sete níveis de dia da semana** e preço (`ln(volume) ~ ln(preço) + dia`) e comparamos pares e grupos de dias com testes de Wald. Quatro cuidados:

- os contrastes foram **definidos antes** de ver o resultado (um por hipótese H1 a H4);
- usamos covariância robusta **HC3**, pouco sensível a heterocedasticidade e a pontos de alta alavancagem em amostras pequenas;
- aplicamos a correção de **Holm**, porque vários testes feitos juntos aumentam a chance de falso positivo;
- lemos a “razão de volume” como: *a quantas vezes o volume do primeiro dia equivale ao do segundo, ao mesmo preço*.

| Contraste | Razão de volume | IC 95% | p bruto | p de Holm | Diferença detectada? |
|---|---:|---|---:|---:|---|
| Terça vs. quarta | 0,963 | 0,666 a 1,392 | 0,842 | 1,000 | Não |
| Terça vs. quinta | 1,014 | 0,690 a 1,490 | 0,944 | 1,000 | Não |
| Terça = quarta = quinta (conjunto) | – | – | 0,970 | 1,000 | Não |
| Segunda vs. média de terça a quinta | 1,401 | 1,146 a 1,715 | 0,0010 | 0,0062 | **Sim** |
| Segunda = terça = quarta = quinta (conjunto) | – | – | 0,0089 | 0,0443 | **Sim** |
| Sexta vs. média de segunda a quinta | 0,262 | 0,195 a 0,353 | < 10⁻¹⁷ | < 10⁻¹⁷ | **Sim** |
| Sábado vs. domingo | 1,708 | 0,508 a 5,748 | 0,387 | 1,000 | Não |

**O que os testes dizem, hipótese por hipótese.**

- **H1 confirmada.** Terça, quarta e quinta não se distinguem (p de Holm = 1,000 em todos os testes). É aqui que a leitura visual “terça e quarta são parecidas” ganha respaldo estatístico.
- **H3 confirmada com folga.** Sexta vende cerca de **26%** do que se vende de segunda a quinta (razão 0,262), e o intervalo de confiança está longe de 1.
- **H2 não se confirma pelo teste.** A segunda vende **1,40 vez** mais que terça a quinta, e o teste conjunto que inclui a segunda é significativo (p de Holm = 0,044). O que quebra a igualdade do bloco segunda a quinta é a segunda-feira. Esse é o assunto do próximo capítulo.
- **H4 fica em aberto.** Sábado e domingo não diferem, mas o intervalo da razão vai de 0,51 a 5,75. Com cinco observações em cada um, o teste não tem poder para afirmar nada. Eles serão agrupados por **falta de dados**, não por evidência de igualdade.

> **Atenção à leitura do p-valor.** Um p-valor alto **não prova que dois dias são iguais**; prova apenas que a amostra não os distingue. O intervalo da razão terça/quarta (0,67 a 1,39) ainda admite diferenças de 30% a 40%. Por isso o agrupamento nunca foi decidido só pelo p-valor: ele também precisou de semelhança visual, parcimônia e, no fim, de desempenho de previsão.

> **Decisão do capítulo.** Terça, quarta e quinta formam um bloco. Sexta tem nível próprio. Sábado e domingo formam um bloco por falta de dados. A segunda-feira **fica de fora do bloco pelo teste** e vira um desafiante a ser julgado na validação.

---

## Capítulo 6. O caso da segunda-feira

A segunda-feira é o ponto em que três evidências discordam:

| Evidência | O que sugere |
|---|---|
| Boxplot | Segunda parece da mesma família de terça a quinta, com sobreposição clara com a quinta |
| Teste de Wald | Segunda é 1,40 vez maior que terça a quinta (p de Holm = 0,0062) |
| Parcimônia | Cada nível extra de calendário custa um parâmetro estimado com apenas 13 segundas |

Em vez de escolher uma evidência, **duas partições foram postas para competir** sob o mesmo protocolo de validação temporal:

- **P3:** segunda a quinta juntas, sexta, fim de semana (4 parâmetros);
- **P4:** segunda separada, terça a quinta juntas, sexta, fim de semana (5 parâmetros).

| Grupo | Obs. na validação | WMAPE P3 | WMAPE P4 | Viés P3 | Viés P4 |
|---|---:|---:|---:|---:|---:|
| Segunda | 3 | 33,59% | 36,01% | -21,54% | +4,14% |
| Terça a quinta | 10 | 34,66% | 38,01% | -22,51% | -29,48% |
| Sexta | 4 | 33,55% | 32,57% | -21,21% | -20,35% |
| Fim de semana | 4 | 147,81% | 152,63% | – | – |
| **Total (21 dias)** | 21 | **35,29%** | **38,16%** | -21,06% | -20,40% |

**Leitura.** Separar a segunda **corrige o viés da própria segunda** (de -21,5% para +4,1%) e reduz seu RMSE (de 18,36 para 15,14 kg). Em troca, **piora o erro dos dias de terça a quinta** (WMAPE de 34,66% para 38,01%), piora o WMAPE total (de 35,29% para 38,16%) e aumenta o erro absoluto das somas semanais (de 159,6 para 168,6 kg). Como o otimizador trabalha com **metas semanais**, o erro semanal pesa mais que o erro diário isolado.

Há ainda um aviso de honestidade: a segunda tem apenas **3 observações** na janela de validação. O resultado é um sinal, não uma sentença.

> **Decisão do capítulo.** A segunda-feira **foi agrupada** com terça a quinta no modelo final (P3). Trata-se de um **agrupamento preditivo**, e não de uma afirmação de que os dias são iguais. O modelo sabe que a segunda tende a vender mais; ele só não ganha precisão ao estimar um parâmetro separado para ela. Se o negócio passar a exigir precisão específica na segunda, P4 está documentado como alternativa.

---

## Capítulo 7. A escada de modelos: cada degrau paga seu custo?

Com as partições definidas, o calendário foi construído degrau a degrau. Em todos eles a inclinação do preço é **única** (um coeficiente só), e muda apenas o nível de cada contexto. Os baselines pedidos pelo enunciado entram como ponto de partida.

**Protocolo de validação** (idêntico para todos os candidatos):

- os primeiros 55 dias treinam o modelo e os **21 dias seguintes** (09/10 a 31/10) são previstos **um a um**, sempre re-treinando só com o passado e sem embaralhar;
- métrica principal: **WMAPE**, o erro absoluto total dividido pelo volume real total, em kg. O MAPE comum foi descartado como critério porque volumes próximos de zero (fim de semana) o inflam artificialmente (91,7% no campeão);
- modelo com inclinação de preço não negativa ou com previsão não positiva é **inválido**;
- entre candidatos a até 1 ponto percentual do melhor, vence o mais simples.

| Degrau | Modelo | Parâmetros | WMAPE | MAE (kg) | RMSE (kg) | Teste do bloco acrescentado (p de Holm) |
|---|---|---:|---:|---:|---:|---|
| Enunciado | Linear: `volume ~ preço` | 2 | 73,04% | 18,31 | 24,73 | Inválido: previsão mínima de -2,54 kg |
| P0 | Potência só com preço | 2 | 78,00% | 19,55 | 26,38 | – |
| P1 | + fim de semana | 3 | 53,51% | 13,41 | 21,14 | < 5 × 10⁻¹⁸ |
| **P3** | **+ sexta** | **4** | **35,29%** | **8,84** | **15,39** | **< 5 × 10⁻¹⁸** |
| P4 | + segunda separada | 5 | 38,16% | 9,56 | 16,14 | 0,0018 |
| P2 | Sete dias | 8 | 39,41% | 9,88 | 16,62 | 1,000 |

![Ranking de calendário pela validação temporal (WMAPE)](../../../reports/figures/02_ranking_calendario.png)

**A moral do quadro.**

- O **preço sozinho prevê mal** (WMAPE de 78%): ele confirma o sinal negativo, mas não explica os níveis.
- **Fim de semana e sexta** pagam muito bem: juntos derrubam o WMAPE em mais de 42 pontos percentuais.
- A partir de P3, **mais detalhe piora a previsão**. P4 tem p-valor significativo e melhora marginalmente o BIC, mas perde em erro. P2, com oito parâmetros, não acrescenta nada (p = 1,000) e erra mais que P3.

Esse é o ponto em que a história separa duas perguntas que costumam ser confundidas: *“existe diferença estatística?”* (P4: sim) e *“usar essa diferença melhora a previsão?”* (P4: não).

---

## Capítulo 8. Forma da curva e tendência: dois desafiantes que perderam

Com o calendário de P3 fixado, duas outras decisões foram testadas pelo mesmo protocolo.

**Forma funcional.**

| Modelo | Parâmetros | WMAPE | MAE (kg) | RMSE (kg) | Previsão mínima | Válido? |
|---|---:|---:|---:|---:|---:|---|
| **Potência** `ln(volume) ~ ln(preço)` | 4 | **35,29%** | 8,84 | 15,39 | 0,62 kg | Sim |
| Exponencial `ln(volume) ~ preço` | 4 | 35,44% | 8,88 | 15,47 | 0,60 kg | Sim |
| Linear `volume ~ preço` | 4 | 55,02% | 13,79 | 19,08 | -24,80 kg | **Não** |

Potência e exponencial empataram na prática. A potência ficou por ter vantagem pequena no WMAPE e no erro semanal, e porque seu coeficiente de preço **é diretamente a elasticidade** (o quanto o volume cai, em percentual, para cada 1% de aumento de preço). A linear prevê volume negativo e foi rejeitada. A assimetria do volume (1,665) já sugeria trabalhar em logaritmo desde o EDA.

**Tendência no tempo.** O gráfico cronológico mostra preços e volumes se movendo juntos no fim da amostra, o que justificou o teste, mas não a inclusão. Adicionando o índice de tempo (T1):

| Modelo | WMAPE | RMSE (kg) | WMAPE semanal | p de Holm do bloco |
|---|---:|---:|---:|---:|
| **P3 (sem tendência)** | **35,29%** | 15,39 | **30,32%** | – |
| T1 (P3 + tendência) | 35,94% | **15,23** | 30,77% | 1,000 |

A tendência reduziu levemente o RMSE, mas piorou a métrica principal e o erro semanal. Em uma amostra de três meses, ela provavelmente absorveria o episódio de outubro e degradaria a previsão para datas futuras. Foi descartada.

> **Decisão do capítulo.** O modelo é uma **curva de potência, sem tendência**, com o calendário P3.

---

## Capítulo 9. O modelo final

Congelada a especificação, o modelo foi ajustado com os 76 dias de desenvolvimento.

```
ln(volume) = 91,5915 - 12,3647 × ln(preço) - 1,3394 × I(sexta) - 2,9670 × I(fim de semana)

volume previsto (kg) = exp(ln(volume)) × 1,1226      <- fator de smearing de Duan
```

| Termo | Coeficiente | IC 95% (HC3) | Como ler |
|---|---:|---|---|
| Constante | 91,5915 | 53,55 a 129,64 | Nível de segunda a quinta |
| ln(preço) | -12,3647 | -17,69 a -7,04 | **Elasticidade-preço**, única para todos os dias |
| Sexta | -1,3394 | -1,64 a -1,04 | A sexta vende exp(-1,3394) = **26,2%** do nível de segunda a quinta |
| Fim de semana | -2,9670 | -3,56 a -2,37 | O fim de semana vende exp(-2,9670) = **5,1%** do nível de segunda a quinta |

**Como ler a curva.** São **três curvas paralelas** (mesma inclinação, níveis diferentes). Cada contexto tem sua própria curva: segunda a quinta no topo, sexta a cerca de um quarto dela e o fim de semana a cerca de um vigésimo.

**Elasticidade.** Um aumento de 1% no preço está associado a uma queda de cerca de **11,6%** no volume (o coeficiente, -12,36, é a aproximação em escala logarítmica). O sinal é estável, mas a magnitude é alta e incerta, com intervalo de -17,7 a -7,0.

**O fator de smearing.** Prever em escala logarítmica e voltar para quilos com `exp()` subestima a média. O fator de Duan (1,1226), recalculado em cada janela da validação, corrige essa distorção sem supor que os erros são normais.

![Curvas centrais por contexto, dentro do suporte de preço](../../../reports/figures/02_curvas_suporte.png)

**Exemplo de uso** (cenário central, em kg por dia):

| Preço (R$/kg) | Segunda a quinta | Sexta | Fim de semana |
|---:|---:|---:|---:|
| 1.250 | 34,3 | 9,0 | 1,8 |
| 1.275 | 26,9 | 7,0 | 1,4 |
| 1.300 | 21,1 | 5,5 | 1,1 |

Subir o preço de R$ 1.250 para R$ 1.300 (4%) reduz o volume previsto em mais de um terço, de 34,3 para 21,1 kg em dia útil. É essa sensibilidade que o otimizador terá de equilibrar com a margem.

---

## Capítulo 10. Podemos confiar nesse modelo? Diagnósticos e robustez

Escolher o modelo não encerra o trabalho. Depois do congelamento, perguntamos onde ele pode estar nos enganando. Esses testes **não reabrem a seleção**: servem para dimensionar a incerteza.

| Pergunta | Verificação | Resultado | Consequência |
|---|---|---|---|
| A variância dos erros é constante? | Breusch-Pagan | p = 0,0175: **não é** | Usar erros-padrão robustos (HC3) |
| Os erros de um dia contaminam o seguinte? | Durbin-Watson e Ljung-Box | DW = 1,83; Ljung-Box (lag 5) p = 0,943 | Sem sinal forte de autocorrelação curta |
| Os erros são normais? | QQ-plot | Caudas pesadas | Intervalos que supõem normalidade seriam otimistas |
| Alguma observação domina o ajuste? | Cook e alavancagem | 5 pontos acima de 4/n (Cook) e 7 acima de 2p/n (alavancagem); o mais influente é 11/10 (0,59 kg ao menor preço do suporte) | Nenhum ponto foi removido |
| A elasticidade depende de um dia só? | Leave-one-out (76 reajustes) | De -14,10 a -11,20 | O sinal nunca inverte; a maior mudança é de 1,73 |
| E se os erros grandes pesarem menos? | Regressão robusta de Huber | -13,89 | Mesma ordem de grandeza |
| E se o fim de semana sair? | Ajuste só com dias úteis | -14,83 | Mesma ordem de grandeza |
| Preço e calendário se confundem? | VIF | Próximo de 1 | Sem colinearidade problemática |
| Quão estável é a elasticidade? | Bootstrap por blocos semanais (1.000 réplicas) | IC 95%: -15,98 a -6,71; mediana -12,34; nenhuma réplica não negativa | Sinal estável, magnitude incerta |

![Diagnósticos de resíduos](../../../reports/figures/02_diagnosticos_residuos.png)

![Influência das observações](../../../reports/figures/02_influencia.png)

**Moral.** A conclusão qualitativa (“preço maior, volume menor”) é robusta a todos os testes. A conclusão quantitativa (“-12% por 1%”) é **sensível**: dependendo de como se trata a amostra, ela varia de -11 a -15 e, pelo bootstrap, de -16 a -7.

---

## Capítulo 11. Incerteza e suporte: o que o otimizador recebe

O otimizador não deve receber apenas um número por dia. Por isso, a curva é entregue com **dois cuidados**.

**1. Três cenários de volume.** Calculados a partir da razão entre volume real e previsto nas 21 previsões da validação (quantis de 20% e 80%, para evitar extremos pouco estáveis):

| Cenário | Multiplicador sobre a previsão central |
|---|---:|
| Conservador | 0,641 |
| Central | 1,000 |
| Otimista | 1,498 |

A largura da faixa (de 0,64 a 1,50) é um aviso claro: o **nível** de volume é incerto, mesmo com o sinal da elasticidade bem estabelecido.

**2. Suporte de preço por contexto.** O modelo só é válido dentro do que a amostra cobre, e a função de previsão **bloqueia preços fora dessa faixa**:

| Contexto | Obs. | Preço mínimo (R$/kg) | Preço máximo (R$/kg) |
|---|---:|---:|---:|
| Segunda a quinta | 52 | 1.201,63 | 1.352,42 |
| Sexta | 14 | 1.208,37 | 1.365,49 |
| Fim de semana | 10 | 1.188,86 | 1.354,19 |

O fim de semana tem faixa numérica larga, mas só 10 observações: qualquer recomendação nesse contexto deve ser lida com mais cautela.

---

## Capítulo 12. A prova final: abrindo o cofre

Só depois de congelar fórmula, calendário, coeficientes, fator de smearing, suporte e cenários, com **hash do núcleo preditivo** registrado, o holdout (03/11 a 14/11/2025, dez dias úteis) foi aberto. Nenhum parâmetro foi reestimado. Depois da avaliação, o hash permaneceu idêntico: apenas metadados foram anexados.

| Métrica | Validação temporal (21 dias) | Holdout oficial (10 dias) |
|---|---:|---:|
| WMAPE | 35,29% | 36,28% |
| MAE | 8,84 kg | 6,66 kg |
| RMSE | 15,39 kg | 8,53 kg |
| Erro absoluto mediano | 4,02 kg | 3,18 kg |
| Viés acumulado | -110,83 kg (-21,06%) | -29,76 kg (-16,21%) |
| WMAPE semanal | 30,32% | 16,77% |

![Validação temporal: realizado e previsto um passo à frente](../../../reports/figures/02_validacao_temporal.png)

![Avaliação no holdout oficial](../../../reports/figures/02_holdout.png)

**Leitura.**

- O **WMAPE diário praticamente não mudou** (35,29% contra 36,28%): o modelo não desmoronou fora da amostra, e a validação interna foi uma boa estimativa do erro real.
- Em quilos, o erro é menor no holdout porque o volume médio também é menor: cerca de 18 kg por dia, contra cerca de 25 kg por dia na validação. MAE e RMSE dependem da escala; o WMAPE, não.
- No agregado semanal, o modelo acertou a primeira semana quase em cheio (diferença de 0,52 kg) e **subestimou** a segunda em 30,28 kg.
- O **viés acumulado é de subestimação nos dois testes** (-21% na validação, -16% no holdout). Parece um padrão sistemático e não ruído, e deve ser lido junto com os cenários do capítulo 11.
- O holdout **não contém fins de semana**, então o comportamento do modelo nesse contexto continua sem teste fora da amostra.

---

## Capítulo 13. O que esta história não conta

Uma boa história também delimita o que ela **não** permite concluir.

- **Não é um efeito causal.** O preço histórico não foi randomizado. Pode ter sido definido em resposta à demanda esperada, e a base não traz estoque, promoções, concorrência, clima, imposto realizado ou preço de lista. A curva serve para **planejamento sob incerteza**, não como medida definitiva do que acontece se o preço mudar.
- **A elasticidade é alta e sensível.** Um valor perto de -12 pode refletir, em parte, que a faixa de preços observada é estreita (capítulo 2) e que outubro foi um episódio atípico.
- **Outubro é um episódio.** Oito dos 12 pontos extremos marginais caem entre 7 e 15 de outubro, com preços baixos e volumes altos, seguidos de preços altos e volumes baixos. Os pontos foram mantidos, e a janela de validação (09/10 a 31/10) coincide justamente com esse período, o que torna a validação **exigente**.
- **Não extrapola.** Fora de R$ 1.189 a R$ 1.365/kg não há dado que sustente a curva.
- **Fim de semana é frágil.** Cinco sábados e cinco domingos não sustentam elasticidade própria, e o holdout não os cobre.
- **A previsão não é de alta precisão.** Com WMAPE por volta de 35%, a curva é suficiente para orientar a otimização, desde que as metas semanais sejam tratadas com os cenários de incerteza.
- **A segunda-feira é um agrupamento de conveniência preditiva** (capítulo 6).

---

## Capítulo 14. Quadro-resumo das decisões

| # | Decisão | Evidência | Alternativa descartada | Cap. |
|---|---|---|---|:---:|
| 1 | Investigar a variação temporal do volume | Preço com CV de 3,1% e volume com CV de 89,6%; médias de preço quase iguais entre dias | Explicar o volume só pelo preço | 2 |
| 2 | Dia da semana como variável de calendário | p = 1,1 × 10⁻²³; ΔBIC = -105,7 contra p > 0,57 e ΔBIC > 0 nos demais | Mês, quinzena, semana do mês | 3 |
| 3 | Terça a quinta no mesmo nível | Caixas sobrepostas; p de Holm = 1,000 nos contrastes | Um nível para cada dia | 4, 5 |
| 4 | Sexta com nível próprio | Razão 0,262 (IC 0,195 a 0,353) | Sexta junto com segunda a quinta | 5, 7 |
| 5 | Sábado e domingo agrupados | Cinco observações em cada; IC da razão de 0,51 a 5,75 | Níveis separados | 5 |
| 6 | Segunda agrupada a terça–quinta | WMAPE de 35,29% contra 38,16%; menor erro semanal | P4 (segunda separada) | 6, 7 |
| 7 | Curva de potência | WMAPE de 35,29% contra 35,44% (exponencial); linear inválida | Exponencial e linear | 8 |
| 8 | Sem tendência temporal | WMAPE de 35,94% com tendência; p de Holm = 1,000 | T1 | 8 |
| 9 | Elasticidade única para todos os dias | 76 observações e apenas 10 de fim de semana; no notebook 2.1, a elasticidade por contexto teve WMAPE médio de 44,34% contra 40,22% e p = 0,79 nas interações | Interações preço × calendário (nenhuma especificação do 2.0 as inclui) | 7, 15 |
| 10 | Smearing, HC3 e cenários de incerteza | Heterocedasticidade (p = 0,0175), caudas pesadas, erro de nível de 35% | Previsão pontual com intervalos normais | 9 a 11 |
| 11 | Método analítico (2.0) como narrativa oficial | Decisão do grupo; o método do livro (2.1) chega aos mesmos coeficientes | Método do livro (2.1) como narrativa | 15 |

---

## Capítulo 15. Duas trilhas, um mesmo modelo: a decisão do grupo pelo método analítico

O projeto tem dois notebooks de curva de demanda:

- **2.0, método analítico:** parte dos gráficos, formula hipóteses de agrupamento, testa essas hipóteses e só então valida em janela temporal. É a história contada nos capítulos 2 a 12 deste documento.
- **2.1, método do livro:** segue a sequência de Phillips (seções 4.2 a 4.4). Compara as formas linear, exponencial e de potência só com preço e depois acrescenta variáveis pelo processo *champion-challenger*.

> **Decisão do grupo.** O grupo decidiu apresentar a curva de demanda pelo **método analítico (2.0)** e não pelo método do livro (2.1). Este documento conta a história do 2.0 e usa o 2.1 apenas como evidência complementar.

| Aspecto | 2.0, método analítico (adotado) | 2.1, método do livro |
|---|---|---|
| Ponto de partida | Gráficos de barras e boxplots, que geram hipóteses de agrupamento | Preço sozinho com três formas funcionais, como propõe Phillips |
| Origem dos candidatos de calendário | Leitura dos gráficos de volume por dia da semana | EDA (dia da semana, mês, quinzena, semana do mês, tendência) mais a hipótese de início do mês do documento da Minerva |
| Justificativa dos grupos | Contrastes de Wald com HC3 e correção de Holm entre dias, depois validação | Comparação direta de duas partições prontas (CAL3 e CAL4) por desempenho; o notebook não traz contrastes entre pares de dias |
| Validação temporal | Origem móvel: 55 dias iniciais e 21 previsões um passo à frente | Corte único 52/24 e três janelas expansivas (39/13, 52/13 e 65/11) |
| Variáveis desafiantes | Tendência | Início do mês, semana do mês, tendência e elasticidade por contexto |
| Checagens adicionais | Contrastes, Huber, ajuste sem fim de semana, VIF | Verificação do tipo da seção 4.4 de Phillips (o calendário explica o preço histórico?) |
| Multiplicadores de cenário | 0,641 / 1,000 / 1,498 | 0,519 / 1,000 / 1,752 |
| Artefato | `models/demand_curve_champion.json` | `models/demand_curve_champion_livro.json` |

### Onde as duas trilhas chegam ao mesmo lugar

Caminhos diferentes terminam na **mesma curva**. Os coeficientes dos dois artefatos são idênticos: constante 91,5915, preço -12,3647, sexta -1,3394 e fim de semana -2,9670. Também coincidem o fator de smearing (1,1226), o suporte de preço por contexto e o desempenho no holdout (WMAPE de 36,28%, com 153,87 kg previstos para 183,63 kg realizados). Em ambos:

- o calendário é segunda a quinta, sexta e fim de semana, **sem separar a segunda**;
- a forma é potência, com elasticidade compartilhada;
- nenhuma variável extra (mês, quinzena, semana do mês, início do mês, tendência) é mantida.

Para o grupo, isso é um argumento a favor da robustez: a escolha do método muda **como a decisão é justificada e narrada**, não a curva central. Uma conclusão que sobrevive a duas rotas independentes está menos exposta às escolhas de uma delas.

### O que o método analítico entrega e o do livro não

- **A ponte entre gráfico, hipótese e teste** (capítulos 2 a 5). É ela que explica *por que* terça a quinta ficam juntas: as caixas se sobrepõem no boxplot e os contrastes entre dias não detectam diferença.
- **A tensão da segunda-feira exposta com dois critérios** (p-valor e previsão), em vez de apenas uma comparação de desempenho entre partições.
- **Robustez adicional:** regressão de Huber, ajuste sem fim de semana e VIF.

### O que o método do livro entrega e o analítico não

O 2.1 contém três evidências que o 2.0 não produziu e que podem ser citadas como apoio:

- **Mês, quinzena e semana do mês testados na previsão.** No corte único, semana do mês parecia vencer (WMAPE de 35,49%), mas nas três janelas seu WMAPE médio subiu para 58,16% e a pior janela chegou a 105,54%: sobreajuste. No 2.0, essas variáveis foram descartadas apenas pela triagem de F e BIC do EDA (capítulo 3).
- **Elasticidade por contexto testada.** A inclinação compartilhada teve WMAPE médio de 40,22%, contra 44,34% da inclinação por contexto, e o teste conjunto das interações deu p = 0,79. No 2.0, a elasticidade única é uma escolha de parcimônia; o 2.1 fornece a evidência direta.
- **Verificação do tipo da seção 4.4.** O calendário selecionado explica apenas 0,47% da variação histórica do preço (p = 0,8759), o que reduz a preocupação de que os níveis por dia estejam confundidos com a política de preços. Isso não elimina endogeneidade por demanda antecipada.

### Pontos de atenção de consistência

1. **O notebook 3.0 hoje importa os artefatos do 2.1** (`demand_curve_champion_livro.json` e `demand_curve_uncertainty_livro.json`). Como o núcleo é idêntico, a curva central é a mesma. A diferença está na incerteza: os multiplicadores do 2.1 são mais largos (0,519 a 1,752, contra 0,641 a 1,498) e as chaves dos cenários têm outros nomes (`conservador` e `otimista`, contra `conservative` e `optimistic`). Para apresentar o método analítico de ponta a ponta, o 3.0 precisa apontar para os artefatos do 2.0 ou a diferença precisa ser declarada.
2. **Diagnósticos com pequenas diferenças numéricas entre os notebooks**, apesar de coeficientes idênticos: Breusch-Pagan com p = 0,0175 (2.0) e 0,0422 (2.1); IC HC3 da elasticidade de -17,69 a -7,04 (2.0) e de -17,60 a -7,13 (2.1); leave-one-out de -14,10 a -11,20 (2.0) e de -14,46 a -11,44 (2.1). Este documento não investigou a origem dessas diferenças. Ao citar um desses números, convém indicar o notebook de onde veio.

---

## Capítulo 16. Mapa de artefatos e glossário

**Onde está cada parte da história**

| O quê | Onde |
|---|---|
| EDA, gráficos de calendário e triagem por dia da semana | `notebooks/1.0-minerva-eda-preparacao.ipynb` |
| Contrastes, ranking de calendário, forma, tendência, diagnósticos e holdout | `notebooks/2.0-minerva-curva-demanda-validacao.ipynb` |
| Triagem de hipóteses de calendário | `reports/tables/01_resumo_sazonalidade.csv` |
| Contrastes entre dias | `reports/tables/02_contrastes_calendario.csv` |
| Ranking de calendário, P3 contra P4 e escada incremental | `reports/tables/02_ranking_calendario.csv`, `02_comparacao_p3_p4_por_grupo.csv`, `02_tabela_incremental_modelos.csv` |
| Forma funcional e tendência | `reports/tables/02_ranking_forma.csv`, `02_ranking_tendencia.csv` |
| Coeficientes do campeão | `reports/tables/02_coeficientes_campeao.csv` |
| Previsões do holdout | `data/processed/minerva_previsoes_holdout.csv` |
| Modelo congelado, incerteza e resumo da seleção (método analítico) | `models/demand_curve_champion.json`, `demand_curve_uncertainty.json`, `model_selection_summary.json` |
| Equivalentes do método do livro (hoje importados pelo notebook 3.0) | `models/demand_curve_champion_livro.json`, `demand_curve_uncertainty_livro.json`, `model_selection_summary_livro.json` |
| Função de previsão para o otimizador | `src/modeling/demand_curve.py` |
| Figuras da história | `reports/figures/01_sazonalidade_dia_semana.png`, `01_preco_volume.png`, `02_ranking_calendario.png`, `02_validacao_temporal.png`, `02_diagnosticos_residuos.png`, `02_influencia.png`, `02_curvas_suporte.png`, `02_holdout.png` |

**Documentos relacionados.** O storytelling do EDA com mais detalhe sobre a qualidade da base está em `docs/storytelling-eda-minerva.md`. O notebook `2.1-minerva-curva-demanda-metodo-livro.ipynb` percorre a trilha do método do livro (Phillips); o capítulo 15 compara as duas trilhas e registra a decisão do grupo. O notebook 3.0 consome a curva congelada para otimizar os preços.

**Glossário**

| Termo | Significado |
|---|---|
| **Holdout** | Dados reservados que não participam de nenhuma decisão de modelagem e são usados uma única vez, no fim |
| **Elasticidade-preço** | Variação percentual do volume associada a 1% de variação do preço |
| **Curva de potência** | Modelo `volume = A × preço^(-ε)`; em logaritmo, vira uma reta cujo coeficiente é a elasticidade |
| **WMAPE** | Soma dos erros absolutos dividida pela soma do volume real; mede o erro relativo em kg e não explode com volumes pequenos |
| **Validação temporal (origem móvel)** | Prever cada dia usando só o passado e re-treinar a cada passo, sem embaralhar as datas |
| **HC3** | Estimador de erros-padrão robusto a variância não constante e a pontos influentes |
| **Correção de Holm** | Ajuste dos p-valores quando vários testes são feitos juntos |
| **Smearing de Duan** | Fator que corrige o viés ao converter previsões de `ln(volume)` para quilos |
| **Pooling preditivo** | Agrupar categorias porque isso melhora a previsão, mesmo que haja alguma diferença estatística entre elas |
