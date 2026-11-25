"""Atualiza os resumos das etapas 2.0 e 3.0/3.1 a partir de resultados persistidos e compatíveis.

Execute após os notebooks. --check verifica defasagem sem escrever arquivos.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDITIVO = "reports/tables/preditivo_diario/"


def read_json(name):
    return json.loads((ROOT / name).read_text())


def read_csv(name):
    with (ROOT / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def number(value, decimals=2):
    value = float(value)
    if not math.isfinite(value):
        return "-"
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def verify_sources():
    """Confere que os resultados foram gerados a partir dos artefatos atuais."""
    model = read_json("models/preditivo_diario/curva_demanda.json")
    planning = read_json("models/otimizacao/entradas_planejamento.json")
    optimization = read_json("data/processed/minerva_otimizacao_resultado.json")
    relaxation = read_json("data/processed/minerva_simulacao_relaxacoes.json")
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
    return model


def render_curve(model):
    candidates = read_csv(PREDITIVO + "comparacao_candidatos.csv")
    holdout = read_csv(PREDITIVO + "metricas_holdout.csv")[0]
    weekly = read_csv(PREDITIVO + "resumo_semanal_holdout.csv")
    benchmark = read_csv(PREDITIVO + "metricas_benchmark_calendario.csv")
    chosen = next(r for r in candidates if r["Código"] == model["selection"]["chosen"])
    baseline = 100 * sum(float(r["WMAPE diário"]) for r in benchmark) / len(benchmark)
    beta = model["coefficients"]["ln_preco"]
    one_percent = 100 * (1.01**beta - 1)
    sexta = 100 * math.exp(model["coefficients"]["contexto_Sexta"])
    forecast = sum(float(r["volume_previsto_kg"]) for r in weekly)
    actual = sum(float(r["volume_real_kg"]) for r in weekly)
    direction = "subestima" if forecast < actual else "superestima"
    supports = "\n".join(
        f"- {context.replace('_', ' ')}: de R$ {number(s['min'])} a R$ {number(s['max'])}/kg."
        for context, s in model["price_support"].items()
    )
    return f"""# Curva de demanda: resumo da etapa 2.0

<!-- Gerado por scripts/update_project_report.py; atualize os artefatos, não os números à mão. -->

Resumo da etapa do notebook 2.0 (`notebooks/2.0-minerva-modelo-preditivo.ipynb`). Ela estima,
por validação cruzada temporal, como o preço e o calendário explicam o volume diário em dias úteis,
e publica a curva usada pelo otimizador em `models/preditivo_diario/curva_demanda.json`.

## Resultado

- Modelo escolhido: `{chosen["Código"]}`, curva de potência com elasticidade compartilhada e um
  nível de demanda por contexto de calendário.
- Elasticidade estimada: `{number(beta, 4)}`. Mantido o calendário, 1% a mais no preço reduz o
  volume previsto em cerca de {number(-one_percent)}%.
- Na sexta, o nível previsto é cerca de {number(sexta, 1)}% do nível de segunda a quinta, no mesmo preço.
- Erro na validação cruzada: WMAPE diário médio de {number(chosen["WMAPE diário (%)"])}%.
- Holdout de dez dias úteis: WMAPE diário de {number(holdout["WMAPE diário (%)"])}% e semanal de
  {number(holdout["WMAPE semanal (%)"])}%. Nas duas semanas, o modelo {direction} o volume total.
- Referência sem preço (média do mesmo dia da semana): WMAPE diário médio de {number(baseline)}%.

## Limites

- A relação é observacional. Ela não mede o efeito causal do preço nem considera estoque,
  promoções, concorrência ou preço de lista.
- Os erros descrevem desempenho observado. Não garantem que as metas semanais serão atingidas.
- A curva vale apenas para dias úteis e para a faixa de preços observada no treino:

{supports}

- O holdout foi usado uma única vez, depois do congelamento da curva. Uma nova avaliação final
  exige observações posteriores.

## Onde estão os detalhes

- `notebooks/2.0-minerva-modelo-preditivo.ipynb`: validação, comparação de
  candidatos, diagnósticos e holdout.
- [Modelo matemático](../modelo-matematico-otimizacao-precos.md): formulação usada pelo otimizador.
- [Referências](../referencias-bibliograficas.md).
"""


def render_optimization(model):
    diagnostic = read_json("data/processed/minerva_diagnostico_infactividade.json")["diagnostic"]
    weeks = diagnostic["weeks"]
    limits = {r["rule"]: r for r in read_csv("reports/tables/relaxacoes/limiares_viabilidade.csv")}
    scenarios = {r["identificacao"]: r for r in read_csv("reports/tables/03_cenarios_gurobi.csv")}
    sensitivity = [
        float(r["margem_reotimizada_rs"])
        for r in read_csv("reports/tables/03_sensibilidade_premissas.csv")
        if r["margem_reotimizada_rs"]
    ]
    lower, upper = weeks["semana_1"]["lower_kg"], weeks["semana_1"]["upper_kg"]
    initial = limits["initial_transition"]
    daily = limits["daily_variation"]
    minimum = limits["tolerance_lower"]
    if limits["tolerance_upper"]["status"] != "no_recovery_in_range":
        raise ValueError("O máximo semanal passou a permitir plano; revise o resumo da etapa 3.")
    return f"""# Otimização de preços: resumo das etapas 3.0 e 3.1

<!-- Gerado por scripts/update_project_report.py; atualize os artefatos, não os números à mão. -->

Resumo das etapas de otimização de referência (`notebooks/3.0-minerva-otimizacao-precos.ipynb`)
e de flexibilizações (`notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`). O planejamento
escolhe um preço por dia útil, de 03 a 14/11/2025, para maximizar a margem prevista pela curva
`{model["model_id"]}`, sujeito às regras da instância.

## Resultado

- **Sem flexibilização não há plano.** O maior volume previsto é {number(weeks["semana_1"]["maximum_reachable_kg"])} kg
  na primeira semana e {number(weeks["semana_2"]["maximum_reachable_kg"])} kg na segunda. O mínimo é
  {number(lower)} kg por semana, e o máximo, {number(upper)} kg.
- **Flexibilizar um limite por vez:**
  - Limite da primeira mudança: é preciso chegar a R$ {number(initial["minimum"])}/kg para existir plano.
    Sem esse limite, a margem prevista é R$ {number(scenarios["R1"]["margem_prevista_rs"])}.
  - Variação entre dias consecutivos: plano a partir de R$ {number(daily["minimum"])}/kg, com margem de
    R$ {number(daily["margem_prevista_rs"])} no menor limite viável.
  - Mínimo semanal: plano a partir de {number(minimum["piso_resultante_kg"])} kg por semana, com margem de
    R$ {number(minimum["margem_prevista_rs"])}.
  - Máximo semanal: sozinho, não permite plano até o limite testado.
- **Referência teórica:** sem as regras operacionais e com extrapolação da faixa de preços, a
  margem máxima é R$ {number(scenarios["R14"]["margem_prevista_rs"])}. Esse caso não cumpre as
  regras originais.
- **Premissas:** com as premissas alteradas (demanda, custo, imposto e elasticidade), a margem
  reotimizada fica entre R$ {number(min(sensitivity))} e R$ {number(max(sensitivity))}.

## Limites

- A alíquota de 7% é hipótese do projeto; a planilha não traz imposto.
- O custo unitário é constante nos dez dias e igual ao do último dia do treino.
- Estoque, capacidade, validade e transferência de compras entre dias não são modelados.
- A margem é prevista pela curva congelada. O realizado não mostra o volume que seria vendido
  nos preços sugeridos, então a comparação com novembro não mede ganho real.
- Um plano ótimo vale para as entradas e tolerâncias da instância; não garante o resultado real.

## Onde estão os detalhes

- `notebooks/3.0-minerva-otimizacao-precos.ipynb`: caso original, uma regra por vez
  e comparação com o holdout.
- `notebooks/3.1-minerva-simulacao-relaxacoes.ipynb`: menores flexibilizações,
  combinações e alternativas comparadas.
- [Modelo matemático](../modelo-matematico-otimizacao-precos.md): formulação das restrições.
"""


def render_reports():
    model = verify_sources()
    return {
        "docs/storytelling/02-curva-de-demanda-modelo.md": render_curve(model),
        "docs/storytelling/03-storytelling-otimizacao-minerva.md": render_optimization(model),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Falha se os resumos estiverem defasados."
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
            "Resumos defasados; execute scripts/update_project_report.py: " + ", ".join(stale)
        )
    if args.check:
        print("Resumos conferidos contra os artefatos atuais.")


if __name__ == "__main__":
    main()
