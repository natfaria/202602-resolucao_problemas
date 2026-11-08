# Referências e critérios de citação

O enunciado e a planilha fornecem as regras e os dados recebidos. Phillips fundamenta a
estimação da relação preço-demanda; as fontes estatísticas específicas fundamentam
retransformação, inferência e avaliação temporal. As tabelas exportadas pelo projeto são
as fontes dos resultados calculados. As escolhas de cenários são premissas próprias.

## Fontes do problema e dos métodos

1. MINERVA FOODS; UNIFESP; ITA. *Otimização de precificação aplicado ao segmento de carnes in natura:
   Desafio Minerva-Unifesp-ITA*. 17 ago. 2026. [Documento recebido](referencias/Minerva_Unifesp_ITA.pdf).
   A planilha recebida é `data/raw/instance_desafio_minerva.xlsx`.
2. PHILLIPS, Robert L. *Pricing and Revenue Optimization*. 2. ed. Stanford: Stanford University
   Press, 2021. cap. 4, especialmente seções 4.2 a 4.4. ISBN 9781503614260, edição digital.
   [Exemplar de referência recebido](referencias/dokumen.pub_pricing-and-revenue-optimization-second-edition-9781503614260.pdf).
3. DUAN, Naihua. Smearing Estimate: A Nonparametric Retransformation Method.
   *Journal of the American Statistical Association*, 78(383), 605–610, 1983.
   [DOI: 10.1080/01621459.1983.10478017](https://doi.org/10.1080/01621459.1983.10478017).
4. MACKINNON, James G.; WHITE, Halbert. Some heteroskedasticity-consistent covariance matrix
   estimators with improved finite sample properties. *Journal of Econometrics*, 29(3),
   305–325, 1985. [DOI: 10.1016/0304-4076(85)90158-7](https://doi.org/10.1016/0304-4076(85)90158-7).
5. HYNDMAN, Rob J.; ATHANASOPOULOS, George. *Forecasting: Principles and Practice*. 3. ed.
   Melbourne: OTexts, 2021. cap. 5, seções 5.2 e 5.10.
   [Benchmarks e validação temporal](https://otexts.com/fpp3/toolbox.html).
6. GUROBI OPTIMIZATION, LLC. *Gurobi Optimizer Reference Manual*. Versão 13.0.
   [Nonlinear Constraints](https://docs.gurobi.com/projects/optimizer/en/current/features/nonlinear.html).
7. STATSMODELS. Documentação de `het_breuschpagan` e `get_robustcov_results`.
   A chamada padrão do teste de heterocedasticidade usa a versão studentizada de Koenker
   (`robust=True`); o nome Breusch-Pagan no projeto inclui essa variante.
   [Implementação do teste](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_breuschpagan.html).

## Uso das referências

A revisão de Mullapudi, *Pricing Optimization across Domains: A Comparative Review* (2025), é
citada pelo próprio enunciado como contexto. Como não sustenta uma discussão comparativa na
entrega atual, não é usada como referência metodológica do projeto. Seu PDF recebido é preservado.

Não se atribuem a essas fontes a alíquota hipotética de 7%, os limites de estresse, a decisão
de agrupar dias ou os resultados numéricos próprios. Esses itens são premissas ou cálculos do projeto.
A numeração de figuras e tabelas é local a cada notebook: `1`, `2`, `3` e `3.1` são os prefixos;
os relatórios textuais indicam quando usam uma sequência própria.
