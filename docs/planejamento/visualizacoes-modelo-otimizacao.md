# Fluxo atual de dados, previsão e decisão

```text
Planilha original
    |
    v
1.0: auditoria, desenvolvimento e holdout separado
    |
    v
2.0.1: comparação temporal e curva para dias úteis
    |  models/preditivo_diario/curva_demanda.json
    v
3.0: modelo econômico, regras, cenários e sensibilidade
    |  models/otimizacao/entradas_planejamento.json
    v
3.1: mínimos e combinações de flexibilizações
```

As etapas recebem arquivos persistidos e verificam suas fontes. O modelo central não é
substituído pelas curvas hipotéticas da sensibilidade. O benchmark é uma referência adicional,
sem alterar a regra de seleção. Veja a [narrativa da curva](../storytelling/curva-de-demanda-modelo-2-0.md)
e os [resultados operacionais](resultados-operacionais.md).
