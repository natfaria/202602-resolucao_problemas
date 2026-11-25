# Exploração dos dados: resumo da etapa 1.0

Resumo da etapa do notebook `notebooks/1.0-minerva-eda-preparacao.ipynb`. Ela valida a planilha,
separa o desenvolvimento do holdout, reconstrói as variáveis de decisão e examina se a base sustenta
uma curva de demanda. A análise completa, com tabelas e gráficos, está no notebook.

## Base e separação temporal

- A planilha tem 86 registros de um produto. Desses, 76 vão para o desenvolvimento, de 01/08 a
  31/10/2025, e 10 ficam isolados como holdout, de 03 a 14/11/2025.
- O holdout não é examinado nesta etapa. Ele só é usado depois do congelamento da curva.
- Preço por kg é a receita dividida pelo volume. Custo por kg é o custo dividido pelo volume.

## Principais achados

- A base é utilizável: não há dados ausentes, duplicados ou inválidos nas 76 observações de
  desenvolvimento.
- Há variação de preço suficiente, mas as conclusões valem apenas para a faixa observada de
  aproximadamente R$ 1.189 a R$ 1.365/kg.
- Nos dias úteis, preço e volume têm associação negativa: preços maiores aparecem com volumes menores.
- O dia da semana é a principal variável de contexto. Mesmo controlando o preço, ele melhora bastante
  o ajuste.
- Mês, quinzena e semana do mês não mostram contribuição clara depois do controle pelo preço.
- Os fins de semana têm poucos dados: cinco sábados e cinco domingos não bastam para estimar
  elasticidades específicas com segurança.
- Preço, calendário e tempo estão parcialmente confundidos. Em outubro, preços baixos coincidem com
  volumes altos.
- Os pontos extremos não devem ser removidos automaticamente, porque vários pertencem a um episódio
  temporal coerente de outubro.
- Nenhum modelo foi escolhido nesta etapa. A hipótese inicial mais defensável é uma elasticidade
  compartilhada, com níveis diferentes de demanda por contexto de calendário. Ela é testada no
  [resumo da curva de demanda](02-curva-de-demanda-modelo.md).

## Limites

- A relação é observacional. Estoque, promoções, concorrência, clima e preço de lista não estão na base.
- Dez dias úteis são uma delimitação do estudo. A ausência de vendas nos fins de semana não foi
  convertida em volume zero, e isso não prova que a operação fecha nesses dias.
- As hipóteses de calendário foram formuladas no desenvolvimento completo. Não há validação aninhada
  de todo o processo exploratório.

## Referências

As referências metodológicas estão em [referências](../referencias-bibliograficas.md).
