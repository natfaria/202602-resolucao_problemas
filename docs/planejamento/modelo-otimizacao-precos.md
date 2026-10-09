# Modelo Matemático para Otimização de Preços

## 1. Definição do Problema

Deseja-se determinar uma sequência de preços diários que maximize a margem esperada acumulada ao longo de um horizonte de $T$ dias, sujeita a restrições operacionais de volume, variação de preço e viabilidade técnica da curva de demanda.

A demanda em cada dia é determinada por uma função estimada que depende do preço praticado e do contexto calendário do dia. O custo unitário e a alíquota de tributo sobre receita são conhecidos e constantes.

---

## 2. Conjuntos e Índices

### Conjuntos

- **$\mathcal{T}$**: conjunto de dias do horizonte de decisão. $|\mathcal{T}| = T$ (número de dias).
- **$\mathcal{S}$**: conjunto de semanas dentro do horizonte. $|\mathcal{S}| = S$ (número de semanas).
- **$\mathcal{C}$**: conjunto de contextos calendários (ex.: segunda–quinta, sexta, fim de semana).
- **$\mathcal{T}_s$**: subset de dias pertencentes à semana $s \in \mathcal{S}$.
- **$\mathcal{T}_c$**: subset de dias pertencentes ao contexto $c \in \mathcal{C}$.

### Índices

- **$t \in \mathcal{T}$**: índice de dia.
- **$s \in \mathcal{S}$**: índice de semana.
- **$c \in \mathcal{C}$**: índice de contexto calendário.
- **$c(t)$**: função que retorna o contexto calendário do dia $t$.

---

## 3. Parâmetros

### 3.1 Parâmetros da Curva de Demanda

A curva de demanda foi estimada em etapa anterior (Notebook 2) e é mantida **fixa** nesta etapa.

- **$\hat{\alpha}$**: intercepto da curva em escala logarítmica (parâmetro estimado).
- **$\hat{\beta}$**: elasticidade-preço da demanda, $\hat{\beta} < 0$ (parâmetro estimado).
- **$\hat{\gamma}_c$**: efeito aditivo do contexto $c$ em escala logarítmica, $c \in \mathcal{C}$ (parâmetros estimados).
- **$\hat{\sigma}$**: fator de smearing ou correção de retransformação (adimensional, $\geq 1$).

A forma funcional é:
$$q_t(p_t) = \hat{\sigma} \cdot \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right)$$

### 3.2 Suporte da Curva

Para cada contexto $c \in \mathcal{C}$:

- **$\underline{p}_c$**: preço mínimo observado no período de estimação para o contexto $c$.
- **$\overline{p}_c$**: preço máximo observado no período de estimação para o contexto $c$.

A previsão é válida apenas quando $p_t \in [\underline{p}_{c(t)}, \overline{p}_{c(t)}]$.

### 3.3 Parâmetros Operacionais

- **$T$**: número de dias no horizonte (ex.: 10 dias).
- **$p_0$**: preço praticado no dia anterior ao horizonte (preço de referência inicial).
- **$\Delta_{\max}$**: variação máxima de preço permitida entre dois dias consecutivos (em R$/kg).
- **$V_s$**: meta de volume (em kg) para a semana $s \in \mathcal{S}$.
- **$\text{tol}_s$**: tolerância percentual sobre a meta semanal (adimensional, ex.: 0,30 representa ±30%).

A faixa admissível de volume para a semana $s$ é:
$$V_s (1 - \text{tol}_s) \leq V_{s,\text{real}} \leq V_s (1 + \text{tol}_s)$$

### 3.4 Parâmetros Econômicos

- **$\tau$**: alíquota de imposto sobre receita (adimensional, ex.: 0,07 para 7%).
- **$c_t$**: custo unitário previsto para o dia $t$ (em R$/kg).

---

## 4. Variáveis de Decisão

- **$p_t$**: preço praticado no dia $t$, em R$/kg. $t \in \mathcal{T}$.

**Restrições de domínio:**
$$p_t \in \mathbb{R}_{> 0}, \quad \forall t \in \mathcal{T}$$

---

## 5. Variáveis Derivadas (Quantidades Calculadas)

As seguintes quantidades são determinadas pelas variáveis de decisão e parâmetros:

### 5.1 Demanda

$$q_t(p_t) = \hat{\sigma} \cdot \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right), \quad \forall t \in \mathcal{T}$$

Unidade: kg.

### 5.2 Margem Unitária

$$m_t(p_t) = (1 - \tau) \cdot p_t - c_t, \quad \forall t \in \mathcal{T}$$

Unidade: R$/kg. Representa o lucro esperado por unidade vendida após tributo e custo.

### 5.3 Margem Diária

$$M_t(p_t) = m_t(p_t) \cdot q_t(p_t) = \left[(1 - \tau) \cdot p_t - c_t\right] \cdot q_t(p_t), \quad \forall t \in \mathcal{T}$$

Unidade: R$. Margem total acumulada no dia $t$.

### 5.4 Volume Semanal

$$V_{s,\text{real}} = \sum_{t \in \mathcal{T}_s} q_t(p_t), \quad \forall s \in \mathcal{S}$$

Unidade: kg. Volume total vendido na semana $s$.

---

## 6. Função de Demanda

Conforme estimado em etapa anterior, a relação preço-demanda é uma função potência logarítmica (log-linear):

$$\ln(q_t) = \hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}$$

Retransformando para a escala original com correção de viés (smearing):

$$q_t(p_t) = \hat{\sigma} \cdot \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right)$$

Esta função é:
- **Contínua e diferenciável** em $p_t > 0$.
- **Decrescente** em $p_t$ pois $\hat{\beta} < 0$ (relação normal preço-demanda).
- **Côncava em $\ln(p_t)$** (elasticidade constante).
- **Válida apenas para** $p_t \in [\underline{p}_{c(t)}, \overline{p}_{c(t)}]$ (suporte observado).

---

## 7. Função Objetivo

Maximizar a margem total acumulada ao longo do horizonte:

$$\max_{p_1, \ldots, p_T} \sum_{t \in \mathcal{T}} M_t(p_t) = \sum_{t \in \mathcal{T}} \left[(1 - \tau) \cdot p_t - c_t\right] \cdot q_t(p_t)$$

Expandindo:

$$\max_{p_t} \sum_{t=1}^{T} \left[(1 - \tau) \cdot p_t - c_t\right] \cdot \hat{\sigma} \cdot \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right)$$

Unidade: R$ (valor monetário total esperado).

---

## 8. Restrições

### 8.1 Suporte da Curva de Demanda

Para cada dia, o preço deve permanecer dentro da faixa de preços observada no contexto correspondente:

$$\underline{p}_{c(t)} \leq p_t \leq \overline{p}_{c(t)}, \quad \forall t \in \mathcal{T}$$

**Justificativa:** Previsões fora do suporte representam extrapolação não validada.

### 8.2 Variação Máxima de Preço

Entre dois dias consecutivos, a variação de preço não pode exceder o limite operacional:

$$|p_t - p_{t-1}| \leq \Delta_{\max}, \quad \forall t \in \{2, 3, \ldots, T\}$$

### 8.3 Variação na Fronteira (Preço Inicial)

Na transição do dia anterior (31/10) para o primeiro dia do horizonte:

$$|p_1 - p_0| \leq \Delta_{\max}$$

**Nota:** $p_0$ é um parâmetro (preço observado), não uma variável.

### 8.4 Meta Semanal de Volume

Para cada semana $s \in \mathcal{S}$, o volume acumulado deve estar dentro da faixa de tolerância:

$$V_s (1 - \text{tol}_s) \leq \sum_{t \in \mathcal{T}_s} q_t(p_t) \leq V_s (1 + \text{tol}_s)$$

**Justificativa:** Restrição operacional de planejamento de volume por período.

### 8.5 Positividade de Preço

$$p_t \geq 0, \quad \forall t \in \mathcal{T}$$

Na prática, esta restrição é sempre ativa pois a forma funcional garante $p_t > 0$.

---

## 9. Formulação Compacta

**Problema de otimização não-linear contínuo:**

$$\begin{align}
\max_{p_t} \quad & \sum_{t=1}^{T} \left[(1 - \tau) p_t - c_t\right] \hat{\sigma} \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right) \\
\text{s.a.} \quad & \underline{p}_{c(t)} \leq p_t \leq \overline{p}_{c(t)}, \quad \forall t \in \mathcal{T} \\
& |p_1 - p_0| \leq \Delta_{\max} \\
& |p_t - p_{t-1}| \leq \Delta_{\max}, \quad \forall t \in \{2, \ldots, T\} \\
& V_s (1 - \text{tol}_s) \leq \sum_{t \in \mathcal{T}_s} q_t(p_t) \leq V_s (1 + \text{tol}_s), \quad \forall s \in \mathcal{S} \\
& p_t \geq 0, \quad \forall t \in \mathcal{T}
\end{align}$$

onde $q_t(p_t) = \hat{\sigma} \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t) + \hat{\gamma}_{c(t)}\right)$.

---

## 10. Contrato de Entrada

O modelo requer os seguintes dados como entrada:

### 10.1 Artefatos do Notebook 2 (Curva Estimada)

1. **Parâmetros da curva:**
   - $\hat{\alpha}$, $\hat{\beta}$ (parâmetros principais)
   - $\hat{\gamma}_c$ para cada $c \in \mathcal{C}$ (efeitos de contexto)
   - $\hat{\sigma}$ (fator de smearing)
   - Intervalos de confiança ou matriz de covariância (para análise de sensibilidade)

2. **Suporte validado:**
   - $\underline{p}_c, \overline{p}_c$ para cada contexto $c \in \mathcal{C}$
   - Número de observações por contexto (para avaliação de confiabilidade)

3. **Métricas de diagnóstico:**
   - WMAPE, RMSE, viés em kg (validação temporal)
   - Elasticidade esperada (verifi­cação de sinal e magnitude)

### 10.2 Instância Operacional

1. **Calendário do horizonte:**
   - Datas de cada dia $t \in \mathcal{T}$
   - Contexto $c(t)$ para cada dia (identificação da semana, dia da semana, etc.)
   - Identificação de semanas $\mathcal{T}_s$

2. **Metas e tolerâncias:**
   - $V_s$ (meta em kg para cada semana $s$)
   - $\text{tol}_s$ (tolerância percentual para cada semana $s$)

3. **Restrições de preço:**
   - $p_0$ (preço referência do dia anterior)
   - $\Delta_{\max}$ (variação máxima permitida)

4. **Parâmetros econômicos:**
   - $c_t$ (custo unitário previsto para cada dia $t$)
   - $\tau$ (alíquota de tributo)

### 10.3 Formato Técnico

Dados estruturados em:
- Arquivo JSON com parâmetros da curva e versão do modelo
- Arquivo CSV ou estrutura tabular com calendário, contextos, metas, custos
- Descrição textual de contextos e regras de classificação

---

## 11. Saídas Obrigatórias

### 11.1 Plano de Preços

- **$p_t^*$ para $t \in \{1, 2, \ldots, T\}$:** sequência de preços ótimos recomendados, em R$/kg.
- Formato: tabela com colunas [data, contexto, p_t*, validação suporte]

### 11.2 Quantidades Derivadas da Solução

Para cada dia $t$ com preço ótimo $p_t^*$:

1. **Volume previsto:** $q_t(p_t^*) = \hat{\sigma} \exp\left(\hat{\alpha} + \hat{\beta} \ln(p_t^*) + \hat{\gamma}_{c(t)}\right)$ em kg
2. **Margem unitária:** $m_t(p_t^*) = (1-\tau) p_t^* - c_t$ em R$/kg
3. **Margem diária:** $M_t(p_t^*) = m_t(p_t^*) \cdot q_t(p_t^*)$ em R$
4. **Verificação de suporte:** indicador $\mathbb{1}\{p_t^* \in [\underline{p}_{c(t)}, \overline{p}_{c(t)}]\}$
5. **Verificação de variação:** $|p_t^* - p_{t-1}^*|$ (ou $|p_1^* - p_0|$ para $t=1$)

### 11.3 Agregações por Semana

Para cada semana $s \in \mathcal{S}$:

1. **Volume semanal:** $V_{s,\text{real}} = \sum_{t \in \mathcal{T}_s} q_t(p_t^*)$ em kg
2. **Faixa meta:** $[V_s(1-\text{tol}_s), V_s(1+\text{tol}_s)]$ em kg
3. **Status meta:** atendido ✓ / não-atendido ✗
4. **Margem semanal:** $M_s = \sum_{t \in \mathcal{T}_s} M_t(p_t^*)$ em R$

### 11.4 Resumo Geral

- **Margem total acumulada:** $M_{\text{total}} = \sum_{t=1}^{T} M_t(p_t^*)$ em R$
- **Status de viabilidade:** factível / infactível
- **Restrições ativas:** lista de restrições com folga nula ou próxima de zero
- **Número de iterações do solver:** para referência de convergência

### 11.5 Diagnósticos

- **Valores dos resíduos primal e dual** (para problemas infactíveis)
- **Envelopes de preço alcançáveis** (para análise de sensibilidade)
- **Sensibilidade a perturbações** de parâmetros críticos (custo, meta, variação)

---

## 12. Premissas do Modelo

1. **Curva de demanda congelada:** Os parâmetros $\hat{\alpha}, \hat{\beta}, \hat{\gamma}_c, \hat{\sigma}$ não são reestimados nesta etapa; são recebidos da etapa anterior como constantes.

2. **Forma funcional log-linear:** A função de demanda é determinística (sem ruído estocástico adicional). Incerteza é capturada em análise de sensibilidade com cenários.

3. **Elasticidade constante:** A elasticidade-preço $\hat{\beta}$ é compartilhada por todos os contextos. Interações preço-contexto, se existentes, foram avaliadas e rejeitadas na estimação.

4. **Suporte rígido:** Extrapolação além do suporte $[\underline{p}_{c(t)}, \overline{p}_{c(t)}]$ é proibida; não há relaxação deste limite.

5. **Custos determinísticos:** Os custos unitários $c_t$ são conhecidos (ou previstos) sem incerteza; não variam com quantidade.

6. **Tributo linear:** A alíquota $\tau$ é aplicada sobre toda a receita de forma linear.

7. **Horizontalidade temporal:** Não há desconto de fluxo futuro; a margem total é a soma aritmética.

8. **Independência temporal:** A demanda em um dia não depende de preços ou demandas de dias anteriores (sem dinâmica de estoque ou goodwill).

9. **Contexto calendário conhecido:** O contexto $c(t)$ para cada dia é determinístico e conhecido antecipadamente.

10. **Meta de volume por semana:** As metas são agregadas por semana civil, não por grupos de dias arbitrários.

---

## 13. Propriedades Matemáticas do Problema

### 13.1 Caracterização

- **Tipo:** Otimização não-linear contínua com restrições lineares (em $p_t$) e não-lineares (em $q_t(p_t)$).
- **Classe:** Problema de programação não-linear (NLP).
- **Convexidade:** A função objetivo **não é côncava** em $p_t$ (produto de função côncava com variável). O problema é **não-convexo**.
- **Número de variáveis:** $|T|$ (número de dias).
- **Número de restrições:** $\approx 2|T| + 4|S|$ (suporte, variação, metas semanais).

### 13.2 Implicações

- Soluções locais podem não ser globais.
- Métodos de otimização numérica requerem **múltiplos pontos iniciais** para aumentar chance de encontrar melhor solução.
- Verificação de viabilidade **antes** de otimizar é essencial (problema pode ser infactível).

---

## 14. Diagnóstico de Viabilidade

Antes de resolver o problema de maximização, deve-se testar a viabilidade primal: existe uma sequência de preços que satisfaz todas as restrições?

### 14.1 Teste de Viabilidade Determinística

**Construir envelopes:**

1. **Envelope superior de preço:** máximo preço $\bar{p}_t$ alcançável no dia $t$ respeitando $p_0$, $\Delta_{\max}$ e suporte.
2. **Envelope inferior de preço:** mínimo preço $\underline{p}_t$ alcançável.

Para cada dia $t$:
$$\bar{p}_t = \min\left(\overline{p}_{c(t)}, p_0 + t \cdot \Delta_{\max}\right)$$
$$\underline{p}_t = \max\left(\underline{p}_{c(t)}, p_0 - t \cdot \Delta_{\max}\right)$$

(variação acumulada desde $p_0$)

3. **Volumes correspondentes:**
   - $q_{\max,t} = q_t(\underline{p}_t)$ (preço mínimo → demanda máxima)
   - $q_{\min,t} = q_t(\bar{p}_t)$ (preço máximo → demanda mínima)

4. **Faixa alcançável de volume por semana:**
$$V_{s,\min} = \sum_{t \in \mathcal{T}_s} q_{\min,t}, \quad V_{s,\max} = \sum_{t \in \mathcal{T}_s} q_{\max,t}$$

5. **Teste:** Para cada semana $s$, verificar se:
$$V_{s,\min} \leq V_s(1 + \text{tol}_s) \quad \text{e} \quad V_{s,\max} \geq V_s(1 - \text{tol}_s)$$

**Se verdadeiro para toda semana:** problema é **potencialmente viável**.  
**Se falso para alguma semana:** problema é **infactível com as restrições atuais**.

### 14.2 Identificação de Fontes de Infactibilidade

Se infactível, diagnosticar qual(is) restrição(ões) causa(m):

- **Suporte muito estreito:** $\overline{p}_c - \underline{p}_c$ pequeno → faixa de volume pequena
- **Variação máxima muito restritiva:** $\Delta_{\max}$ pequeno → movimento lento de preço
- **Preço inicial desfavorável:** $p_0$ próximo de um extremo → limita direção de variação
- **Meta incompatível:** $V_s$ fora da zona alcançável mesmo com movimento de preço ótimo

---

## 15. Estratégias de Recuperação de Viabilidade

Se o problema for infactível com as restrições nominais, as seguintes estratégias podem ser avaliadas em ordem de preferência operacional. Cada estratégia é resolvida em **duas etapas**: minimizar a relaxação, depois fixar e maximizar margem.

### 15.1 Estratégia A: Ajustar Preço Inicial

Minimizar o ajuste necessário no preço inicial:

$$\min_{p_0'} |p_0' - p_0|$$
$$\text{s.a. viabilidade primal com } p_0'$$

Depois, fixar $p_0'$ e resolver o problema de maximização original.

**Saída:** novo preço inicial mínimo $p_0'^*$, variação necessária, impacto em margem.

### 15.2 Estratégia B: Aumentar Variação Máxima

Minimizar o aumento necessário em $\Delta_{\max}$:

$$\min_{\Delta'} \Delta' \quad \text{s.a.} \quad \Delta' \geq \Delta_{\max}$$
$$\text{e viabilidade primal com } \Delta'$$

Depois, fixar $\Delta'$ e resolver o problema de maximização.

**Saída:** nova variação mínima $\Delta'^*$, mudança em R$, dias afetados.

### 15.3 Estratégia C: Liberar Apenas Transição Inicial

Aumentar variação apenas na fronteira $|p_1 - p_0|$, mantendo $\Delta_{\max}$ nos pares internos:

$$\min_{\Delta_0} \Delta_0$$
$$\text{s.a.} \quad |p_1 - p_0| \leq \Delta_0, \quad |p_t - p_{t-1}| \leq \Delta_{\max} \text{ para } t > 1$$
$$\text{e viabilidade}$$

Depois maximizar margem com $\Delta_0$ congelado.

**Saída:** variação inicial mínima $\Delta_0^*$, sensibilidade isolada.

### 15.4 Estratégia D: Aumentar Tolerância de Meta

Para cada semana $s$, minimizar a tolerância necessária:

$$\min_{\text{tol}_s'} \text{tol}_s'$$
$$\text{s.a.} \quad V_s(1 - \text{tol}_s') \leq V_{s,\text{real}} \leq V_s(1 + \text{tol}_s')$$
$$\text{e viabilidade com } \text{tol}_s'$$

**Saída:** tolerância nova por semana, desvio máximo em kg de cada meta.

### 15.5 Estratégia E: Reduzir Meta Nominal

Minimizar a redução em meta:

$$\max_{V_s'} V_s'$$
$$\text{s.a.} \quad V_s' \leq V_s$$
$$\text{e viabilidade com } V_s'$$

**Saída:** nova meta máxima $V_s'^*$, redução percentual.

### 15.6 Fronteira de Pareto

Construir combinações não-dominadas de relaxações (ex.: $\Delta' \times \text{tol}_s'$, margem máxima para cada combinação) para visualizar trade-offs operacionais.

---

## 16. Perguntas de Escrutínio

Antes de implementar a solução, responder:

1. **A curva estimada é estável?** (WMAPE aceitável em validação temporal?)
2. **O suporte é suficiente?** (Cobre a região de interesse operacional?)
3. **O problema é viável com restrições nominais?** (Ou já é esperada infactibilidade?)
4. **Qual estratégia de recuperação é aceitável operacionalmente?** (Trade-off margem vs. mudança operacional)
5. **Os custos unitários são confiáveis?** (Ou há incerteza significativa?)
6. **A alíquota de tributo é correta?** (E há cenários de sensibilidade?)
7. **O contexto calendário $c(t)$ está corretamente definido?** (Verifi­cação de amostra)
8. **As metas semanais são realistas?** (Comparação com histórico?)
9. **A variação máxima é exigência operacional ou parâmetro ajustável?** (Grau de flexibilidade)
10. **A solução será implementada tal qual, ou requer ajuste manual?** (Margem de segurança)
11. **Como será feita a validação em produção?** (Métricas de acompanhamento real vs. previsto)
12. **Há plano B se a solução recomendada não der resultado esperado?** (Contingência)
13. **Sensibilidade será executada para quais cenários de demanda, custo e tributo?** (Escopo)
14. **Como a empresa comunicará a decisão de pricing aos clientes?** (Implementação operacional)

---

## 17. Resumo Notacional

| Símbolo | Significado | Unidade |
|---------|-------------|---------|
| $T, S$ | Número de dias, semanas | adimensional |
| $\mathcal{T}, \mathcal{S}, \mathcal{C}$ | Conjuntos de dias, semanas, contextos | — |
| $p_t$ | Preço no dia $t$ | R$/kg |
| $p_0$ | Preço inicial (dia anterior) | R$/kg |
| $q_t(p_t)$ | Demanda no dia $t$ | kg |
| $c_t$ | Custo unitário dia $t$ | R$/kg |
| $\tau$ | Alíquota de tributo | adimensional |
| $\hat{\alpha}, \hat{\beta}, \hat{\gamma}_c$ | Parâmetros curva (estimados) | — |
| $\hat{\sigma}$ | Fator smearing | adimensional |
| $\underline{p}_c, \overline{p}_c$ | Suporte de preço contexto $c$ | R$/kg |
| $V_s$ | Meta volume semana $s$ | kg |
| $\text{tol}_s$ | Tolerância meta semana $s$ | adimensional |
| $\Delta_{\max}$ | Variação máxima preço | R$/kg |
| $m_t(p_t)$ | Margem unitária | R$/kg |
| $M_t(p_t)$ | Margem diária | R$ |
| $M_{\text{total}}$ | Margem total acumulada | R$ |

---

**Documento Versão:** 1.0  
**Data:** 2026-10-05  
**Escopo:** Modelagem matemática formal do problema de otimização de preços  
**Status:** Pronto para implementação em Notebook 3
