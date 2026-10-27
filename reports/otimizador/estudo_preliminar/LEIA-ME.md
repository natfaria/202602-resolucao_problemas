# Estudo preliminar do otimizador

Abra `analise_e_plano_otimizador.html` em um navegador. O relatório contém a descrição do problema, as premissas, os resultados e os gráficos incorporados.

O arquivo `minerva_estudo_otimizador.zip` reúne o relatório, gráficos, tabelas, soluções e scripts reproduzíveis.

## Premissas principais

- Curva de demanda P3: seg–qui, sexta e fim de semana.
- Horizonte: dez datas comerciais, de 03 a 14/11/2025.
- Imposto: 7% sobre a receita.
- Custo de referência: último custo unitário conhecido em 31/10, constante no horizonte.
- Tolerâncias de 5% e 30% analisadas separadamente, devido à divergência entre o texto do PDF e a planilha.
- Condição de abertura tratada explicitamente na análise de viabilidade.

Este é um estudo independente para planejar o otimizador. Os resultados na malha de preços não constituem prova de ótimo contínuo nem de ganho realizado. Os scripts e regras do otimizador preexistente não foram usados como base.
