# Estudo de flexibilizações operacionais

## Objetivo

Quantificar quanto é necessário alterar uma regra para recuperar a viabilidade do planejamento e
como a margem prevista responde às folgas adicionais. O estudo é determinístico e mantém a curva
publicada, seu smearing, o preço anterior observado, o custo do último dia de treino e o imposto.

## Entradas e divisão do trabalho

- `notebooks/3.0-minerva-otimizacao-precos.ipynb`: formulação, caso de referência, diagnóstico,
  combinações de regras mantidas ou removidas, condições iniciais hipotéticas e comparação com o
  holdout. Exporta `models/otimizacao/entradas_planejamento.json` antes da busca de preços.
- `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`: recebe esse artefato e resolve flexibilizações
  graduais, mínimos de viabilidade, combinações parciais e sensibilidade da meta nominal.

O artefato de entradas contém referências e hashes da curva, do treino e das restrições, além de
custo, imposto, preço anterior, regras e calendário. A curva é lida do caminho registrado, com
precisão integral. Se uma fonte mudar, as entradas precisam ser geradas novamente. Não há cópia de
coeficientes entre notebooks nem dependência de variáveis mantidas em memória.

## Limites comerciais recebidos

O estudo recebe `models/otimizacao/limites_flexibilizacoes.json`. O teto para mudanças entre
as decisões do horizonte é R$ 15/kg. Ele não se aplica à primeira mudança em relação ao preço
anterior, que continua sendo examinada separadamente nas faixas declaradas da análise.
A regra de referência da instância permanece R$ 2/kg; R$ 15/kg é o teto da flexibilização admitida.

Buscas de mínimos, curvas, grades e alternativas ficam dentro desse teto. Se uma regra não
recuperar a viabilidade dentro da faixa permitida, o resultado é registrado sem plano ou margem.
A referência financeira também é escolhida somente entre recuperações mínimas admissíveis.
O limite é aplicado na entrada de cada resolução, evitando que uma grade introduza casos acima
do teto. As comparações com regras removidas permanecem referências teóricas separadas.

## Regras examinadas

| Análise | Alteração | Condições mantidas |
|---|---|---|
| Variação interna | Aumentar o limite entre decisões do horizonte | Primeira mudança, faixa semanal e suporte |
| Transição inicial | Aumentar a primeira mudança admitida | Preço anterior real, variação interna, faixa e suporte |
| Piso semanal | Ampliar somente a tolerância inferior | Teto, regras de preço e suporte |
| Teto semanal | Ampliar somente a tolerância superior | Piso, regras de preço e suporte |
| Meta nominal | Deslocar simultaneamente piso e teto | Tolerâncias, regras de preço e suporte |

A tolerância superior também é examinada com a primeira ligação removida, para medir seu efeito
financeiro em uma condição factível. Essa exceção acompanha a identificação de cada ponto.

## Método de solução e mínimos

`src/optimization/relaxation_study.py` aplica alterações ao contrato `PriceProblem` e chama o mesmo
`solve_scenario` de Gurobi utilizado na otimização de referência. Volume, receita e margem são
recalculados pela inferência canônica. A primeira mudança é independente da variação interna.

Um envelope de volume inteiramente fora da faixa certifica inviabilidade. A sobreposição do
envelope com a faixa é somente uma condição necessária: um plano deve ser encontrado e verificado
para confirmar factibilidade. Ausência de solução encontrada não é chamada de inviabilidade.

A bisseção mantém um limite inviável provado e outro com plano factível. A precisão é R$ 0,001/kg
para limites de mudança e 0,000001 para tolerâncias. O mínimo reportado é o lado factível do
intervalo; a margem correspondente é otimizada dentro das tolerâncias do solver.

A bisseção é usada somente em ampliações que geram conjuntos admissíveis aninhados. A meta nominal
é uma sensibilidade: sua redução também abaixa o teto e pode tornar o problema inviável.

## Curvas e combinações

As curvas isoladas mostram os pontos inviáveis, o mínimo calculado e a margem prevista nas folgas
seguintes. A escala financeira é comum nos painéis comparáveis. Reduzir somente o piso não altera
a trajetória de preço alcançável; aumentar o teto não corrige um piso inalcançável.

Três grades cruzam transição inicial e variação interna; variação interna e redução do piso;
transição inicial e redução do piso. A fronteira contém as posições factíveis não dominadas nas
duas alterações operacionais. A margem é reportada separadamente, sem somar grandezas em R$ de
mudança e kg de volume. A fronteira é aproximada pela grade, não um mínimo contínuo certificado.

Os casos repetidos são reutilizados apenas dentro da mesma instância congelada. Cada caso recebe
um identificador que liga condições, status, margem, folgas e plano diário.

## Conjuntos parciais e comparação financeira

A grade conjunta cruza primeira mudança, variação interna, tolerância inferior e tolerância
superior. As quatro famílias são alteradas independentemente, com todas as regras mantidas sob
limites finitos. Meta nominal, preço anterior observado, custo, imposto e curva permanecem fixos.
Os pisos e tetos são verificados em cada semana; cada tolerância modificada é aplicada às duas
semanas, conservando independência entre os lados inferior e superior.

Além da fronteira de viabilidade das grades de dois eixos, a comparação financeira minimiza as
quatro folgas e maximiza a margem, sem somar unidades distintas. Um caso pode ser descartado se
outro exige mudanças não maiores e entrega margem equivalente ou superior, com alguma melhora
estrita. O limitante do solver e equivalência de R$ 0,10 são utilizados na comparação. Cada caso
dominado registra a identificação de uma alternativa que o domina. Casos sem ótimo certificado
não são usados como comparadores financeiros.

As diferenças de margem usam como referência a melhor recuperação mínima isolada admissível, que é uma
configuração factível. Não se atribui margem ao caso original inviável, nem se interpreta a
diferença como ganho realizado sobre a operação histórica.

O quadro de destaques considera: maior margem preservando a faixa semanal original; maior margem
preservando a primeira mudança original; posição central da grade da primeira mudança e teto de variação interna com faixa semanal
mantida; maior margem eficiente com as quatro famílias alteradas; e maior margem da grade. Casos
coincidentes são reunidos. Somente alternativas eficientes que superam a referência factível são
destacadas. A tabela completa de casos eficientes permite examinar os outros compromissos.

As referências sem regras operacionais, com suporte mantido ou extrapolação, são recebidas de
`data/processed/minerva_otimizacao_resultado.json`, com conferência da curva e das entradas usadas.
Elas permanecem comparações teóricas separadas dos conjuntos parciais. A melhor margem encontrada
na grade não é apresentada como a melhor combinação contínua nem como aceitação comercial das
faixas de análise.

## Saídas

- Notebook executado `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`.
- Tabelas em `reports/tables/relaxacoes/`: entradas de cada caso, limiares, curvas, combinações,
  fronteiras, sensibilidade da meta nominal e planos nos mínimos. Incluem também
  `combinacoes_quatro_regras.csv`, `dominancia_financeira.csv`, `alternativas_eficientes.csv`,
  `alternativas.csv`, `planos_alternativas.csv` e `resumo_semanal_alternativas.csv`.
- Figuras em `reports/figures/relaxacoes/`.
- Planos diários em `data/processed/minerva_planos_relaxacoes.csv`.
- Resultado consolidado em `data/processed/minerva_simulacao_relaxacoes.json`.

## Verificação e interpretação

Cada plano precisa respeitar as regras declaradas e o suporte da curva. Curva e entradas devem
permanecer idênticas durante a execução. Os status e os limitantes globais são preservados.
As curvas de flexibilização devem ser compatíveis com a margem ótima não decrescente, considerando
os gaps numéricos. Casos inviáveis não recebem plano diário.

O menor afrouxamento recupera viabilidade; folgas adicionais podem aumentar margem prevista, mas
exigem mudanças operacionais maiores. A escolha comercial depende dos limites aceitáveis informados
pela operação. O estudo não estima efeitos causais, não simula incerteza de demanda e não lê o
holdout para escolher condições. O objetivo financeiro permanece maximizar a margem prevista.
