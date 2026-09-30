# Storytelling da análise exploratória da base Minerva

## 1. A pergunta que orienta a exploração

O desafio não consiste apenas em prever vendas. A previsão será posteriormente usada por um modelo
de otimização que escolherá preços diários, respeitando metas semanais de volume e limites de
variação entre preços consecutivos. Por isso, a análise exploratória precisa responder primeiro a
uma pergunta mais básica:

> A amostra possui qualidade, variação de preço e cobertura de calendário suficientes para estimar
> uma relação preço-volume útil à tomada de decisão?

O EDA não tenta escolher antecipadamente a curva definitiva. Seu papel é conhecer a amostra,
identificar limitações, formular hipóteses e entregar um conjunto pequeno de alternativas para a
validação temporal posterior.

## 2. Primeiro, proteger a avaliação futura

A planilha contém 86 observações de um único produto. Antes de qualquer gráfico ou teste, os dados
foram separados cronologicamente:

- 76 observações entre 1º de agosto e 31 de outubro de 2025 formam o conjunto de desenvolvimento;
- 10 observações posteriores formam o holdout oficial;
- nenhum resultado do holdout foi usado para criar hipóteses nesta exploração.

Essa separação é importante porque a mesma amostra não deve ser usada simultaneamente para formular
hipóteses e declarar que elas generalizam. O holdout permanece reservado para a avaliação final do
modelo que será escolhido no notebook seguinte.

## 3. A base é consistente, mas possui limites informacionais

A auditoria encontrou uma base tecnicamente limpa: não existem datas duplicadas por produto,
valores ausentes ou valores não positivos em volume, receita e custo. Portanto, não foi necessário
imputar dados nem excluir registros.

Essa consistência não significa que toda a demanda esteja explicada. A planilha não informa estoque,
ruptura, promoções, preço de concorrentes, clima, preço de lista ou imposto realizado. Também não é
possível saber se o preço médio diário representa um único preço oferecido ou uma média de várias
transações. Consequentemente, a relação estimada será uma associação condicional aos dados
disponíveis, e não uma demonstração causal completa do efeito do preço.

A instância de otimização informa, para cada uma das duas semanas, meta de 165 kg, tolerância de 30%
e variação máxima de R$ 2,00 entre preços de dias consecutivos. Esses valores deverão ser lidos
diretamente da planilha na etapa de otimização.

## 4. Reconstruindo as variáveis de decisão

Como a fonte apresenta receita, custo e volume totais, o preço e o custo unitários foram
reconstruídos:

- `preco_kg = receita / volume`;
- `custo_kg = custo / volume`;
- `margem_unitaria_ex_post = preco_kg - custo_kg`.

Preço e calendário podem contribuir para a previsão de volume porque são informações disponíveis no
momento da decisão. Receita e margem realizadas são consequências do preço e do volume observados;
usá-las como explicativas da demanda criaria uma relação circular. O custo será importante para a
função de margem da otimização, mas não entra automaticamente como explicação do comportamento do
cliente.

Também foram criadas representações de calendário e tempo, como dia da semana, fim de semana, mês,
quinzena, semana do mês e índice cronológico. Elas são hipóteses candidatas, não variáveis aprovadas
antecipadamente.

## 5. O volume é heterogêneo; o preço possui variação observável

O volume diário varia de 0,59 kg a 100 kg. Sua média é 21,13 kg, enquanto a mediana é 16,70 kg. A
diferença entre essas medidas e a assimetria positiva de 1,665 mostram uma distribuição com cauda à
direita: a maior parte dos dias possui volume relativamente baixo, acompanhada por poucos dias de
volume muito alto.

Essa forma sustenta testar o logaritmo do volume no modelo posterior. A transformação reduz a
influência da escala dos maiores valores sem exigir que eles sejam removidos e permite comparar uma
curva de potência com outras formas funcionais.

O preço médio realizado varia de R$ 1.188,86/kg a R$ 1.365,49/kg, com média de R$ 1.275,02/kg. Essa
amplitude fornece variação empírica para estudar a associação preço-volume, mas também define o
limite da análise: previsões e recomendações fora desse intervalo seriam extrapolações sem suporte
direto na amostra.

O custo unitário é mais concentrado, com média de R$ 981,63/kg e desvio-padrão de R$ 12,96/kg. Isso
reforça que, nesta amostra, as maiores mudanças visuais ocorrem principalmente em preço e volume.

## 6. A ordem temporal revela episódios, não apenas pontos isolados

Quando os dados são colocados em ordem cronológica, surge uma história que seria escondida por uma
análise apenas agregada.

Agosto e setembro apresentam alternância de volumes, em sua maioria abaixo de 50 kg. Entre 7 e 16 de
outubro, preços mais baixos coincidem com uma sequência de volumes elevados, incluindo observações
entre aproximadamente 50 kg e 100 kg. Na parte final do mês, preços acima de R$ 1.325/kg coincidem
com volumes muito menores.

Visualmente, esse comportamento é compatível com uma relação negativa entre preço e volume. Porém,
ele também mostra que preço e tempo se movimentam juntos. Assim, parte da relação atribuída ao preço
pode refletir uma mudança de regime, um evento comercial não observado ou outro fator associado ao
período. O índice de tempo deve, portanto, ser tratado como análise de sensibilidade, e não incluído
automaticamente na curva.

## 7. O calendário muda o nível de volume

A cobertura da semana é desigual. Segunda a quinta possuem 13 observações cada e sexta possui 14.
Sábado e domingo possuem apenas cinco observações cada.

As médias de volume também diferem substancialmente:

| Dia | Volume médio |
|---|---:|
| Segunda | 32,58 kg |
| Terça | 24,45 kg |
| Quarta | 28,25 kg |
| Quinta | 28,64 kg |
| Sexta | 7,72 kg |
| Sábado | 2,26 kg |
| Domingo | 1,04 kg |

As faixas de preço apresentam sobreposição entre os dias, enquanto os níveis de volume se separam
de maneira clara entre segunda a quinta, sexta e fim de semana. Isso sugere que o calendário pode
alterar o patamar esperado de demanda mesmo quando uma única resposta ao preço é compartilhada.

Ao mesmo tempo, as cinco observações de sábado e as cinco de domingo são insuficientes para sustentar
elasticidades próprias com estabilidade. Uma especificação inicial defensável deve usar poucos
parâmetros e compartilhar a inclinação do preço entre os contextos.

## 8. A sazonalidade marginal pode ser confundida com preço

Os recortes de mês, quinzena e semana do mês exibem diferenças visuais de volume. Entretanto, essas
diferenças aparecem junto de mudanças no preço médio:

- outubro possui volume médio de 25,83 kg, mas contém maior dispersão e o ponto de 100 kg;
- a primeira quinzena combina volume médio de 25,94 kg com preço médio de R$ 1.258,76/kg;
- a segunda quinzena combina volume médio de 16,56 kg com preço médio de R$ 1.290,45/kg;
- semanas 2 e 3 do mês apresentam maior volume e preços menores;
- semanas 4 e 5 apresentam menor volume e preços médios acima de R$ 1.300/kg.

Portanto, não seria correto interpretar essas diferenças como sazonalidade pura. Um grupo pode ter
vendido mais simplesmente porque recebeu preços menores. Para separar parcialmente essas dimensões,
cada hipótese de calendário foi adicionada a um baseline log-log que já contém preço.

## 9. A triagem controlada prioriza dia da semana

O teste F conjunto foi usado para verificar se os coeficientes de cada variável de calendário
acrescentam ajuste ao baseline com preço. O BIC foi usado como evidência complementar, penalizando o
aumento de complexidade. Como a amostra é pequena e temporal, essa triagem não substitui a validação
fora da janela de ajuste.

Os resultados foram:

| Hipótese | p-valor do teste F | ΔBIC | Leitura exploratória |
|---|---:|---:|---|
| Mês | 0,698 | +7,903 | Não melhorou o baseline |
| Quinzena | 0,579 | +4,008 | Não melhorou o baseline |
| Semana do mês | 0,852 | +15,873 | Não melhorou o baseline |
| Dia da semana | aproximadamente 1,11 × 10⁻²³ | -105,737 | Forte ganho de ajuste |

Mês, quinzena e semana do mês não apresentaram ganho suficiente para compensar seus parâmetros
adicionais. Dia da semana, por outro lado, apresentou forte evidência de diferenças de nível mesmo
após o controle exploratório pelo preço. Isso o transforma em candidato prioritário, mas ainda não
define se a melhor representação será sete dias, uma indicação de fim de semana ou um agrupamento
mais parcimonioso.

## 10. A relação preço-volume é negativa nos dias úteis

Os gráficos em escala original e log-log mostram uma tendência decrescente nos dias úteis. Quando a
correlação é calculada separadamente por dia da semana, os coeficientes de Pearson de segunda a
sexta ficam entre -0,628 e -0,872. As correlações de Spearman também são negativas, especialmente na
segunda (-0,775) e na quinta (-0,868).

Esse padrão é compatível com uma curva de demanda decrescente. Contudo, correlação não mede efeito
causal e não controla todos os fatores ausentes da base. No sábado, a correlação de Pearson é
positiva, e no domingo a correlação de Spearman é próxima de zero. Como cada um desses grupos possui
somente cinco pontos, o comportamento de fim de semana deve ser interpretado como instável, e não
como evidência de uma resposta econômica diferente.

A hipótese mais defensável para iniciar a modelagem é, portanto, uma elasticidade compartilhada com
interceptos ou níveis diferentes por contexto de calendário.

## 11. Os extremos formam um episódio que merece diagnóstico

A regra de 1,5 vezes o intervalo interquartil, aplicada dentro de cada dia da semana, sinalizou 12
datas distintas. Onze foram extremas em volume, três em preço e duas simultaneamente nos dois
critérios.

Oito dessas sinalizações estão concentradas entre 7 e 15 de outubro. Essa concentração temporal
indica que os pontos podem pertencer a um episódio operacional ou comercial, em vez de serem erros
independentes. Além disso, a sequência posterior combina aumento expressivo de preço e redução de
volume.

Por esse motivo, nenhum ponto foi removido no EDA. A próxima etapa deverá avaliar resíduos,
alavancagem, influência e estabilidade temporal depois de controlar preço e calendário. A exclusão
de uma observação somente seria justificável por erro comprovado ou por uma regra definida antes da
comparação final dos modelos.

## 12. A história que os dados contam

A amostra conta uma história coerente, mas incompleta. Existe variação de preço suficiente para
estudar resposta de demanda e, nos dias úteis, preços maiores aparecem associados a volumes menores.
Ao mesmo tempo, o nível de vendas muda fortemente ao longo da semana e os episódios de outubro
mostram que preço, calendário e tempo não podem ser analisados isoladamente.

O principal aprendizado do EDA não é que uma curva específica já venceu. O aprendizado é que uma
curva simples somente de preço provavelmente omite estrutura relevante, enquanto uma curva com
muitos parâmetros por dia da semana seria excessiva para 76 observações e especialmente frágil nos
fins de semana.

Assim, o próximo notebook deve comparar temporalmente:

1. uma curva de potência apenas com preço;
2. uma curva com indicação parcimoniosa de fim de semana;
3. uma curva com níveis completos por dia da semana;
4. uma alternativa intermediária de agrupamento de calendário;
5. formas exponencial e linear como concorrentes funcionais;
6. tendência temporal apenas como sensibilidade.

A escolha deverá considerar erro em quilogramas, viés, desempenho semanal, coerência econômica,
positividade das previsões e simplicidade. Somente depois de congelar fórmula, variáveis e critérios
o modelo poderá ser aplicado ao holdout e, em seguida, integrado à otimização de preços.

## 13. Limites da conclusão exploratória

O EDA permite concluir que:

- a base é tecnicamente consistente;
- existe suporte de preço para estimar relações dentro da faixa observada;
- dia da semana é uma hipótese relevante de nível;
- fins de semana possuem suporte insuficiente para elasticidades próprias;
- a associação preço-volume é predominantemente negativa nos dias úteis;
- episódios temporais e variáveis omitidas impedem uma interpretação causal direta;
- nenhum modelo final deve ser escolhido apenas pelos gráficos, correlações, teste F ou BIC.

Ele não permite concluir que:

- o preço seja a única causa das mudanças de volume;
- os pontos extremos sejam erros;
- o padrão observado possa ser extrapolado para qualquer preço;
- uma codificação específica de calendário já seja a vencedora;
- o desempenho dentro da amostra represente desempenho futuro.

## 14. Materiais relacionados

- Notebook executado: `notebooks/1.0-minerva-eda-preparacao.ipynb`.
- Plano metodológico: `docs/docs/plano-acao-tres-notebooks.md`.
- Enunciado do desafio: `docs/referencias/Minerva_Unifesp_ITA.pdf`.
- PHILLIPS, Robert L. *Pricing and Revenue Optimization*. 2. ed.
- MULLAPUDI, Pavan Nithin. *Pricing Optimization across Domains*.

## Resumo Alto Nível
- A base é utilizável: não há dados ausentes, duplicados ou valores inválidos nas 76 observações de desenvolvimento.
- Existe variação de preço suficiente, mas as conclusões valem apenas para a faixa observada de aproximadamente R$ 1.189 a R$ 1.365/kg.
- Preço e volume apresentam associação negativa nos dias úteis: preços maiores geralmente aparecem acompanhados de volumes menores.
- Dia da semana é a principal variável contextual: mesmo controlando exploratoriamente pelo preço, apresentou forte ganho de ajuste.
- Mês, quinzena e semana do mês não mostraram contribuição clara depois do controle pelo preço.
- Fim de semana possui poucos dados: são apenas cinco sábados e cinco domingos, insuficientes para estimar elasticidades específicas com segurança.
- Preço, calendário e tempo estão parcialmente confundidos: especialmente em outubro, quando preços baixos coincidem com volumes elevados.
- Os pontos extremos não devem ser removidos automaticamente: vários pertencem a um episódio temporal coerente de outubro.
- A interpretação não é causal: faltam informações como estoque, promoções, concorrência, clima e preço de lista.
- Nenhum modelo foi escolhido no EDA: a hipótese inicial mais defensável é uma elasticidade compartilhada, com diferentes níveis de demanda por contexto de calendário, a ser validada temporalmente no Notebook 2.
