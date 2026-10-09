# Visualizações e Diagramas — Modelo de Otimização de Preços

Diagramas abstratos em nível conceitual (sem valores numéricos específicos) para auxiliar na compreensão da estrutura do problema, fluxos de dados e relações matemáticas.

---

## 1. Fluxo Geral: Dados → Modelo → Decisão

```
┌─────────────────────┐
│  Notebook 2         │
│  (Curva de Demanda) │
└──────────┬──────────┘
           │
           │ Artefatos:
           │ - demand_curve_champion.json
           │ - Coeficientes (α, β, γ_c)
           │ - Suporte (p_min, p_max) por contexto
           │ - Fator de smearing
           │
           ▼
┌─────────────────────┐
│   Instância         │
│   Operacional       │
│  (Metas, custos,    │
│   restrições)       │
└──────────┬──────────┘
           │
           │ Parâmetros:
           │ - Meta semanal V_s, tolerância
           │ - Variação máxima Δ_max
           │ - Custos c_t
           │ - Imposto τ
           │ - Preço inicial p_0
           │
           ▼
┌─────────────────────────────────┐
│  MODELO MATEMÁTICO              │
│  (Otimização não-linear)        │
│                                 │
│  max Σ_t [(1-τ)p_t - c_t] q_t  │
│  s.a.                           │
│   - Meta semanal                │
│   - Variação de preço           │
│   - Suporte de preço            │
│   - Demanda q_t(p_t)            │
└──────────┬──────────────────────┘
           │
           │ Saída: (p_1*, p_2*, ..., p_10*)
           │
           ▼
┌──────────────────────────────────┐
│  Decisão Operacional             │
│                                  │
│  ✓ Plano de preços diários       │
│  ✓ Volumes esperados             │
│  ✓ Margens esperadas             │
│  ✓ Status de viabilidade         │
│  ✓ Restrições ativas             │
└──────────────────────────────────┘
```

---

## 2. Estrutura do Problema de Otimização

```
                      OTIMIZAÇÃO DE PREÇOS
                    ══════════════════════

                      ┌─────────────────┐
                      │   OBJETIVO      │
                      │                 │
                      │ Maximizar       │
                      │ Margem Total    │
                      └────────┬────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  Margem      │ │  Demanda     │ │  Restrições  │
        │  Unitária    │ │  (não-linear)│ │ (Operacionais)│
        │              │ │              │ │              │
        │ [(1-τ)p - c] │ │ q = f(p, c)  │ │ - Meta      │
        └──────────────┘ └──────────────┘ │ - Variação  │
                                          │ - Suporte   │
                                          └──────────────┘
```

---

## 3. Dinâmica de Preço ao Longo do Horizonte

### Sem restrições (apenas suporte)

```
Preço
  │
  │     p_max (suporte superior)
  │   ╱──────────────────────────╱
  │  │  (zona de preço viável)  │
  │  │ ╱──────────────────────╱  │
  │ ╱──────────────────────╱     │
  ││ p_min (suporte inf.)  │     │
  └┴──────────────────────┴─────▶ Dias
    1  2  3  4  5  6  7  8  9  10

Cada dia pode estar em qualquer ponto da zona viável
(sem custo de transição)
```

### Com restrição de variação (|p_t - p_{t-1}| ≤ Δ)

```
Preço
  │
  │     p_max
  │   ╱──────────────────────────╱
  │  │ ╱╲ ╱╲ ╱╲ ╱╲ ╱╲ ╱╲ ╱╲ ╱╲  │
  │ │╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲╱  ╲│
  │ │ p_min
  └┴──────────────────────────────▶ Dias
    1  2  3  4  5  6  7  8  9  10

Preço forma uma "onda" limitada pela variação máxima
(caminho controlado entre p_0 e p_1)
```

### Com preço inicial fixo (p_0 ← p_{31/10})

```
Preço
  │     p_max
  │   ╱──────────────────────╱
  │  │    ▲ p_0 (preso aqui) │
  │  │   ╱╲  ↙ pode subir até p_0+Δ
  │  │  ╱  ╲ ou descer até p_0-Δ
  │  │ │    ╲
  │  │ │ p_min
  └┴──────────────────────────▶ Dias
   31/10
    ↑
    │ Horizonte de decisão
    1  2  3  4  5  6  7  8  9  10

Primeira transição é limitada por Δ_max
```

---

## 4. Relação entre Preço e Demanda (Curva)

### Curva log-linear (elasticidade constante)

```
Volume (kg)
    ▲
    │       ╲
    │        ╲        (elasticidade = β < 0)
    │         ╲
    │          ╲      ln(q) = α + β ln(p) + γ_c
    │           ╲
    │            ╲
    │             ╲___
    └───────────────────────────▶ Preço (R$/kg)
      p_min      p_ref      p_max
    
    (suporte observado no histórico)

Fora do suporte: extrapolação (NÃO permitida)
Dentro do suporte: previsão confiável
```

### Efeito de calendário (deslocamento vertical)

```
Volume (q)
    ▲
    │     Contexto C₃ ╲
    │      (Alto)      ╲
    │                   ╲
    │   Contexto C₂      ╲  (base)
    │     (Médio)         ╲
    │                      ╲
    │                       ╲ Contexto C₁
    │                        ╲ (Baixo)
    │                         ╲
    └─────────────────────────────▶ Preço
      p_min            p_max

Diferentes contextos deslocam a curva verticalmente
(multiplicação por exp(γ_c))
mas mantêm a mesma elasticidade β
```

---

## 5. Envelopes de Preço e Volume (Diagnóstico)

### Construção de envelopes

```
Preço
  │
  │ p_max ─────────────────────────── (suporte)
  │      │
  │      │ ╱─────────────────────────── (envelope max)
  │      │╱
  │ p_0  ├─ (preço inicial)
  │      │╲
  │      │ ╲─────────────────────────── (envelope min)
  │      │
  │ p_min ─────────────────────────── (suporte)
  │
  └──────────────────────────────────▶ Dias
    0    1  2  3  4  5  6  7  8  9  10

Envelope max: maior preço possível (sobe até p_0+Δ/dia)
Envelope min: menor preço possível (desce até p_0-Δ/dia)
            mas respeitando suporte [p_min, p_max]
```

### Mapeamento em volume

```
Volume (kg)
  ▲                              Semana 1    Semana 2
  │
  │ q_max (usando p_min do envelope)
  │  ╱──╲╱──╲╱──╲╱─────╱──╲╱──╲╱──╲
  │ │    │   │    │    │   │   │   │  (zona alcançável)
  │  ╲──╱╲──╱╲──╱╲────╲──╱╲──╱╲──╱
  │ q_min (usando p_max do envelope)
  │
  │ Meta ─────────────────────── (faixa de meta)
  │ ┌─────────────────────────┐
  │ │                         │
  │ │ Viável se intersecta   │
  │ │                         │
  │ └─────────────────────────┘
  │
  └──────────────────────────────▶ Dias
    1  2  3  4  5  6  7  8  9  10
```

### Cenário de infactibilidade

```
Volume (kg)
  ▲
  │ q_max (zona alcançável de volume)
  │  ╱──╲╱──╲╱──╲╱─────╱──╲╱──╲╱──╲
  │ │    │   │    │     │   │   │   │
  │  ╲──╱╲──╱╲──╱╲─────╲──╱╲──╱╲──╱
  │ q_min
  │
  │                    ╱────────╲
  │                   │  Meta   │ (FORA da zona alcançável!)
  │                   │ faixa   │
  │                    ╲────────╱
  │
  └──────────────────────────────▶ Dias
    1  2  3  4  5  6  7  8  9  10

╳ INFACTÍVEL: não existe sequência de preços que cumpre meta
```

---

## 6. Estrutura de Restrições

```
┌────────────────────────────────────────────────────────────┐
│                   RESTRIÇÕES DO MODELO                     │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. META SEMANAL (por semana s ∈ {1,2}):                  │
│     ═════════════════════════════════════════════════      │
│     V_s(1-tol_s) ≤ Σ_t q_t ≤ V_s(1+tol_s)                │
│                                                             │
│     ┌───────────────────────────────────────┐              │
│     │ Semana 1   │ Meta ± Tolerância        │              │
│     │ Semana 2   │ Meta ± Tolerância        │              │
│     └───────────────────────────────────────┘              │
│                                                             │
│  2. VARIAÇÃO DE PREÇO (por dia t):                        │
│     ══════════════════════════════════════════            │
│     |p_1 - p_0| ≤ Δ_max      (entrada)                   │
│     |p_t - p_{t-1}| ≤ Δ_max  (pares consecutivos)        │
│                                                             │
│     ┌───────────────────────────────────────┐              │
│     │ p_0 ─── Δ_max ─── p_1 ─── Δ_max ─── │              │
│     │         ... ─── Δ_max ─── p_10       │              │
│     └───────────────────────────────────────┘              │
│                                                             │
│  3. SUPORTE DE PREÇO (por contexto c, dia t):             │
│     ════════════════════════════════════════              │
│     p_c^min ≤ p_t ≤ p_c^max    (se contexto c_t = c)     │
│                                                             │
│     ┌───────────────────────────────────────┐              │
│     │ Contexto 1: [p1_min, p1_max]          │              │
│     │ Contexto 2: [p2_min, p2_max]          │              │
│     │ Contexto 3: [p3_min, p3_max]          │              │
│     └───────────────────────────────────────┘              │
│                                                             │
│  4. DEMANDA (cálculo, não restrição livre):               │
│     ═══════════════════════════════════════               │
│     q_t = smear × exp(α̂ + β̂ ln(p_t) + γ̂_{c_t})         │
│                                                             │
│  5. POSITIVIDADE:                                          │
│     ════════════════                                       │
│     q_t ≥ 0, p_t ≥ 0  (sempre satisfeito pela forma)     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 7. Processo de Diagnóstico e Recuperação

### Árvore de Decisão

```
                    ┌─────────────────┐
                    │ VIABILIDADE?    │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
             SIM ▼                        ▼ NÃO
                                    ┌──────────────┐
            Solução                 │ Diagnosticar │
            Ótima                   │ Infactibilid │
            Encontrada              │    ade       │
                                    └──────┬───────┘
                                           │
                          ┌────────────────┼────────────────┐
                          │                │                │
                          ▼                ▼                ▼
                    ┌──────────────┐ ┌─────────────┐ ┌────────────┐
                    │ Suporte      │ │ Variação +  │ │ Meta +     │
                    │ de preço     │ │ Preço       │ │ Tolerância │
                    │ muito        │ │ inicial     │ │ muito      │
                    │ estreito     │ │ limitam     │ │ restritiva │
                    │ limita q     │ │ queda       │ │            │
                    └──────────────┘ └─────────────┘ └────────────┘
                          │                │                │
                          ├────────────────┴────────────────┤
                          │                                 │
                          ▼                                 ▼
                    ┌──────────────────────────────────────────┐
                    │ ESCOLHER ESTRATÉGIA DE RELAXAÇÃO        │
                    ├──────────────────────────────────────────┤
                    │ A. Ajustar preço inicial                │
                    │ B. Aumentar variação diária             │
                    │ C. Liberar só transição inicial         │
                    │ D. Aumentar tolerância de meta          │
                    │ E. Reduzir meta nominal                 │
                    │ (F. Explorar família de curvas)         │
                    └──────────┬───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────────────────┐
                    │ MINIMIZAR RELAXAÇÃO                     │
                    │ (Etapa 1 de cada estratégia)            │
                    └──────────┬───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────────────────┐
                    │ FIXAR RELAXAÇÃO MÍNIMA                 │
                    │ MAXIMIZAR MARGEM                        │
                    │ (Etapa 2 de cada estratégia)            │
                    └──────────┬───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────────────────┐
                    │ FRONTEIRA DE PARETO                     │
                    │ (Visualizar trade-offs)                 │
                    └──────────┬───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────────────────┐
                    │ DECISÃO OPERACIONAL                     │
                    │ (Equipe escolhe qual alternativa        │
                    │  implemente)                            │
                    └──────────────────────────────────────────┘
```

---

## 8. Fronteira de Pareto (Trade-offs)

### Exemplo conceitual de duas dimensões

```
Margem (R$)
  ▲
  │
  │                    ◆
  │                 ◆      ◆
  │              ◆           ◆ ← Fronteira de Pareto
  │           ◆                 ◆
  │        ◆                        ◆
  │     ◆
  │  ◆           (soluções dominadas)
  │
  └────────────────────────────────────────────▶ Variação Δ (R$)
    
Cada ponto ◆: alternativa com relaxação mínima
           em Δ para aquele nível de margem
           
Fronteira: soluções não-dominadas
(aumentar margem requer aumentar Δ)
```

### Exemplo com 3 dimensões

```
              Ajuste
              p_0 (R$)
                 ▲
                 │     ╱╲
                 │    ╱  ╲ Fronteira
                 │   ╱    ╲ Pareto
                 │  ╱  ●   ╲
                 │ ╱ ●   ●   ╲
                 ├───────────────────▶ Variação Δ
                 │                   (R$)
                 │
                 ↙ Tolerância
               Relaxada (%)

Cada ponto representa uma alternativa viável
que minimiza mudança em pelo menos uma dimensão
mantendo margem máxima naquele trade-off
```

---

## 9. Fluxo do Notebook 3 (Otimização)

```
┌─────────────────────────────────────────────────────────┐
│                    NOTEBOOK 3                           │
│             (Otimização de Preços)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ENTRADA:                                              │
│  ├─ demand_curve_champion.json (curva congelada)     │
│  ├─ Instância operacional (metas, custos, etc)       │
│  └─ Premissas (imposto, preço inicial, Δ_max)        │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │ 1. DIAGNÓSTICO DE VIABILIDADE               │   │
│  │    ├─ Construir envelopes de preço          │   │
│  │    ├─ Calcular volume alcançável             │   │
│  │    └─ Verificar interseção com meta          │   │
│  └────────────┬────────────────────────────────┘   │
│               │                                    │
│     ┌─────────┴──────────┐                        │
│     │                    │                        │
│  VIÁVEL                INFACTÍVEL                 │
│     │                    │                        │
│     │            ┌───────▼───────┐               │
│     │            │ 2. IDENTIFICAR│               │
│     │            │ FONTES        │               │
│     │            │ (suporte,     │               │
│     │            │  variação,    │               │
│     │            │  meta, p_0)   │               │
│     │            └───────┬───────┘               │
│     │                    │                        │
│     │            ┌───────▼───────────────────┐  │
│     │            │ 3. IMPLEMENTAR            │  │
│     │            │ ESTRATÉGIAS (A–E)        │  │
│     │            │ Minimizar relaxação       │  │
│     │            │ Depois otimizar           │  │
│     │            └───────┬───────────────────┘  │
│     │                    │                       │
│     ▼                    ▼                       │
│  ┌───────────────────────────────────────────┐  │
│  │ 4. SOLUCIONAR O PROBLEMA                 │  │
│  │    ├─ Usar solver não-linear            │  │
│  │    ├─ Múltiplos pontos iniciais         │  │
│  │    └─ Validar solução                   │  │
│  └────────────┬────────────────────────────┘  │
│               │                               │
│  ┌────────────▼────────────────────────────┐  │
│  │ 5. ANÁLISE DE CENÁRIOS                  │  │
│  │    ├─ Cenário central (ponto-central)   │  │
│  │    ├─ Cenário pessimista (volume baixo) │  │
│  │    ├─ Cenário otimista (volume alto)    │  │
│  │    └─ Variações de imposto e custo      │  │
│  └────────────┬────────────────────────────┘  │
│               │                               │
│  ┌────────────▼────────────────────────────┐  │
│  │ 6. SAÍDAS                               │  │
│  │    ├─ Plano de preços (p_1* ... p_10*) │  │
│  │    ├─ Volumes esperados                │  │
│  │    ├─ Margens esperadas                │  │
│  │    ├─ Diagnóstico de viabilidade       │  │
│  │    ├─ Fronteira de Pareto (se relaxado)│  │
│  │    └─ Visualizações                    │  │
│  └────────────────────────────────────────┘  │
│                                               │
└─────────────────────────────────────────────────┘
```

---

## 10. Análise de Sensibilidade

### Dimensões de sensibilidade

```
                    SOLUÇÃO ÓTIMA
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────────┐ ┌────────────┐ ┌────────────┐
    │  DEMANDA   │ │  CUSTO     │ │  IMPOSTO   │
    │            │ │            │ │            │
    │ ±10%       │ │ ±5%        │ │ 0%, 5%,    │
    │ volume     │ │ R$/kg      │ │ 7%, 10%    │
    │ em cada    │ │ mudança na │ │ alíquota   │
    │ contexto   │ │ previsão   │ │ sobre      │
    │            │ │            │ │ receita    │
    └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
           │              │              │
           │              │              │
           ▼              ▼              ▼
        ┌──────────────────────────────────┐
        │ MATRIZ DE CENÁRIOS               │
        ├──────────────────────────────────┤
        │ 3 cenários de demanda ×          │
        │ 2 premissas de custo ×           │
        │ 4 alíquotas de imposto           │
        │ = 24 combinações                 │
        │                                  │
        │ Para cada: viável? qual margem?  │
        └──────────────────────────────────┘
```

---

## 11. Checklist de Validação Pós-Solução

```
┌─────────────────────────────────────────────────┐
│ AUDITORIA DA SOLUÇÃO                            │
├─────────────────────────────────────────────────┤
│                                                 │
│ ✓ Preços dentro do suporte?                    │
│   p_c^min ≤ p_t ≤ p_c^max (para cada t)       │
│                                                 │
│ ✓ Variação respeita limite?                    │
│   |p_t - p_{t-1}| ≤ Δ_max (para cada par)     │
│                                                 │
│ ✓ Volumes atendem meta?                        │
│   V_s(1-tol_s) ≤ Σ q_t ≤ V_s(1+tol_s)        │
│   (para cada semana s)                         │
│                                                 │
│ ✓ Demanda calculada corretamente?              │
│   q_t = smear × exp(α̂ + β̂ ln(p_t) + γ̂_c)    │
│                                                 │
│ ✓ Margem auditada?                             │
│   m_t = [(1-τ)p_t - c_t] × q_t                │
│   M_total = Σ_t m_t ✓                         │
│                                                 │
│ ✓ Múltiplos pontos iniciais convergem?         │
│   Solução robusta (não preso em mínimo local) │
│                                                 │
│ ✓ Nenhuma variável extrapolou domínio?         │
│   (violação de restrição = solução inválida)   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 12. Comparação de Alternativas (Relatório Final)

### Tabela esquemática de alternativas

```
┌─────────────────────────────────────────────────────────────┐
│                      ALTERNATIVAS VIÁVEIS                   │
├─────┬────────────┬──────────┬──────┬─────────┬──────────────┤
│ Alt.│ Relaxação  │ Margem   │ Vol. │ Semana1 │ Semana 2     │
│     │            │ Esperada │ S1/S2│ ✓/✗     │ ✓/✗          │
├─────┼────────────┼──────────┼──────┼─────────┼──────────────┤
│ 1   │ Nenhuma    │ Infact.  │ ✗/✗  │ ✗       │ ✗            │
│     │ (oficial)  │          │      │         │              │
├─────┼────────────┼──────────┼──────┼─────────┼──────────────┤
│ 2   │ Liberar    │ R$ XXX   │ ✓/✓  │ ✓       │ ✓            │
│     │ Δ → 3,50   │          │      │         │              │
├─────┼────────────┼──────────┼──────┼─────────┼──────────────┤
│ 3   │ Tolerância │ R$ YYY   │ ✓/✓  │ ±45%    │ ±40%         │
│     │ → ±40%     │          │      │         │              │
├─────┼────────────┼──────────┼──────┼─────────┼──────────────┤
│ 4   │ Ajustar p_0│ R$ ZZZ   │ ✓/✓  │ ✓       │ ✓            │
│     │ → 1290     │          │      │         │              │
├─────┼────────────┼──────────┼──────┼─────────┼──────────────┤
│ 5   │ Meta → 150 │ R$ WWW   │ ✓/✓  │ ✓       │ ✓            │
│     │ kg/sem     │          │      │         │              │
└─────┴────────────┴──────────┴──────┴─────────┴──────────────┘

Decisão operacional: qual alternativa a empresa prefere?
(Margem vs. desvio de meta/variação/preço inicial)
```

---

## Conclusão

Estas visualizações apresentam **sem valores numéricos** a lógica do problema:

1. **Fluxo de dados** do Notebook 2 até a decisão.
2. **Estrutura de restrições** e como se comportam.
3. **Envelopes de viabilidade** para diagnóstico.
4. **Processo iterativo** de diagnóstico e recuperação.
5. **Trade-offs** em fronteira de Pareto.
6. **Validação** da solução.

Ao executar o Notebook 3, estas estruturas ganharão **valores concretos e figuras numéricas**, mas a lógica abstrata permanece a mesma para qualquer instância.
