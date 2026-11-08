"""Atualiza os relatórios da entrega a partir de resultados persistidos e compatíveis.

Execute após os quatro notebooks. --check verifica defasagem sem escrever arquivos.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / name).read_text())


def read_csv(name):
    with (ROOT / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def number(value, decimals=2):
    if value is None or value == "":
        return "-"
    value = float(value)
    if not math.isfinite(value):
        return "-"
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def table(headers, rows):
    def row(values):
        return "| " + " | ".join(str(v).replace("|", "/") for v in values) + " |"

    return "\n".join([row(headers), row(["---"] * len(headers)), *(row(r) for r in rows)])


def render_reports():
    model = read_json("models/preditivo_diario/curva_demanda.json")
    planning = read_json("models/otimizacao/entradas_planejamento.json")
    optimization = read_json("data/processed/minerva_otimizacao_resultado.json")
    relaxation = read_json("data/processed/minerva_simulacao_relaxacoes.json")
    diagnostic = read_json("data/processed/minerva_diagnostico_infactividade.json")["diagnostic"]
    for artifact in [planning, optimization, relaxation]:
        if artifact["model_core_sha256"] != model["model_core_sha256"]:
            raise ValueError("Resultados incompatíveis com o modelo atual; reexecute as etapas.")
    for source in ["model", "training", "restrictions"]:
        path = ROOT / planning[f"{source}_file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != planning[f"{source}_file_sha256"]:
            raise ValueError(f"Fonte {source} alterada; regenere as entradas e os resultados.")
    if optimization["planning_inputs_sha256"] != planning["inputs_sha256"]:
        raise ValueError("A otimização não corresponde às entradas atuais.")
    if relaxation["planning_inputs_sha256"] != planning["inputs_sha256"]:
        raise ValueError("As flexibilizações não correspondem ao arquivo de entradas atual.")
    prefix = "reports/tables/preditivo_diario/"
    candidates = read_csv(prefix + "comparacao_candidatos.csv")
    holdout = read_csv(prefix + "metricas_holdout.csv")[0]
    weekly = read_csv(prefix + "resumo_semanal_holdout.csv")
    folds = read_csv(prefix + "calendario_validacao_cruzada.csv")
    benchmark = read_csv(prefix + "metricas_benchmark_calendario.csv")
    coefficients = read_csv(prefix + "coeficientes_ajuste_final.csv")
    chosen = next(r for r in candidates if r["Código"] == model["selection"]["chosen"])
    baseline = 100 * sum(float(r["WMAPE diário"]) for r in benchmark) / len(benchmark)
    beta = model["coefficients"]["ln_preco"]
    candidate_table = table(
        [
            "Modelo",
            "Parâmetros",
            "WMAPE diário médio (%)",
            "RMSE médio (kg)",
            "Elegível",
            "Zona prática",
        ],
        [
            [
                r["Código"],
                r["Parâmetros"],
                number(r["WMAPE diário (%)"]),
                number(r["RMSE (kg)"]),
                "Sim" if r["Válido"] == "True" else "Não",
                "Sim" if r["Na zona de equivalência"] == "True" else "Não",
            ]
            for r in candidates
        ],
    )
    fold_table = table(
        ["Fold", "Origem", "Ajuste até", "Observações de ajuste", "Dias úteis avaliados"],
        [
            [
                r["Fold"],
                r["Origem"],
                r["Ajuste até"],
                r["Observações de ajuste"],
                r["Dias úteis avaliados"],
            ]
            for r in folds
        ],
    )
    coefficient_table = table(
        ["Termo", "Coeficiente", "IC 95% HC3"],
        [
            [
                r["variavel"],
                number(r["coeficiente"], 4),
                f"{number(r['IC95_inferior'])} a {number(r['IC95_superior'])}",
            ]
            for r in coefficients
        ],
    )
    support_table = table(
        ["Contexto", "n", "Preço mínimo (R$/kg)", "Preço máximo (R$/kg)"],
        [
            [k.replace("_", " "), v["n"], number(v["min"]), number(v["max"])]
            for k, v in model["price_support"].items()
        ],
    )
    holdout_table = table(
        ["Métrica", "Resultado"],
        [[k, number(v) + ("%" if "%" in k else "")] for k, v in holdout.items()],
    )
    weekly_table = table(
        ["Semana", "Observado (kg)", "Previsto (kg)", "Erro do total (%)"],
        [
            [
                r["inicio_semana"],
                number(r["volume_real_kg"]),
                number(r["volume_previsto_kg"]),
                number(r["erro_%"]),
            ]
            for r in weekly
        ],
    )
    example_table = table(
        ["Preço (R$/kg)", "Segunda a quinta (kg/dia)", "Sexta (kg/dia)"],
        [
            [
                number(p),
                *[
                    number(
                        model["smearing_factor"]
                        * math.exp(model["coefficients"]["const"] + gamma)
                        * p**beta
                    )
                    for gamma in [0, model["coefficients"]["contexto_Sexta"]]
                ],
            ]
            for p in [1250, 1275, 1300]
        ],
    )
    story = f"""# Como chegamos à curva de demanda: modelo atual

<!-- Gerado por scripts/update_project_report.py; atualize os artefatos, não os números à mão. -->

Esta narrativa acompanha `notebooks/2.0.1-minerva-modelo-preditivo.ipynb`, que recebe a preparação
`1.0` e publica `models/preditivo_diario/curva_demanda.json`. O caminho deste documento foi mantido
para preservar referências existentes; a metodologia descrita é a atual.

## 1. Resultado e alcance

A regra seleciona `P3`, uma curva de potência com elasticidade compartilhada, três níveis de
calendário no ajuste e quatro coeficientes. O domínio publicado é segunda a sexta.
O WMAPE diário médio nos seis folds é **{number(chosen["WMAPE diário (%)"])}%**. No holdout histórico,
o WMAPE diário é **{number(holdout["WMAPE diário (%)"])}%** e o semanal é **{number(holdout["WMAPE semanal (%)"])}%**.
Esses erros descrevem desempenho observado; não estabelecem suficiência para uso comercial ou
uma garantia de atendimento das metas. Os [resultados operacionais](../planejamento/resultados-operacionais.md)
mostram que o caso com todas as regras originais é inviável.

## 2. Dados, calendário e hipóteses

A planilha contém 86 registros de um produto: 76 observações de desenvolvimento, de 01/08 a
31/10/2025, e dez observações de holdout, de 03/11 a 14/11/2025. Preço médio realizado é receita
sobre volume. Não se assume que esse valor seja um preço de lista único e controlável.
A [exploração dos dados](storytelling-eda-minerva.md) identifica associação negativa entre preço e
volume nos dias úteis e diferenças de nível por dia da semana, sem identificar causalidade.

Médias de preço parecidas entre dias não excluem contribuições do preço: numa curva não linear,
a distribuição inteira importa. Boxplots e testes exploratórios motivam candidatos, sem demonstrar
que grupos têm demanda igual. Um p-valor alto significa ausência de evidência suficiente para
rejeitar a hipótese do teste, não evidência de equivalência. O agrupamento de segunda a quinta é
uma escolha de representação e parcimônia avaliada pela previsão.

**Escopo.** Dez dias úteis são uma delimitação deste estudo. O histórico contém cinco sábados e
cinco domingos; dias sem registro não foram convertidos em volume zero. A cobertura do holdout
não comprova que a operação feche aos fins de semana. Planejá-los exigiria ampliar calendário,
validação e calibração. A curva publicada rejeita esses dias.

## 3. Validação temporal e regra de escolha

O protocolo usa seis origens semanais, ajuste expansivo e horizonte de 14 dias corridos, com dez
dias úteis avaliados por origem. Coeficientes e smearing são calculados apenas no passado daquele
fold; não há atualização dentro do horizonte. Essa separação segue Hyndman e Athanasopoulos
(2021, seção 5.10), nas [referências](../referencias-bibliograficas.md).

**Tabela R2.1.** Calendário da avaliação; fonte: `calendario_validacao_cruzada.csv`.

{fold_table}

![Figura R2.1: calendário dos folds](../assets/figures/preditivo_diario/calendario_folds.png)

**Figura R2.1.** Desenvolvimento usado para ajuste e dez dias úteis futuros por fold. As datas
avaliadas se sobrepõem entre origens; os folds não são amostras independentes. Fonte: notebook `2.0.1`.

A métrica principal é a média dos WMAPEs diários dos seis folds, com igual peso por origem.
Em cada fold, WMAPE é soma dos erros absolutos dividida pelo volume observado total. O resumo
não é um WMAPE único sobre previsões empilhadas. RMSE, viés e erro semanal são complementares.

Entram na zona prática os candidatos elegíveis a até 2 pontos percentuais do menor WMAPE diário
e até 5% do menor RMSE. Exige-se inclinação negativa em todos os folds e previsões positivas.
O desempate usa menos parâmetros e, com o mesmo número, prefere potência. É uma regra
operacional, não um teste estatístico de equivalência. `T1` é somente sensibilidade.

## 4. Comparação e benchmark

**Tabela R2.2.** Painel atual; fonte: `comparacao_candidatos.csv`. `T1` não participa da seleção.

{candidate_table}

![Figura R2.2: comparação dos candidatos](../assets/figures/preditivo_diario/comparacao_candidatos.png)

**Figura R2.2.** WMAPE diário médio e por fold; barras de erro representam desvio-padrão entre
origens, sem interpretação de intervalo de confiança. Fonte: notebook `2.0.1`.

`E1` tem WMAPE ligeiramente menor que `P3`; ambos pertencem à zona prática. `P3` é escolhido
pela interpretação direta da elasticidade, com o mesmo número de parâmetros. A diferença não
estabelece superioridade estatística. Separar a segunda-feira em `P4` não melhora a métrica
principal nesses folds; isso não demonstra igualdade entre os dias.

Como referência adicional, a média histórica do mesmo dia da semana, sem preço, tem WMAPE diário
médio de **{number(baseline)}%**, contra **{number(chosen["WMAPE diário (%)"])}%** de `P3`. O benchmark é
reestimado apenas no passado de cada origem e não altera a regra de seleção declarada. Foi
acrescentado na revisão como comparação descritiva. A diferença é evidência preditiva condicional
a esses folds, sem identificar o efeito causal do preço. Fonte: `metricas_benchmark_calendario.csv`.

## 5. Curva final e interpretação

A especificação log-log é ajustada às 76 observações de desenvolvimento:

`ln(volume) = {number(model["coefficients"]["const"], 4)} + ({number(beta, 4)}) ln(preço) + efeitos de calendário`.

**Tabela R2.3.** Coeficientes e intervalos; fonte: `coeficientes_ajuste_final.csv`.

{coefficient_table}

A elasticidade assinada é $\\beta=d\\ln q/d\\ln p$. Para uma variação finita de 1% no preço,
a mudança prevista é $100(1,01^\\beta-1)$, aproximadamente **{number(100 * (1.01**beta - 1))}%**.
As curvas são paralelas em eixos log-log; nos eixos originais são curvas de potência com níveis
diferentes. No mesmo preço, a sexta tem aproximadamente {number(100 * math.exp(model["coefficients"]["contexto_Sexta"]), 1)}%
do nível estimado de segunda a quinta, sob o fator comum de calibração.

A previsão em kg é a exponencial do preditor multiplicada por **{number(model["smearing_factor"], 7)}**.
O smearing segue Duan (1983) e usa os 66 resíduos de dias úteis, enquanto os coeficientes usam
todas as 76 linhas. Sob heterocedasticidade, um único fator não garante correção condicional exata
em todos os preços e contextos. HC3 segue MacKinnon e White (1985): ajusta a covariância para
inferência, sem alterar os coeficientes ou tornar o ajuste resistente a pontos influentes.

**Tabela R2.4.** Exemplos da curva atual, dentro do suporte observado; fonte: artefato preditivo.

{example_table}

## 6. Diagnósticos e faixa de aplicação

Há evidência de heterocedasticidade no teste Breusch-Pagan com variante studentizada de Koenker
(p aproximadamente 0,0175). Durbin-Watson é aproximadamente 1,83 e os testes de autocorrelação
curta não detectam evidência forte nos lags examinados; isso não garante independência temporal.
A retirada de uma observação por vez preserva o sinal negativo, mas altera a magnitude da elasticidade.

![Figura R2.3: diagnósticos](../assets/figures/preditivo_diario/diagnosticos.png)

**Figura R2.3.** Resíduos, QQ-plot e influência nas 76 observações de ajuste. Os limiares de Cook
sinalizam investigação e não determinam exclusão automática. Fonte: notebook `2.0.1`.

**Tabela R2.5.** Faixas observadas usadas como limites de aplicação; fonte: artefato preditivo.

{support_table}

![Figura R2.4: curvas e dados](../assets/figures/preditivo_diario/curvas_suporte.png)

**Figura R2.4.** Preço em R$/kg e volume em kg/dia nos dois contextos admitidos. Fonte: notebook `2.0.1`.

Permanecer entre os preços mínimo e máximo observados reduz extrapolação, mas não garante
precisão, suporte denso no interior da faixa ou identificação causal. O preço pode responder à
demanda antecipada, descontos por quantidade ou variáveis omitidas. As premissas comerciais do
planejamento precisam ser avaliadas separadamente.

## 7. Holdout histórico e integridade

Na execução atual, fórmula, coeficientes, calibração e suporte são salvos antes de carregar
novembro. O hash antes e depois verifica identidade de conteúdo. Não certifica que versões
anteriores do projeto nunca tenham consultado essas datas. Se o desempenho do holdout orientar
uma revisão, serão necessárias novas observações para uma avaliação final independente.
As hipóteses de calendário foram formuladas no desenvolvimento completo; a comparação é
condicional a esse catálogo, sem validação aninhada de todo o processo exploratório.

**Tabela R2.6.** Avaliação nos dez dias úteis; fonte: `metricas_holdout.csv`.

{holdout_table}

**Tabela R2.7.** Totais semanais; fonte: `resumo_semanal_holdout.csv`.

{weekly_table}

![Figura R2.5: holdout](../assets/figures/preditivo_diario/holdout.png)

**Figura R2.5.** Observado e previsto nos preços efetivamente praticados. Fonte: notebook `2.0.1`.

As duas semanas são subestimadas. O WMAPE semanal coincide com o módulo do viés agregado porque
os erros dos dois totais têm o mesmo sinal; erros diários ainda podem se compensar dentro de
cada semana. A proximidade entre WMAPE médio da validação e do holdout não demonstra estabilidade
futura. O realizado não revela o volume que seria vendido nos preços escolhidos pelo otimizador.

## 8. Controle de versões e artefatos

O otimizador lê `models/preditivo_diario/curva_demanda.json`, de núcleo
`{model["model_core_sha256"]}`. Os artefatos `demand_curve_champion*.json`, seus cenários de incerteza
antigos e o notebook `2.0` anterior não são entradas da trilha atual. Coeficientes idênticos em duas
implementações sobre os mesmos dados demonstram concordância do ajuste, não replicação independente.
Não se combinam multiplicadores de incerteza de núcleos diferentes.

A otimização principal é pontual. Sua nova sensibilidade altera premissas em instâncias independentes,
sem substituir o modelo publicado ou apresentar cenários de estresse como intervalos preditivos.
O [mapa de artefatos](../planejamento/plano-acao-tres-notebooks.md) identifica a origem de cada saída.
Os notebooks numeram suas figuras e tabelas; este relatório usa a sequência própria `R2`.

[Referências completas](../referencias-bibliograficas.md).
"""
    thresholds = read_csv("reports/tables/relaxacoes/limiares_viabilidade.csv")
    limits = read_json("models/otimizacao/limites_flexibilizacoes.json")
    sensitivity = read_csv("reports/tables/03_sensibilidade_premissas.csv")
    alternatives = read_csv("reports/tables/relaxacoes/alternativas.csv")
    stress_table = table(
        [
            "Premissa",
            "Status com ligação original",
            "Margem reotimizada sem ligação (R$)",
            "Margem plano fixo (R$)",
            "Metas do plano fixo",
        ],
        [
            [
                r["premissa"],
                next(
                    a["status"]
                    for a in sensitivity
                    if a["premissa"] == r["premissa"] and a["ligacao_inicial_ativa"] == "True"
                ),
                number(r["margem_reotimizada_rs"]),
                number(r["margem_plano_central_fixo_rs"]),
                "Atendidas" if r["metas_plano_fixo_atendidas"] == "True" else "Descumpridas",
            ]
            for r in sensitivity
            if r["ligacao_inicial_ativa"] == "False"
        ],
    )
    min_rows = []
    for r in thresholds:
        if r["status"] == "bracketed":
            value = number(r["minimum"], 6 if r["rule"] == "tolerance_lower" else 3)
            description = (
                f"Fração de tolerância inferior {value}; piso {number(r['piso_resultante_kg'], 3)} kg"
                if r["rule"] == "tolerance_lower"
                else f"Limite de R$ {value}/kg"
            )
        else:
            description = (
                f"Sem recuperação no intervalo examinado, até {number(r['infeasible_value'])}"
            )
        min_rows.append([r["regra"], description, number(r["margem_prevista_rs"])])
    min_table = table(
        ["Regra alterada isoladamente", "Resultado", "Margem prevista (R$)"], min_rows
    )
    alt_table = table(
        [
            "Alternativa",
            "Condição destacada",
            "Margem prevista (R$)",
            "Diferença da referência factível (R$)",
        ],
        [
            [
                r["alternativa"],
                r["destaques"],
                number(r["margem_prevista_rs"]),
                number(r["diferenca_referencia_factivel_rs"]),
            ]
            for r in alternatives
        ],
    )
    diagnostic_table = table(
        ["Semana", "Piso (kg)", "Máximo alcançável (kg)", "Déficit do piso (kg)"],
        [
            [w, number(r["lower_kg"]), number(r["maximum_reachable_kg"]), number(r["shortage_kg"])]
            for w, r in diagnostic["weeks"].items()
        ],
    )
    results = f"""# Resultados operacionais e limites de interpretação

<!-- Gerado por scripts/update_project_report.py. -->

## 1. O caso original é inviável

Com o preço anterior observado e mudanças de até R$ 2/kg, não é possível alcançar o piso de
115,5 kg em nenhuma das duas semanas. Não há plano recomendado sob todas as regras originais.
A planilha e a Figura 5 do enunciado especificam tolerância de 30%, embora o texto do enunciado
mencione 5%. A referência usa 30%, com sensibilidade separada para 5%.
Veja a [fonte do problema](../referencias/Minerva_Unifesp_ITA.pdf) e a
[formulação atual](modelo-matematico-otimizacao-precos.md).

**Tabela R3.1.** Envelope com regras originais; fonte: `minerva_diagnostico_infactividade.json`.

{diagnostic_table}

## 2. Recuperações isoladas e escolhas operacionais

O estudo mantém a curva central, custo unitário de R$ {number(planning["unit_cost"][0])}/kg,
imposto hipotético de {number(100 * planning["tax_rate"], 0)}% e preço anterior de R$ {number(planning["initial_price"])}/kg.
A variação interna tem teto de R$ {number(limits["daily_variation_ceiling"])}/kg; a primeira mudança é
examinada separadamente. Valores de grade não são aprovação comercial.

**Tabela R3.2.** Mínimos pelo lado factível da bisseção e ausências de recuperação na faixa
examinada; fonte: `limiares_viabilidade.csv`. As tolerâncias são frações, não pontos percentuais.

{min_table}

O mínimo recupera a viabilidade prevista; não define a melhor decisão comercial. O limite de
primeira mudança não é uma nova observação do preço anterior. Diminuir o piso é uma exceção à
meta, enquanto aumentar somente o teto não corrige o volume mínimo inalcançável.
A bisseção conserva limite inviável provado e limite com plano verificado; os valores arredondados
na tabela não substituem a precisão dos arquivos e a verificação das restrições.

![Figura R3.1: curvas de flexibilização](../assets/figures/relaxacoes/curvas.png)

**Figura R3.1.** Alterações isoladas, com preço anterior e demais regras mantidos; unidades em cada
eixo. Margens ausentes representam casos sem plano factível. Fonte: notebook `3.1`.

## 3. Alternativas parciais

**Tabela R3.3.** Destaques da grade eficiente; fonte: `alternativas.csv`. A referência financeira
é a recuperação mínima isolada admissível de maior margem, não o caso original inviável.

{alt_table}

![Figura R3.2: alternativas de margem](../assets/figures/relaxacoes/alternativas_margem.png)

**Figura R3.2.** Margens previstas de configurações com regras diferentes. Os comprimentos das
linhas começam na referência factível. As referências livres são teóricas. Fonte: notebook `3.1`.

As fronteiras são aproximadas pelas grades. A maior margem da grade não é a melhor combinação
contínua certificada. Os mínimos isolados, as configurações de regras e as premissas econômicas
não devem ser misturados sem identificar exatamente o problema resolvido.

## 4. Sensibilidade de demanda, elasticidade, custo e imposto

A análise adicional do notebook `3.0` muda uma premissa por vez: demanda 80%/120%, custo 95%/105%,
imposto 0%/14% e elasticidades nos limites HC3 do desenvolvimento. Ao mudar a elasticidade, o
intercepto gira a curva preservando o volume em R$ 1.300/kg em cada contexto. São hipóteses de
estresse, sem probabilidades ou interpretação de intervalo preditivo conjunto. Os modelos de
cenário recebem hashes próprios; o modelo central publicado permanece intacto.

**Tabela R3.4.** Comparação de reotimização e aplicação do plano central fixo; fonte:
`03_sensibilidade_premissas.csv`. Em todas as avaliações do plano fixo, a primeira ligação está
removida; não se trata de um plano admissível sob a ligação original.

{stress_table}

![Figura R3.3: sensibilidade das premissas](../assets/figures/03_sensibilidade_premissas.png)

**Figura R3.3.** Margem reotimizada e do plano central fixo; volume da primeira semana do plano
fixo comparado com os limites originais. Fonte: notebook `3.0`.

Reotimizar pressupõe conhecer a premissa antes de decidir. A avaliação do plano fixo expõe risco
sem essa adaptação. Uma margem calculada para o plano fixo não significa que suas metas estejam
atendidas, e nenhuma dessas diferenças representa ganho financeiro realizado.

## 5. Limites e próximos dados necessários

O modelo principal é determinístico e usa uma relação observacional. O atendimento previsto das
metas não é garantia probabilística. A alíquota de 7% é hipótese, porque a coluna de imposto não
existe na instância. Custo unitário constante não significa custo fixo contábil. Estoque, capacidade,
validade, descontos por cliente e transferência de compras entre dias não foram modelados.

O horizonte de dez dias úteis é uma delimitação do estudo, sem concluir que fins de semana não
operam. O preço médio realizado é uma aproximação da decisão. A comparação com novembro avalia
previsões nos preços históricos, sem observar o contrafactual dos preços sugeridos.
A decisão comercial exige escolher quais exceções são aceitáveis e avaliar o desempenho com
novas observações. A ordem de salvamento e os hashes verificam integridade na execução;
não demonstram que todas as versões anteriores mantiveram o período de novembro intocado.

[Referências metodológicas](../referencias-bibliograficas.md).
"""
    story = story.replace("../assets/", "../../reports/")
    results = results.replace("../assets/", "../../reports/")
    return {
        "docs/storytelling/curva-de-demanda-modelo-2-0.md": story,
        "docs/planejamento/resultados-operacionais.md": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Falha se os relatórios estiverem defasados."
    )
    args = parser.parse_args()
    stale = []
    for name, content in render_reports().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(name)
        else:
            path.write_text(content)
            print(f"Atualizado: {name}")
    if stale:
        raise SystemExit(
            "Relatórios defasados; execute scripts/update_project_report.py: " + ", ".join(stale)
        )
    if args.check:
        print("Relatórios conferidos contra os artefatos atuais.")


if __name__ == "__main__":
    main()
