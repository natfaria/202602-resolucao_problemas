# Plano do otimizador de margem

Este documento substitui, para o otimizador, os planos anteriores da pasta `docs`. O notebook
`3.0-minerva-otimizacao-precos.ipynb` é mantido como está e não é base para a nova versão.

## Objetivo

Definir o preço diário de um SKU nas duas semanas do planejamento (10 dias úteis, de 03/11 a
14/11/2025) que **maximiza a margem total prevista**, respeitando:

- o volume semanal mínimo e máximo, definido pela meta e sua tolerância;
- a variação máxima de preço entre dias consecutivos;
- a curva de demanda escolhida nos notebooks 2.0 e 2.0.1.

Como a meta é inviável com as regras atuais, o otimizador também precisa mostrar **quanto negociar
de cada restrição** e quanto de margem cada negociação libera.

## Visão geral

| Etapa | Entrega | Para que serve |
|---|---|---|
| 1. Modelo matemático | Formulação completa, a versão final do modelo | Base do relatório e referência para o código |
| 2. Implementação | Três notebooks, um por versão incremental | Resolver o modelo e produzir os resultados |
| 3. Análise e relatório | Recomendação, figuras e tabelas finais | Responder às perguntas do desafio |

O modelo da etapa 1 é escrito completo desde o início. A implementação começa por uma versão
básica e acrescenta partes do mesmo modelo, sem mudar a formulação.

---

## Etapa 1 — Modelo matemático

### 1.1 Descrição em texto

Para cada dia do horizonte, escolhe-se um preço. A curva de demanda transforma esse preço em volume
previsto. A margem do dia é a receita líquida de imposto menos o custo do volume vendido. O modelo
escolhe a sequência de preços com a maior soma de margens, desde que:

1. o volume de cada semana fique entre o mínimo e o máximo da meta;
2. o preço de um dia não se afaste mais que o limite permitido do preço do dia anterior;
3. o primeiro preço não se afaste mais que o limite permitido do último preço praticado;
4. nenhum preço saia da faixa observada no histórico para aquele tipo de dia.

O volume não é uma decisão: é consequência do preço.

### 1.2 Conjuntos

| Símbolo | Significado | Valor no caso |
|---|---|---|
| $T$ | Dias do horizonte, em ordem | 10 dias úteis |
| $W$ | Semanas | 2 |
| $T_w$ | Dias da semana $w$ | 5 dias cada |
| $c(t)$ | Contexto de calendário do dia $t$ | segunda a quinta ou sexta |

Sexta-feira e a segunda-feira seguinte são dias consecutivos para a regra de variação.

### 1.3 Parâmetros

| Símbolo | Significado | Valor base | Origem |
|---|---|---|---|
| $p^{ant}$ | Último preço praticado | R\$ 1.318,92 | 31/10/2025, desenvolvimento |
| $c$ | Custo por kg | R\$ 1.004,97 | Média ponderada da última semana do desenvolvimento, melhor estimativa disponível antes do horizonte |
| $\tau$ | Imposto sobre a receita | 7% | Definição do projeto |
| $M_w$ | Meta semanal | 165 kg | Arquivo de restrições da instância |
| $\varepsilon^-, \varepsilon^+$ | Tolerância abaixo e acima da meta | 30% (base) e 5% (sensibilidade) | Instância e enunciado |
| $\Delta_t$ | Variação máxima entre o dia $t$ e o dia anterior; para $t = 1$, o dia anterior é $p^{ant}$ (âncora) | R\$ 2,00 em todos os dias | Instância; a âncora vale |
| $\underline p_{c}, \overline p_{c}$ | Faixa de preço observada por contexto | seg–qui: 1.201,63 a 1.352,42; sexta: 1.208,37 a 1.365,49 | Artefato da curva |
| $\beta$ | Elasticidade-preço | −12,3647 | Curva P3 |
| $A_{c}$ | Nível de demanda do contexto, já com smearing | calculado do artefato | Curva P3 |

Limites semanais:

$$\underline Q_w = M_w(1-\varepsilon^-) \qquad \overline Q_w = M_w(1+\varepsilon^+)$$

Com 30%: de 115,5 a 214,5 kg. Com 5%: de 156,75 a 173,25 kg.

### 1.4 Curva de demanda

$$q_t(p) = A_{c(t)}\, p^{\beta}, \qquad A_{c} = SF\cdot e^{\beta_0 + \gamma_{c}}$$

É a curva P3 do notebook 2.0, com elasticidade única, um nível por contexto e o fator de smearing
$SF = 1{,}1226$. O otimizador não reestima nenhum parâmetro.

### 1.5 Variáveis

- $p_t$: preço do dia $t$ (decisão).
- $q_t$: volume previsto do dia $t$ (derivado, $q_t = q_t(p_t)$).
- $s_w^-, s_w^+ \ge 0$: kg abaixo do mínimo e acima do máximo na semana $w$ (somente na versão
  flexível).

### 1.6 Modelo estrito

$$\max_{p}\ \sum_{t\in T}\big[(1-\tau)\,p_t - c\big]\, q_t(p_t)$$

sujeito a:

$$\underline Q_w \le \sum_{t\in T_w} q_t(p_t) \le \overline Q_w \qquad \forall w \tag{meta}$$

$$|p_t - p_{t-1}| \le \Delta_t \qquad t = 1,\dots,|T|,\quad p_0 = p^{ant} \tag{variação e âncora}$$

A âncora é a restrição de variação do primeiro dia. Escrever um limite $\Delta_t$ por dia permite
relaxar a âncora sem criar outro modelo (seção 1.11).

$$\underline p_{c(t)} \le p_t \le \overline p_{c(t)} \qquad \forall t \tag{faixa}$$

### 1.7 Modelo flexível (quando o estrito é inviável)

As restrições de meta ganham folgas:

$$\underline Q_w - s_w^- \le \sum_{t\in T_w} q_t(p_t) \le \overline Q_w + s_w^+$$

E o problema é resolvido em duas etapas, sem peso arbitrário de penalidade:

1. minimizar a violação total $V^* = \min \sum_w (s_w^- + s_w^+)$;
2. maximizar a margem com $\sum_w (s_w^- + s_w^+) \le V^*$.

O resultado é o plano que mais se aproxima da meta e, entre os que se aproximam igualmente, o de
maior margem.

### 1.8 Formulação resolvida: grade de preços

Como a curva não tem lag, o volume de cada dia depende apenas do preço daquele dia. Os preços são
discretizados em uma grade $P = \{P_1, \dots, P_K\}$ (passo de R\$ 0,50) e cada dia escolhe um ponto:

$$x_{tk}\in\{0,1\}, \qquad \sum_k x_{tk} = 1, \qquad p_t = \sum_k P_k x_{tk}$$

Volume e margem de cada ponto são calculados antes:
$Q_{tk} = q_t(P_k)$ e $G_{tk} = [(1-\tau)P_k - c]\,Q_{tk}$. Assim, objetivo, meta e variação
ficam lineares:

$$\max \sum_{t,k} G_{tk}x_{tk} \quad \text{s.a.}\quad \underline Q_w \le \sum_{t\in T_w}\sum_k Q_{tk}x_{tk} \le \overline Q_w,\quad -\Delta_t \le p_t - p_{t-1} \le \Delta_t$$

A faixa de preço e a variação do primeiro dia em relação a $p^{ant}$ entram eliminando pontos da
grade. O problema tem cerca de 3.600
variáveis binárias e é resolvido com HiGHS (`scipy.optimize.milp`). O solver encontra o ótimo
global **na grade**, dentro das tolerâncias de otimalidade informadas. Por isso, status, limite de
tempo e `mip_gap` devem ser sempre reportados, e resultados que ficam exatamente em um limiar
devem ser conferidos com uma grade mais fina.

### 1.9 Propriedades úteis para o relatório

- **Preço ótimo sem restrições:** $p^* = \dfrac{c}{1-\tau}\cdot\dfrac{\beta}{\beta+1} \approx$
  R\$ 1.176/kg, abaixo da faixa permitida. Com a curva P3 e esse custo, reduzir o preço dentro da
  faixa aumenta volume e margem ao mesmo tempo. Essa conclusão vale para essa curva e esse custo;
  com elasticidade −7, por exemplo, $p^* \approx$ R\$ 1.261, e reduzir abaixo disso troca margem por
  volume.
- **Volume máximo atingível:** é obtido descendo o preço o máximo permitido todos os dias. Com
  $\Delta_t =$ R\$ 2 e $p^{ant} =$ R\$ 1.318,92, chega a 79,20 kg na semana 1 e 87,05 kg na
  semana 2. Isso explica a inviabilidade sem precisar do solver.
- **Inviabilidade:** resulta da combinação entre preço inicial alto, limite de variação baixo e
  mínimo semanal exigido. Afrouxar qualquer um dos três pode recuperar a viabilidade.

### 1.10 Fora do modelo (decisões registradas)

| Item | Decisão | Motivo |
|---|---|---|
| Otimização robusta (mesmo plano para todos os cenários) | Não usada | Com os multiplicadores atuais (×0,64 e ×1,50), garantir o mínimo no conservador exige ≥ 180,1 kg no central, e respeitar o máximo no otimista exige ≤ 143,2 kg. As duas exigências são incompatíveis |
| Cenários conservador e otimista | Usados só para avaliar o plano escolhido | Mostram o risco sem distorcer a decisão |
| Lag de volume | Não usado | Sem ganho comprovado no 2.0.1 e tornaria os dias dependentes entre si |
| Preços fora da faixa observada | Proibidos | A curva não foi validada nessa região |

### 1.11 Formas de negociar as regras

O modelo não muda; muda apenas o valor dos parâmetros. Cada alavanca é avaliada isoladamente, com as
demais na regra atual, e depois em conjunto.

| Alavanca | Parâmetro alterado | Leitura comercial |
|---|---|---|
| Limite de variação diária | $\Delta_t = \Delta$ para todos os dias | Permitir movimentos maiores durante todo o horizonte |
| Mínimo semanal | $\varepsilon^-$, com o máximo fixo | Aceitar vender menos |
| Máximo semanal | $\varepsilon^+$ | Aceitar vender mais; só limita quando a variação é liberada |
| **Âncora: primeiro ajuste** | $\Delta_1$, com R\$ 2 nos demais dias | Permitir um ajuste maior apenas na entrada do horizonte |
| **Âncora: janela de transição** | $\Delta_t = \Delta_{trans}$ nos $k$ primeiros dias, R\$ 2 depois | Permitir uma transição de preço por alguns dias e voltar à regra |
| **Âncora: remoção** | $\Delta_1$ sem limite | Começar o horizonte em qualquer preço da faixa |

As três formas de relaxar a âncora são o mesmo parâmetro visto de ângulos diferentes: o primeiro
ajuste é a janela com $k = 1$, e a remoção é o primeiro ajuste sem limite. A remoção serve como
limite superior de referência; a diferença de margem entre ela e a regra atual compara um plano que
descumpre a meta com outro que a cumpre, e deve ser apresentada como diferença simulada entre
configurações, não como ganho.

Valores mínimos para viabilizar a meta, já calculados no estudo exploratório (cenário central):

| Janela de transição $k$ | Tolerância 30% | Tolerância 5% |
|---:|---:|---:|
| 1 dia (primeiro ajuste) | R\$ 41,47 | R\$ 72,56 |
| 2 dias | R\$ 24,02 | R\$ 41,04 |
| 3 dias | R\$ 18,64 | R\$ 31,22 |
| 5 dias (semana 1) | R\$ 16,10 | R\$ 27,27 |
| 10 dias (horizonte todo) | R\$ 16,10 | R\$ 27,27 |

Uma janela de transição na primeira semana exige o mesmo limite que liberar a variação nas duas
semanas: a segunda semana pode permanecer em R\$ 2. É, portanto, um pedido de negociação menor para o
mesmo resultado de viabilidade. A margem de cada opção será calculada no notebook 3.2.

---

## Etapa 2 — Implementação em três versões

Cada versão tem um notebook próprio, no mesmo padrão de texto e explicação do 2.0 e do 2.0.1:

| Versão | Notebook | Pergunta que responde |
|---|---|---|
| 1 | `notebooks/3.1-minerva-otimizador-estrito.ipynb` | Existe plano que cumpra todas as regras? Se não, por quê? |
| 2 | `notebooks/3.2-minerva-otimizador-flexivel.ipynb` | Qual o melhor plano possível e quanto negociar de cada regra? |
| 3 | `notebooks/3.3-minerva-otimizador-estresse.ipynb` | Quão confiável é a recomendação? |

As versões 1 e 2 são formulações diferentes do mesmo problema: compartilham curva, grade, variação,
âncora e faixa de preço, mas a versão 1 trata a meta como obrigatória e a versão 2 permite violá-la,
medindo a violação. A versão 3 não cria modelo novo; avalia o plano recomendado na versão 2.

Para não duplicar código, as funções comuns (entradas, tabela de volume e margem por preço da grade
e resolução com o solver) são desenvolvidas no notebook 3.1 e, ao final da versão 1, movidas para um
módulo pequeno em um pacote novo, `src/otimizador/`. O pacote `src/optimization/` contém o otimizador
anterior e não é reutilizado nem alterado. Os notebooks 3.2 e 3.3 importam o módulo novo.

Entradas, em todas as versões: artefato `models/demand_curve_champion.json`, base de
desenvolvimento processada e `data/interim/minerva_restricoes.csv`. O conjunto de teste só é
usado na etapa 3.

### Padrão dos notebooks

Os notebooks seguem a forma do 2.0 e do 2.0.1: cada seção é uma unidade curta com três partes, sem
células longas que façam várias coisas ao mesmo tempo.

1. **Texto antes do código:** o que a seção faz e por quê, em linguagem direta.
2. **Código da seção:** uma célula, ou poucas, com uma única responsabilidade (por exemplo, só
   montar a tabela de volume, ou só resolver o modelo).
3. **Resultado:** texto depois da execução, com os números obtidos e o que eles significam.

Funções são definidas na seção em que aparecem pela primeira vez, e não todas no início. Cada
notebook começa com a pergunta que responde e termina com conclusões numeradas.

**Seções do 3.1 (estrito)**

1. Objetivo e pergunta do notebook.
2. Modelo matemático: resumo da etapa 1, com referência a este documento.
3. Entradas: curva, preço anterior, custo, imposto, metas, limites; tabela de premissas.
4. Curva no horizonte: nível por dia e volume na faixa de preço permitida.
5. Grade de preços: tabela de volume e margem por dia × preço.
6. Referências simples: manter o preço de 31/10 e descer R\$ 2 por dia.
7. Montagem do modelo estrito: variáveis, objetivo e restrições, uma de cada vez.
8. Resolução com a regra atual: status do solver.
9. Diagnóstico da inviabilidade: volume máximo atingível contra o mínimo exigido.
10. Resolução com regras liberadas: verificação de que o modelo encontra soluções quando elas existem.
11. Conclusões.

**Seções do 3.2 (flexível)**

1. Objetivo e pergunta do notebook.
2. Do modelo estrito ao flexível: folgas e resolução em duas etapas.
3. Melhor plano possível com a regra atual.
4. Alavanca 1: limite de variação diária.
5. Alavanca 2: mínimo semanal.
6. Alavanca 3: âncora (primeiro ajuste, janela de transição e remoção).
7. Painel comparativo das alavancas.
8. Mapa conjunto: variação × tolerância.
9. Tabela de negociação: opções viáveis, o que exigem e a margem de cada uma.
10. Conclusões.

**Seções do 3.3 (estresse)**

1. Objetivo e pergunta do notebook.
2. Plano recomendado no 3.2.
3. Avaliação nos cenários conservador e otimista.
4. Sensibilidade à elasticidade.
5. Sensibilidade ao custo.
6. Validação numérica: `mip_gap`, grade fina nos limiares e fórmula do volume máximo.
7. Conclusões e limitações.

### Versão 1 — Modelo estrito e diagnóstico (básica)

**Escopo**
- Carregar entradas e montar a tabela de volume e margem por dia × preço da grade.
- Resolver o modelo estrito da seção 1.6.
- Se for inviável, mostrar por quê: volume máximo atingível de cada semana contra o mínimo exigido.
- Comparar com duas referências: manter o preço de 31/10 e descer R\$ 2 por dia.

**Saídas:** preço e volume diários, volume semanal contra a faixa, margem e status do solver.

**Critérios de aceite**
- Reproduzir o volume máximo de 79,20 e 87,05 kg com a regra atual.
- Margem de referência com preço constante: cerca de R\$ 33,4 mil. Rampa de R\$ 2: cerca de
  R\$ 35,2 mil.
- Com o limite de variação liberado, encontrar uma solução viável e coerente com $p^*$ (preços na
  borda inferior da faixa até o teto de volume limitar).

### Versão 2 — Modelo flexível e curvas de negociação

**Escopo**
- Implementar o modelo flexível em duas etapas (seção 1.7).
- Varrer cada alavanca da seção 1.11 isoladamente, mantendo as demais na regra atual:
  1. limite de variação diária (R\$ 2 a R\$ 60);
  2. mínimo semanal em kg, com o máximo fixo;
  3. relaxação da âncora: limite do primeiro ajuste (de R\$ 2 até a remoção) e janela de transição
     ($k$ = 1, 2, 3 e 5 dias).
- Mapa conjunto: limite de variação × tolerância, com os kg fora da faixa e a margem.
- Tudo com tolerância de 30% e sensibilidade com 5%.

**Saídas:** painel com três gráficos na mesma escala vertical (variação diária, mínimo semanal e
âncora), pontos viáveis cheios e inviáveis vazados, premissas na legenda e o valor mínimo viável de
cada alavanca marcado; curva da janela de transição; mapa conjunto; tabela-resumo de negociação com
a margem de cada opção viável.

**Critérios de aceite**
- Valores mínimos para viabilizar a meta, cenário central: limite de variação de R\$ 16,10 (30%) e
  R\$ 27,27 (5%); tolerância de 52% com R\$ 2; janela de transição conforme a tabela da seção 1.11.
- Flexibilizar só o mínimo semanal não altera a margem (rampa de R\$ 2).

### Versão 3 — Testes de estresse e validação

**Escopo**
- Avaliar o plano recomendado nos cenários conservador e otimista: volume e margem que ele
  produziria, sem reotimizar.
- Sensibilidade à elasticidade (−7, −12,36 e −16), informando o preço de referência em que o volume
  é mantido (R\$ 1.274,43), e ao custo (R\$ 1.004,97 e R\$ 1.010,45).
- Validação numérica: status e `mip_gap` em todas as resoluções, conferência dos limiares com
  grade mais fina e conferência do volume máximo pela fórmula da seção 1.9.

**Saídas:** tabela de estresse do plano recomendado e tabela de sensibilidade.

**Critérios de aceite**
- Toda conclusão econômica do relatório vem acompanhada da faixa de elasticidade em que ela vale.

---

## Etapa 3 — Análise e relatório

1. **Recomendação de negociação:** qual restrição flexibilizar e quanto, com a margem prevista e o
   risco nos cenários. Até aqui, a leitura é: o limite de variação diária é a alavanca que gera
   margem; flexibilizar só o mínimo semanal compra viabilidade sem ganho de margem; relaxar a
   âncora com uma janela de transição na primeira semana viabiliza a meta com o mesmo limite diário
   e mantém a regra de R\$ 2 na segunda semana; o primeiro ajuste isolado exige um corte grande.
2. **Respostas às perguntas do enunciado:** impacto da meta semanal e impacto da variação entre
   dias consecutivos, a partir dos painéis da versão 2.
3. **Uso do conjunto de teste:** relatar a margem realizada pela Minerva no período e comparar com a
   margem que a curva previa para os preços praticados. O teste não permite medir o que teria
   acontecido com os preços recomendados.
4. **Limitações:** elasticidade observacional, erro semanal de previsão (~39%, notebook 2.0.1)
   maior que a tolerância de 30%, e soluções próximas da borda inferior da faixa de preço.
