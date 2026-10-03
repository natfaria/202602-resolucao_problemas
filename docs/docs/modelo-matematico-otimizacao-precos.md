# Modelo matemático genérico para otimização de preços

## 1. Finalidade e escopo

Este documento formaliza um modelo genérico para definir uma sequência de preços ao longo de um
horizonte de decisão. O objetivo é maximizar a margem de contribuição prevista, respeitando metas
de volume, estabilidade entre preços consecutivos e os limites de validade da curva de demanda.

A formulação não contém valores de uma instância específica. Todos os valores devem ser fornecidos
pela descrição do problema ou por artefatos produzidos e congelados antes da otimização. Essa
separação permite reutilizar o mesmo modelo em outros horizontes, produtos e políticas comerciais.

O modelo possui duas camadas independentes:

1. uma camada estatística, que fornece a função de demanda prevista;
2. uma camada de decisão, que recebe essa função sem reestimá-la e escolhe os preços.

O resultado da otimização é condicional às premissas da curva de demanda e aos parâmetros
operacionais informados. Ele não transforma automaticamente uma associação estatística em efeito
causal.

## 2. Conjuntos e índices

| Símbolo | Definição |
|---|---|
| $T$ | Conjunto ordenado dos períodos de decisão do horizonte |
| $t \in T$ | Índice de um período de decisão |
| $W$ | Conjunto de semanas ou janelas nas quais existem metas de volume |
| $w \in W$ | Índice de uma semana ou janela de controle |
| $T_w \subseteq T$ | Períodos que pertencem à semana ou janela $w$ |
| $C$ | Conjunto de contextos conhecidos antes da decisão, como grupo de calendário |
| $c(t) \in C$ | Contexto associado ao período $t$ |
| $S$ | Conjunto opcional de cenários de demanda |
| $s \in S$ | Índice de um cenário de demanda |
| $s_0$ | Cenário de referência usado na formulação determinística |

O conjunto $T$ deve possuir uma ordem total. Para cada período que não seja o primeiro, o símbolo
$t-1$ representa a decisão imediatamente anterior na sequência operacional, que pode ser diferente
do dia imediatamente anterior no calendário.

Os subconjuntos $T_w$ devem cobrir o horizonte de acordo com a regra operacional da meta. Caso um
período pertença a mais de uma janela, isso deve ser declarado explicitamente na instância.

## 3. Parâmetros

### 3.1 Parâmetros econômicos e operacionais

| Símbolo | Unidade | Definição |
|---|---:|---|
| $p^{\mathrm{ant}}$ | moeda/unidade | Último preço conhecido antes do horizonte |
| $c_t$ | moeda/unidade | Custo unitário previsto para o período $t$ |
| $\tau_t$ | proporção | Alíquota ad valorem aplicada à receita no período $t$ |
| $\underline p_t$ | moeda/unidade | Menor preço admissível no período $t$ |
| $\overline p_t$ | moeda/unidade | Maior preço admissível no período $t$ |
| $\Delta_0$ | moeda/unidade | Variação máxima entre o preço anterior e a primeira decisão |
| $\Delta_t$ | moeda/unidade | Variação máxima entre $p_{t-1}$ e $p_t$ |
| $M_w$ | unidade de volume | Meta nominal de volume da janela $w$ |
| $\varepsilon_w^-$ | proporção | Tolerância permitida abaixo da meta de $w$ |
| $\varepsilon_w^+$ | proporção | Tolerância permitida acima da meta de $w$ |
| $\underline Q_w$ | unidade de volume | Limite inferior de volume da janela $w$ |
| $\overline Q_w$ | unidade de volume | Limite superior de volume da janela $w$ |
| $h_t$ | moeda/unidade | Incremento comercial opcional para o preço do período $t$ |

Quando a tolerância for expressa em torno de uma meta, os limites semanais são calculados por:

$$
\underline Q_w = M_w(1-\varepsilon_w^-)
$$

$$
\overline Q_w = M_w(1+\varepsilon_w^+)
$$

Em linguagem natural, a meta nominal é transformada em uma faixa admissível. As tolerâncias
inferior e superior podem ser diferentes. Se a regra de negócio estabelecer somente uma meta
mínima, $\overline Q_w$ deve ser omitido em vez de receber um valor artificialmente grande.

### 3.2 Parâmetros da demanda

| Símbolo | Definição |
|---|---|
| $\theta$ | Conjunto congelado de parâmetros da curva de demanda |
| $x_t$ | Vetor de características conhecidas antes da decisão em $t$ |
| $D_t(p;\theta)$ | Demanda prevista no período $t$ quando o preço é $p$ |
| $k_s$ | Multiplicador opcional de nível da demanda no cenário $s$ |
| $\pi_s$ | Probabilidade ou peso atribuído ao cenário $s$, quando aplicável |

Os parâmetros de demanda devem ser estimados antes da otimização. O otimizador não pode selecionar
variáveis, recalibrar coeficientes ou alterar o suporte da curva em função do resultado financeiro.

## 4. Variáveis de decisão e quantidades derivadas

### 4.1 Variável principal

$$
p_t \in \mathbb{R}_{>0}, \qquad t\in T
$$

$p_t$ é o preço escolhido para o período $t$. Na formulação básica ele é contínuo e estritamente
positivo.

### 4.2 Volume previsto

$$
q_t = D_t(p_t;\theta), \qquad t\in T
$$

$q_t$ é uma quantidade derivada do preço e do contexto conhecido. Ela pode ser representada como
variável auxiliar ligada à curva por uma igualdade, mas não constitui uma decisão independente.

Com cenários, utiliza-se:

$$
q_{ts}=D_{ts}(p_t;\theta_s), \qquad t\in T,\ s\in S
$$

Nesse caso, o mesmo preço é avaliado sob diferentes curvas ou níveis de demanda. O preço não pode
ser escolhido depois que o cenário é observado, salvo se o problema declarar uma política
adaptativa.

### 4.3 Margem prevista

$$
g_t = \left[(1-\tau_t)p_t-c_t\right]q_t
$$

$g_t$ é a margem de contribuição prevista no período. A receita é descontada pelo tributo ad
valorem e pelo custo unitário. Custos fixos ou outras despesas só entram no modelo quando estiverem
explicitamente representados.

## 5. Função de demanda

### 5.1 Representação genérica

A formulação de otimização utiliza uma função conhecida:

$$
D_t:\ [\underline p_t,\overline p_t]\longrightarrow \mathbb{R}_{>0}
$$

Em linguagem natural, para cada período e dentro do suporte autorizado, a curva transforma um preço
em uma previsão positiva de volume.

### 5.2 Especialização para uma curva de potência

Quando a camada estatística selecionar uma regressão log-log com efeitos de contexto, a previsão
pode ser escrita como:

$$
D_t(p;\theta)
=
SF\exp\left(\beta_0 + \beta_p\ln p + x_t^\top\gamma\right)
$$

ou, de forma equivalente,

$$
D_t(p;\theta)=A_t p^{\beta_p},
\qquad
A_t=SF\exp\left(\beta_0+x_t^\top\gamma\right)
$$

Nessa expressão:

- $\beta_0$ é o intercepto na escala logarítmica;
- $\beta_p$ é a elasticidade-preço compartilhada;
- $\gamma$ contém os efeitos dos contextos conhecidos;
- $SF$ é o fator de correção da retransformação;
- $A_t$ reúne os componentes de nível aplicáveis ao período $t$.

Para um cenário multiplicativo:

$$
D_{ts}(p;\theta_s)=k_sD_t(p;\theta)
$$

O multiplicador altera o nível da demanda, mas não altera a elasticidade. Se a incerteza também
envolver elasticidade ou efeitos de calendário, cada cenário deve possuir seu próprio vetor
$\theta_s$.

## 6. Função objetivo

### 6.1 Formulação determinística

O problema central maximiza a margem acumulada no cenário de referência:

$$
\max_{p}
\quad
\sum_{t\in T}
\left[(1-\tau_t)p_t-c_t\right]D_t(p_t;\theta)
$$

Em linguagem natural, o modelo escolhe os preços que produzem a maior soma de margens previstas ao
longo do horizonte. A quantidade vendida em cada período é determinada pela curva de demanda
congelada.

### 6.2 Extensão por valor esperado

Quando existirem cenários com probabilidades defensáveis, a função objetivo pode ser:

$$
\max_{p}
\quad
\sum_{s\in S}\pi_s
\sum_{t\in T}
\left[(1-\tau_t)p_t-c_t\right]D_{ts}(p_t;\theta_s)
$$

Em linguagem natural, maximiza-se a margem média ponderada entre os cenários. Essa formulação exige
que os pesos $\pi_s$ sejam definidos antes de observar a solução.

Uma coleção de cenários sem probabilidades não deve ser transformada automaticamente em valor
esperado. Nesse caso, os cenários servem para sensibilidade ou para uma formulação robusta
explicitamente aprovada.

## 7. Restrições da formulação estrita

### 7.1 Vínculo entre preço e demanda

$$
q_t=D_t(p_t;\theta),
\qquad t\in T
$$

O volume utilizado nas metas e no objetivo deve ser recalculado diretamente pelo artefato da curva.
Não são permitidos volumes copiados ou ajustados manualmente depois da otimização.

### 7.2 Suporte de preço

$$
\underline p_t\le p_t\le\overline p_t,
\qquad t\in T
$$

Cada preço deve permanecer dentro da região na qual a curva foi autorizada para o contexto do
período. Essa restrição evita que o otimizador explore extrapolações estatísticas silenciosas.

### 7.3 Transição entre o histórico e o horizonte

$$
|p_1-p^{\mathrm{ant}}|\le\Delta_0
$$

Equivalentemente:

$$
p_1-p^{\mathrm{ant}}\le\Delta_0
$$

$$
p^{\mathrm{ant}}-p_1\le\Delta_0
$$

Em linguagem natural, a primeira decisão não pode se afastar do último preço conhecido além do
limite de entrada definido pela operação.

### 7.4 Estabilidade entre decisões consecutivas

$$
|p_t-p_{t-1}|\le\Delta_t,
\qquad t\in T\setminus\{1\}
$$

Equivalentemente:

$$
p_t-p_{t-1}\le\Delta_t,
\qquad t\in T\setminus\{1\}
$$

$$
p_{t-1}-p_t\le\Delta_t,
\qquad t\in T\setminus\{1\}
$$

Em linguagem natural, duas decisões adjacentes na sequência operacional não podem diferir além do
limite informado. A instância deve declarar se períodos sem operação interrompem ou não essa
sequência.

### 7.5 Faixa de volume por janela

$$
\underline Q_w
\le
\sum_{t\in T_w}q_t
\le
\overline Q_w,
\qquad w\in W
$$

Em linguagem natural, a soma dos volumes previstos em cada janela precisa permanecer dentro da
faixa contratual correspondente. As janelas são verificadas separadamente; compensar déficit de uma
semana com excesso de outra não é permitido, salvo previsão expressa da regra de negócio.

### 7.6 Incrementos comerciais opcionais

Se preços precisarem respeitar uma grade comercial, pode-se acrescentar:

$$
p_t=\underline p_t+h_tz_t,
\qquad z_t\in\mathbb{Z}_{\ge0}
$$

Em linguagem natural, o preço passa a ser um múltiplo do incremento $h_t$ contado a partir do limite
inferior. Essa extensão transforma o problema contínuo em um problema com variáveis inteiras e não
deve ser ativada sem uma regra comercial explícita.

## 8. Formulação compacta

A formulação determinística estrita pode ser resumida como:

$$
\begin{aligned}
\max_{p,q}\quad
& \sum_{t\in T}\left[(1-\tau_t)p_t-c_t\right]q_t \\
\text{sujeito a}\quad
& q_t=D_t(p_t;\theta), && t\in T, \\
& \underline p_t\le p_t\le\overline p_t, && t\in T, \\
& |p_1-p^{\mathrm{ant}}|\le\Delta_0, & & \\
& |p_t-p_{t-1}|\le\Delta_t, && t\in T\setminus\{1\}, \\
& \underline Q_w\le\sum_{t\in T_w}q_t\le\overline Q_w, && w\in W, \\
& p_t>0,\ q_t>0, && t\in T.
\end{aligned}
$$

Em linguagem natural, escolhem-se preços positivos dentro do suporte, respeitando a estabilidade
na entrada e ao longo do horizonte. A curva converte preços em volumes, cada janela precisa cumprir
sua faixa de volume e a melhor solução é aquela com maior margem total prevista.

## 9. Diagnóstico de viabilidade

Antes de maximizar margem, deve-se verificar se as restrições admitem ao menos uma trajetória.
Defina o conjunto de trajetórias que respeitam suporte e estabilidade:

$$
\mathcal P=
\left\{
p:\
\underline p_t\le p_t\le\overline p_t,
\ |p_1-p^{\mathrm{ant}}|\le\Delta_0,
\ |p_t-p_{t-1}|\le\Delta_t
\right\}
$$

Para cada janela, os envelopes de volume são:

$$
Q_w^{\min}
=
\min_{p\in\mathcal P}
\sum_{t\in T_w}D_t(p_t;\theta)
$$

$$
Q_w^{\max}
=
\max_{p\in\mathcal P}
\sum_{t\in T_w}D_t(p_t;\theta)
$$

Se ocorrer:

$$
Q_w^{\max}<\underline Q_w
$$

ou:

$$
Q_w^{\min}>\overline Q_w,
$$

a formulação é necessariamente infactível. Em linguagem natural, nem a trajetória mais favorável
ao volume consegue entrar na faixa exigida.

A interseção dos envelopes com as faixas semanais é condição necessária, mas não é suficiente em
todo problema possível, porque uma mesma trajetória deve atender simultaneamente a todas as
janelas. Quando o diagnóstico não prova infactibilidade, o problema conjunto ainda precisa ser
resolvido e validado.

Quando todas as curvas são estritamente decrescentes, reduzir preço aumenta volume. Essa propriedade
facilita a construção dos envelopes, mas deve ser confirmada no suporte antes de ser utilizada.

## 10. Recuperação de viabilidade

Uma formulação infactível não deve produzir um plano diário. Primeiro identifica-se uma alteração
operacional mínima; somente depois a margem é maximizada.

### 10.1 Princípio lexicográfico

Para uma medida de relaxação $R(p,r)$, a primeira etapa é:

$$
R^*=\min_{p,r}R(p,r)
$$

sujeita às demais regras que devem permanecer rígidas.

Na segunda etapa:

$$
\max_p
\sum_{t\in T}\left[(1-\tau_t)p_t-c_t\right]D_t(p_t;\theta)
$$

sujeita às restrições do problema e a:

$$
R(p,r)=R^*
$$

Em linguagem natural, o ganho financeiro não pode justificar uma violação maior que a estritamente
necessária para recuperar viabilidade.

### 10.2 Relaxação apenas da transição inicial

Introduz-se $r_0\ge0$:

$$
|p_1-p^{\mathrm{ant}}|\le\Delta_0+r_0
$$

Primeiro minimiza-se $r_0$. Depois, fixa-se $r_0=r_0^*$ e maximiza-se a margem. Todas as transições
internas continuam com seus limites originais.

### 10.3 Relaxação comum das variações de preço

Introduz-se um novo limite comum $\delta\ge0$:

$$
|p_1-p^{\mathrm{ant}}|\le\delta
$$

$$
|p_t-p_{t-1}|\le\delta,
\qquad t\in T\setminus\{1\}
$$

Primeiro minimiza-se $\delta$. Depois, o menor valor viável é congelado e a margem é maximizada.

### 10.4 Folgas de volume

Para diagnosticar falta ou excesso de volume, podem ser introduzidas folgas não negativas:

$$
\sum_{t\in T_w}q_t+s_w^-\ge\underline Q_w
$$

$$
\sum_{t\in T_w}q_t-s_w^+\le\overline Q_w
$$

$$
s_w^-,s_w^+\ge0
$$

$s_w^-$ mede a insuficiência para o limite inferior e $s_w^+$ mede o excesso sobre o limite
superior. Essas folgas devem ser reportadas em suas unidades originais.

Alterações em preço e volume possuem unidades diferentes. Por isso, não se deve somá-las em uma
penalidade única sem uma equivalência operacional previamente aprovada. Quando mais de uma classe
de relaxação for considerada, deve-se reportar uma fronteira de Pareto.

## 11. Premissas do modelo

### 11.1 Premissas estatísticas

1. A função $D_t(p;\theta)$ foi congelada antes da otimização.
2. As características $x_t$ estão disponíveis no momento da decisão.
3. A previsão só é utilizada dentro do suporte autorizado.
4. O volume observado representa adequadamente a demanda ou suas limitações de censura estão
   documentadas.
5. A relação estimada entre preço e volume pode ser usada para decisão somente no grau de
   causalidade sustentado pelo desenho do estudo.
6. A incerteza utilizada pelo otimizador foi produzida pela etapa estatística e não inventada pela
   etapa de decisão.

### 11.2 Premissas econômicas

1. $c_t$ é conhecido ou previsto usando apenas informações disponíveis antes do horizonte.
2. $\tau_t$ incide sobre a receita conforme a base tributária definida no problema.
3. A margem utilizada é de contribuição; custos não representados permanecem fora do objetivo.
4. Não existem efeitos intertemporais de preço sobre demanda, como antecipação, estoque do cliente
   ou canibalização, salvo se incorporados a $D_t$.
5. Não existem efeitos cruzados entre produtos, salvo se a curva e as restrições forem ampliadas.

### 11.3 Premissas operacionais

1. A ordem de $T$ representa corretamente decisões consecutivas para a regra de estabilidade.
2. As metas são verificadas separadamente nas janelas $T_w$.
3. Limites inferiores e superiores de volume possuem força contratual conforme informada.
4. Os limites de preço representam simultaneamente suporte estatístico e admissibilidade comercial,
   ou essas duas faixas são modeladas separadamente.
5. Preços são contínuos, exceto quando a restrição de incremento comercial for ativada.
6. Estoque, capacidade, preço mínimo, orçamento promocional e outras regras ausentes são assumidos
   não limitantes. Se essa premissa não for válida, novas restrições devem ser acrescentadas.

## 12. Contrato de entrada da instância

Uma instância do problema deve fornecer, no mínimo:

| Entrada | Validação necessária |
|---|---|
| Horizonte ordenado $T$ | Datas válidas, ordem inequívoca e regra de predecessor |
| Janelas $T_w$ | Cobertura e associação correta de cada período |
| Curva $D_t$ e parâmetros $\theta$ | Versão, integridade, suporte e vínculo com a incerteza |
| Preço anterior $p^{\mathrm{ant}}$ | Origem e momento de observação |
| Custos $c_t$ | Unidade, método de previsão e ausência de informação futura |
| Tributos $\tau_t$ | Base de incidência e período de validade |
| Suportes $[\underline p_t,\overline p_t]$ | Compatibilidade com o contexto $c(t)$ |
| Limites $\Delta_0$ e $\Delta_t$ | Interpretação operacional das transições |
| Metas e tolerâncias | Conversão correta para $\underline Q_w$ e $\overline Q_w$ |
| Cenários | Origem estatística e, se usadas, probabilidades $\pi_s$ |

Nenhum desses valores deve ser inferido silenciosamente pelo solver. Ausências ou ambiguidades
devem interromper a recomendação ou ser registradas como premissas explícitas aprovadas.

## 13. Saídas obrigatórias

Para uma formulação factível, o resultado deve conter:

1. preços $p_t$ por período;
2. volumes previstos $q_t$ recalculados pela curva;
3. custos, tributos e margens $g_t$ por período;
4. volumes e margens agregados por janela;
5. folga de todas as restrições;
6. restrições ativas;
7. versão e hash dos artefatos estatísticos;
8. status e tolerâncias numéricas do solver;
9. desempenho da política nos cenários de sensibilidade.

Para uma formulação infactível, a saída não deve conter uma agenda apresentada como recomendação.
Ela deve conter os envelopes de viabilidade, déficits ou excessos e as relaxações mínimas analisadas.

## 14. Critérios para escrutínio antes da aplicação

Antes de autorizar uso operacional, devem ser respondidas as seguintes perguntas:

1. A curva de demanda possui interpretação causal suficiente para simular mudanças de preço?
2. A elasticidade e as previsões são plausíveis em todo o suporte utilizado?
3. O preço histórico representa o preço controlado pela operação?
4. As metas constituem limites inferiores, faixas bilaterais ou objetivos flexíveis?
5. A regra de transição usa dias corridos, dias de operação ou decisões consecutivas?
6. Custos e tributos estão completos e disponíveis antes da decisão?
7. Existe granularidade, piso, teto ou aprovação comercial não modelada?
8. Estoque, capacidade e ruptura podem limitar o volume realizado?
9. A política precisa ser factível no cenário de referência ou protegida contra cenários adversos?
10. O ganho estimado justifica a alteração operacional requerida e a incerteza da curva?

Enquanto essas questões não forem resolvidas, a solução matemática deve ser apresentada como
análise condicionada, e não como instrução automática de preço.
