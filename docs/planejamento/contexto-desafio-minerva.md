# Contexto do desafio Minerva

Este documento resume o enunciado do Desafio Minerva-Unifesp-ITA e mostra como cada parte está
implementada no projeto. Ele não substitui o enunciado nem os notebooks; serve de porta de entrada
para lê-los.

- **Enunciado:** `docs/referencias/Minerva_Unifesp_ITA.pdf`, "Otimização de precificação aplicado ao
  segmento de carnes in natura", Minerva Foods, 17/08/2026.
- **Estado descrito:** repositório em 24/11/2026, último commit `c2dc4bd` (23/11/2026). Os números
  vêm dos notebooks executados e das tabelas em `reports/tables/`.

## 1. O problema em uma frase

Para o `Produto_A`, escolher **um preço por dia** nos dez dias úteis de 03 a 14/11/2025 que
**maximize a margem total prevista**, respeitando as metas semanais de volume, o limite de variação
de preço entre dias consecutivos e a curva que relaciona preço e volume.

## 2. O que o enunciado pede

| Seção do PDF | Conteúdo | Implicação para o projeto |
|---|---|---|
| 0.1 Introdução | Preço ótimo é tratado com programação matemática, aprendizado de máquina ou heurísticas. Há dois desafios: definir o percentual de variação e entender a elasticidade preço-demanda. | O projeto combina dados e programação matemática (Gurobi). |
| 0.2 Dados | Vendas têm picos (início do mês, segunda-feira, promoções, feriados) e tendem a cair ao longo da semana. A curva é do tipo `volume = A / preço^B`. | A curva é ajustada em log-log, com elasticidade `B`. |
| 0.3 Definição | Horizonte de 2 semanas, preço diário por SKU, maximização da margem total. Restrições: (1) metas semanais com tolerância; (2) limite de variação de preço entre dias consecutivos; (3) respeitar a função volume-preço. | Ver as seções 4 e 5. |
| 0.3 Incertezas | Demanda do dia não é conhecida; a disposição a pagar não é conhecida; simplificações da curva podem levar a conclusões equivocadas. | Tratado nos riscos (seção 7). |
| 0.4 Arquivo de dados | Figura 3: histórico de 01/08 a 31/10/2025 com produto, data, volume, receita, custo e imposto realizados. Figura 4: teste de 03/11 a 14/11/2025. Figura 5: meta, tolerância e variação máxima por semana. | Ver a seção 3. |
| 0.5 Ferramenta | Os tomadores de decisão precisam de uma ferramenta. Entradas: preço anterior, variação diária, limites semanais de volume e quais restrições relaxar. Saída: série diária de preços, volumes e margens, em tabela e gráfico. | **Ainda não existe como interface** (seção 7). |
| Entregáveis | Como definir a relação volume-preço; solução técnica recomendada (tratamento de dados e modelos finais); impacto da meta semanal; impacto da variação de preço entre dias. | Ver a seção 4. |
| Estratégias | Dados (regressões), programação matemática, simulação ou combinação. | O projeto usa as quatro. |

Referências citadas no enunciado: Mullapudi (2025), revisão de precificação em outros setores; e
Phillips (2021), *Pricing and Revenue Optimization*, 2. ed.

## 3. Dados: enunciado e planilha

A planilha recebida é `data/raw/instance_desafio_minerva.xlsx`. Ela não é modificada pelo projeto.

| Item | Enunciado | Planilha recebida | Tratamento no projeto |
|---|---|---|---|
| Histórico | 01/08 a 31/10/2025 | aba `base_dados`, 86 linhas, 1 produto | 76 linhas de desenvolvimento |
| Holdout | 03/11 a 14/11/2025 | as 10 linhas posteriores ao corte | isolado; usado uma única vez, no fim |
| Imposto realizado | Coluna na Figura 3 | **não existe** na planilha | premissa de 7% sobre a receita |
| Nulos, duplicatas, valores não positivos | não mencionado | 0, 0 e 0 | auditado no notebook 1.0; nenhuma linha removida |
| Meta semanal | Figura 5 | 165 kg por semana | usada como referência da faixa |
| Tolerância | texto: 5% | 30% | usa 30%; 5% entra como sensibilidade |
| Variação máxima entre dias | Figura 5: R$ 2 | R$ 2 nas duas semanas | aplicada entre decisões consecutivas |

Dois detalhes de interpretação:

- A sexta-feira e a segunda-feira seguinte são tratadas como dias consecutivos.
- O horizonte cobre segunda a sexta. O enunciado não exclui fins de semana, mas o histórico tem
  poucas vendas em sábados e domingos (5 registros em cada dia), então o projeto os deixa fora do
  planejamento.

Tratamento inicial (notebook 1.0): validação do esquema, conversão de tipos, verificação de
duplicatas e de valores não positivos, corte temporal entre desenvolvimento e holdout, e variáveis
derivadas. Preço é receita dividida pelo volume; custo unitário é custo dividido pelo volume. Não
houve imputação nem remoção de linhas.

## 4. Como o projeto responde ao enunciado

```
1.0 EDA e preparação  →  2.0.1 Curva preditiva  →  3.0 Otimização de referência  →  3.1 Flexibilizações
```

| Etapa | Notebook | Pergunta que responde | Saídas principais |
|---|---|---|---|
| Preparação e EDA | `notebooks/1.0-minerva-eda-preparacao.ipynb` | Os dados são confiáveis? Como variam preço, volume e calendário? | `data/processed/minerva_modelagem_treino.csv`, `data/interim/` |
| Curva preditiva | `notebooks/2.0.1-minerva-modelo-preditivo.ipynb` | Como preço e calendário explicam o volume? | `models/preditivo_diario/curva_demanda.json` |
| Otimização de referência | `notebooks/3.0-minerva-otimizacao-precos.ipynb` | Quais regras impedem um plano? Qual plano maximiza a margem sob cada alteração? | `models/otimizacao/entradas_planejamento.json`, `data/processed/minerva_otimizacao_resultado.json`, `data/processed/minerva_plano_precos.csv` |
| Flexibilizações | `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb` | Quanto cada regra precisa ser relaxada? O que acontece com combinações? | `reports/tables/relaxacoes/`, `data/processed/minerva_simulacao_relaxacoes.json` |

Código-fonte:

- `src/modeling/`: curva de demanda, ajuste, smearing e benchmarks.
- `src/optimization/`: contrato de entradas (`planning_inputs.py`), problema e viabilidade
  (`price_schedule.py`), solver Gurobi (`gurobi_solver.py`), estudo de relaxações, comparação com o
  holdout e a ferramenta de planejamento (`ferramenta.py`).
- `src/app/ferramenta_precos.py`: interface Streamlit da ferramenta do item 0.5. Execução a partir da
  raiz: `.venv/bin/python -m streamlit run src/app/ferramenta_precos.py`. Os logos ficam em
  `src/app/assets/`. A lógica de planejamento fica em `src/optimization/ferramenta.py`; a interface
  só chama essas funções.

## Organização do repositório

O projeto foi implementado usando o **cookiecutter-data-science**: `Makefile` com alvos como
`create_environment` e `data`, `src/config.py`, `data/` dividido em `raw`, `interim` e `processed`,
e pastas `models/`, `notebooks/`, `reports/` e `docs/`.

Convenção adotada: `src/` é o pacote Python que contém o produto (lógica e interface). `notebooks/`
é exploração e relatório; `scripts/` guarda utilitários de geração de relatórios; `tests/` valida o
código de `src/`.

### Curva escolhida (notebook 2.0.1)

Modelo `P3-power-grouped-dias-uteis`. Para segunda a quinta, o volume previsto é:

`volume = 1,0912 × exp(91,59 − 12,36 × ln(preço))`

Na sexta, o nível cai por um fator `exp(−1,34)`. O coeficiente de fim de semana existe no artefato,
mas não é usado no horizonte. Os coeficientes foram ajustados com 76 observações, e o smearing usa
os resíduos de 66 dias úteis.

A escolha veio de validação cruzada temporal com seis origens semanais e horizonte de duas semanas.
Foram comparados sete candidatos; um oitavo, com tendência, serviu só de sensibilidade. O critério
principal é o WMAPE diário: 36,9% em média na validação e 37,2% no holdout.

## 5. Premissas usadas na otimização

| Premissa | Valor | Origem |
|---|---|---|
| Custo unitário | R$ 1.010,446838/kg | custo ÷ volume de 31/10/2025, mantido nos 10 dias |
| Preço anterior | R$ 1.318,919594/kg | receita ÷ volume de 31/10/2025 |
| Imposto | 7% sobre a receita | premissa do projeto; não há coluna na planilha |
| Dias planejados | segunda a sexta (10 dias) | escolha do projeto |
| Meta semanal | 165 kg, com tolerância de 30% → faixa de 115,5 a 214,5 kg | planilha |
| Variação máxima entre dias | R$ 2/kg | planilha |
| Faixa de preço | R$ 1.201,63 a 1.352,42 (seg–qui); R$ 1.208,37 a 1.365,49 (sexta) | suporte observado no treino |
| Solver | Gurobi 13.0.3; 30 s por resolução; gap relativo de 1e-6 | notebook 3.0 |
| Holdout | lido uma única vez, depois de salvos os planos | protocolo do projeto |

## 6. Resultados atuais (notebook 3.0)

1. **As regras originais são inviáveis.** O maior volume previsto é 76,99 kg na semana 1 e 84,62 kg
   na semana 2, contra um mínimo de 115,5 kg. Com tolerância de 5%, o mínimo sobe para 156,75 kg e o
   caso continua inviável.
2. **Uma regra por vez:**
   - Reduzir o mínimo semanal: há plano a partir de cerca de 76,99 kg.
   - Ampliar a primeira mudança: há plano a partir de cerca de R$ 44,39/kg de limite.
   - Ampliar as mudanças entre dias até R$ 15/kg: continua inviável.
   - Ampliar o máximo semanal: continua inviável, porque o problema é o mínimo.
   - Permitir só extrapolação da faixa de preço: continua inviável.
3. **Plano selecionado** (sem limite na primeira mudança; demais regras mantidas):
   - preço de R$ 1.209,11/kg nos dez dias;
   - volume de 50,33 kg/dia de segunda a quinta e 13,19 kg na sexta; 214,5 kg por semana, com o teto
     semanal ativo;
   - margem prevista de R$ 48.917,58 nas duas semanas;
   - salto de R$ 109,81/kg (cerca de 8,3%) já no primeiro dia.
4. **Referência teórica sem regras operacionais** (com extrapolação): preço de R$ 1.182,11/kg e
   margem prevista de R$ 50.432,89. Essa referência fica fora da faixa observada e não é um plano
   aplicável.
5. **Holdout:** os planos foram congelados antes da leitura. A comparação mostra previsão contra
   realizado. O realizado teve 74,24 kg na semana 1 e 109,39 kg na semana 2, abaixo do mínimo nas duas
   semanas. A comparação não mede o volume que seria vendido nos preços sugeridos.
6. **Testes:** `.venv/bin/python -m pytest -q` passou com 92 testes, em 24/11/2026.

## 7. Riscos e pendências

1. **A ferramenta do item 0.5 existe, com escopo limitado.** A interface Streamlit recebe preço
   anterior, limites da primeira mudança e entre dias, meta, tolerâncias, custo, imposto e as regras
   a relaxar. Devolve plano diário, resumo semanal, gráficos e CSV. O horizonte é fixo (03/11 a
   14/11/2025), herdado das entradas congeladas, e a curva não é reajustada.
2. **Links da documentação corrigidos.** Os storytelling usam os nomes `01-`, `02-` e `03-`, e
   `mkdocs build --strict` volta a passar.
3. **O plano selecionado depende de uma regra não original.** Ele começa com um salto de
   R$ 109,81/kg, que viola a regra de variação máxima. O teto de R$ 120/kg para a primeira mudança foi
   definido no notebook; o `models/otimizacao/limites_flexibilizacoes.json` deixa esse teto nulo.
4. **A elasticidade é alta e depende de um trecho do histórico.** O `β` estimado é −12,36. O exemplo
   do enunciado (2% de preço gera 5% de volume) corresponde a cerca de −2,5. Segundo a EDA, o período
   de 7 a 16/10 concentra volumes altos com preços baixos. O preço de R$ 1.209 está nessa região:
   as cinco observações de segunda a quinta entre R$ 1.200 e R$ 1.220 são todas de 8 a 16/10. O
   volume previsto (50 kg/dia) está dentro do observado, não é extrapolação, mas depende desse
   episódio.
5. **Erro diário alto.** O WMAPE diário fica perto de 37%. A margem prevista é condicional à curva e
   deve ser lida como uma estimativa, não como resultado esperado.
6. **Imposto é premissa.** O enunciado mostra a coluna na Figura 3, mas a planilha não a contém.
7. **Tolerância divergente.** O texto diz 5%, a planilha diz 30%. O projeto usa 30% e mostra o caso
   de 5% como sensibilidade.

## 8. Ordem de leitura sugerida

1. O enunciado, `docs/referencias/Minerva_Unifesp_ITA.pdf`, seções 0.3 e 0.5.
2. Este documento.
3. Os notebooks 1.0, 2.0.1 e 3.0, nessa ordem.
4. A formulação em [modelo-matematico-otimizacao-precos.md](modelo-matematico-otimizacao-precos.md).
5. O notebook 3.1, para as flexibilizações.

Para reproduzir os testes:

```bash
.venv/bin/python -m pytest -q
```
