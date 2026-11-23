"""Comparação financeira posterior ao planejamento, sem executar otimização."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

MARGIN_COLUMNS = {
    "identificacao": "Cenário",
    "margem_prevista_rs": "Margem prevista (R$)",
    "margem_real_rs": "Real com custo registrado (R$)",
    "margem_real_custo_planejamento_rs": "Real com custo do planejamento (R$)",
    "diferenca_margem_real_rs": "Diferença do real (R$)",
    "diferenca_margem_real_pct": "Diferença do real (%)",
    "diferenca_margem_custo_planejamento_rs": "Diferença com mesmo custo (R$)",
    "diferenca_margem_custo_planejamento_pct": "Diferença com mesmo custo (%)",
}
REVENUE_VOLUME_COLUMNS = {
    "identificacao": "Cenário",
    "volume_previsto_kg": "Volume previsto (kg)",
    "volume_real_kg": "Volume real (kg)",
    "diferenca_volume_pct": "Diferença de volume (%)",
    "receita_prevista_rs": "Receita prevista (R$)",
    "receita_real_rs": "Receita real (R$)",
    "diferenca_receita_rs": "Diferença de receita (R$)",
    "diferenca_receita_pct": "Diferença de receita (%)",
}
ACTUAL_COLUMNS = [
    "volume_real_kg",
    "receita_real_rs",
    "custo_real_rs",
    "imposto_real_rs",
    "custo_planejamento_sobre_volume_real_rs",
    "margem_real_rs",
    "margem_real_custo_planejamento_rs",
]
FORECAST_COLUMNS = [
    "volume_previsto_kg",
    "receita_prevista_rs",
    "custo_previsto_rs",
    "imposto_previsto_rs",
    "margem_prevista_rs",
]


def build_actual_daily(
    holdout: pd.DataFrame,
    horizon: pd.DataFrame,
    *,
    unit_cost: float,
    tax_rate: float,
) -> pd.DataFrame:
    """Calcula o realizado com custo registrado e com o custo fixo do planejamento."""
    if not np.isfinite(unit_cost) or unit_cost <= 0 or not 0 <= tax_rate < 1:
        raise ValueError("Custo ou imposto inválido para a comparação.")
    calendar = horizon[["data", "semana"]].copy()
    calendar["data"] = pd.to_datetime(calendar["data"])
    actual = holdout.rename(
        columns={
            "Data": "data",
            "Volume Realizado (kg)": "volume_real_kg",
            "Receita Realizada (R$)": "receita_real_rs",
            "Custo Realizado (R$)": "custo_real_rs",
        }
    ).copy()
    if "Produto" in actual and actual["Produto"].nunique() != 1:
        raise ValueError("A comparação exige um único produto.")
    actual["data"] = pd.to_datetime(actual["data"])
    if calendar.empty or calendar["semana"].isna().any():
        raise ValueError("O calendário precisa informar dias e semanas.")
    if calendar["data"].duplicated().any() or actual["data"].duplicated().any():
        raise ValueError("A comparação exige uma observação por data.")
    if set(actual["data"]) != set(calendar["data"]):
        raise ValueError("As datas do teste precisam coincidir com o horizonte planejado.")
    values = actual[["volume_real_kg", "receita_real_rs", "custo_real_rs"]].to_numpy(float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(
            "Volume, receita e custo realizados precisam ser finitos e não negativos."
        )
    actual = (
        calendar.merge(
            actual[["data", "volume_real_kg", "receita_real_rs", "custo_real_rs"]],
            on="data",
            validate="one_to_one",
        )
        .sort_values("data")
        .reset_index(drop=True)
    )
    actual["aliquota_imposto"] = float(tax_rate)
    actual["custo_planejamento_kg"] = float(unit_cost)
    actual["imposto_real_rs"] = tax_rate * actual["receita_real_rs"]
    actual["custo_planejamento_sobre_volume_real_rs"] = unit_cost * actual["volume_real_kg"]
    net_revenue = actual["receita_real_rs"] - actual["imposto_real_rs"]
    actual["margem_real_rs"] = net_revenue - actual["custo_real_rs"]
    actual["margem_real_custo_planejamento_rs"] = (
        net_revenue - actual["custo_planejamento_sobre_volume_real_rs"]
    )
    return actual


def summarize_actual(actual_daily: pd.DataFrame) -> pd.DataFrame:
    """Soma os valores por semana e no horizonte completo, sem médias de percentuais."""
    rows = []
    for period, group in [*actual_daily.groupby("semana", sort=False), ("total", actual_daily)]:
        rows.append(
            {
                "periodo": period,
                "data_inicio": pd.Timestamp(group["data"].min()),
                "data_fim": pd.Timestamp(group["data"].max()),
                "dias": len(group),
                **group[ACTUAL_COLUMNS].sum().to_dict(),
            }
        )
    return pd.DataFrame(rows)


def compare_scenarios(
    results: Mapping[str, Mapping[str, Any]],
    actual_daily: pd.DataFrame,
    scenario_info: Mapping[str, Mapping[str, str]],
) -> pd.DataFrame:
    """Compara planos já definidos; resultados sem plano mantêm previsões ausentes."""
    if set(results) != set(scenario_info):
        raise ValueError("Cada cenário precisa de uma identificação na comparação.")
    actual_daily = actual_daily.copy()
    actual_daily["data"] = pd.to_datetime(actual_daily["data"])
    references = summarize_actual(actual_daily)
    rows = []
    for key, info in scenario_info.items():
        result = results[key]
        daily = result.get("daily")
        if daily is not None:
            if not result.get("validation", {}).get("satisfied", False):
                raise ValueError("A comparação financeira exige planos aprovados na conferência.")
            daily = pd.DataFrame(daily).copy()
            daily["data"] = pd.to_datetime(daily["data"])
            if daily["data"].duplicated().any() or set(daily["data"]) != set(actual_daily["data"]):
                raise ValueError("O plano precisa cobrir exatamente os dias do teste.")
            daily = daily.set_index("data").loc[actual_daily["data"]].reset_index()
            if not np.allclose(daily["custo_kg"], actual_daily["custo_planejamento_kg"]):
                raise ValueError("O custo do plano difere da referência de planejamento.")
            if not np.allclose(daily["aliquota_imposto"], actual_daily["aliquota_imposto"]):
                raise ValueError("O imposto do plano difere da referência do realizado.")
            daily["receita_prevista_rs"] = daily["preco_kg"] * daily["volume_previsto_kg"]
            daily["custo_previsto_rs"] = daily["custo_kg"] * daily["volume_previsto_kg"]
            daily["imposto_previsto_rs"] = daily["aliquota_imposto"] * daily["receita_prevista_rs"]
            daily["margem_prevista_rs"] = (
                daily["receita_prevista_rs"]
                - daily["imposto_previsto_rs"]
                - daily["custo_previsto_rs"]
            )
            if not np.isclose(
                daily["margem_prevista_rs"].sum(), result["total_margin_rs"], atol=0.02, rtol=0
            ):
                raise ValueError("A margem recalculada difere do plano salvo.")
        for reference in references.to_dict(orient="records"):
            period = reference["periodo"]
            record = {
                "cenario": key,
                "identificacao": info["identificacao"],
                "descricao": info["descricao"],
                "status": result["status"],
                "plano_disponivel": daily is not None,
                **reference,
                **dict.fromkeys(FORECAST_COLUMNS, np.nan),
            }
            if daily is not None:
                dates = actual_daily.loc[
                    actual_daily["semana"].eq(period)
                    if period != "total"
                    else np.ones(len(actual_daily), dtype=bool),
                    "data",
                ]
                record.update(
                    daily.loc[daily["data"].isin(dates), FORECAST_COLUMNS].sum().to_dict()
                )
            for forecast, baseline, label in [
                ("volume_previsto_kg", "volume_real_kg", "volume"),
                ("receita_prevista_rs", "receita_real_rs", "receita"),
                ("margem_prevista_rs", "margem_real_rs", "margem_real"),
                (
                    "margem_prevista_rs",
                    "margem_real_custo_planejamento_rs",
                    "margem_custo_planejamento",
                ),
            ]:
                suffix = "kg" if label == "volume" else "rs"
                difference = record[forecast] - record[baseline]
                record[f"diferenca_{label}_{suffix}"] = difference
                record[f"diferenca_{label}_pct"] = (
                    100 * difference / record[baseline] if record[baseline] > 0 else np.nan
                )
            rows.append(record)
    return pd.DataFrame(rows)


def plot_financial_comparison(comparison: pd.DataFrame, *, title: str):
    """Desenha margem e receita por semana e total, com referências reais explícitas."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    periods = comparison["periodo"].drop_duplicates().tolist()
    n_cases = comparison["cenario"].nunique()
    fig, axes = plt.subplots(
        2, len(periods), figsize=(17, max(8, 0.5 * n_cases + 3)), squeeze=False
    )
    for col, period in enumerate(periods):
        panel = comparison.loc[comparison["periodo"].eq(period)]
        label = "Duas semanas" if period == "total" else str(period).replace("semana_", "Semana ")
        for row, (forecast, actual, metric) in enumerate(
            [
                ("margem_prevista_rs", "margem_real_rs", "Margem"),
                ("receita_prevista_rs", "receita_real_rs", "Receita"),
            ]
        ):
            ax = axes[row, col]
            y = np.arange(len(panel))
            values = panel[forecast].to_numpy(float)
            valid = np.isfinite(values)
            ax.barh(y[valid], values[valid], color="#24547a")
            reference = float(panel[actual].iloc[0])
            ax.axvline(reference, color="#a35b20", ls="--", lw=1.8)
            if row == 0:
                ax.axvline(
                    panel["margem_real_custo_planejamento_rs"].iloc[0], color=".3", ls=":", lw=1.8
                )
            ax.set_yticks(y, panel["identificacao"])
            ax.set_ylim(len(panel) - 0.4, -0.6)
            ax.set(title=f"{metric} — {label}", xlabel=f"{metric} (R$)", ylabel="Cenário")
            ax.grid(axis="x", alpha=0.2)
            ax.xaxis.set_major_formatter(
                FuncFormatter(lambda value, _: f"{value:,.0f}".replace(",", "."))
            )
            ax.tick_params(axis="x", labelsize=8, rotation=25)
            left, right = ax.get_xlim()
            for position in y[~valid]:
                ax.text(
                    left + (right - left) * 0.02, position, "Sem plano", va="center", fontsize=8
                )
    fig.suptitle(title, fontsize=14)
    fig.legend(
        handles=[
            Patch(facecolor="#24547a", label="Previsto para o cenário"),
            Line2D(
                [0],
                [0],
                color="#a35b20",
                ls="--",
                label="Real: receita registrada e margem reconstruída",
            ),
            Line2D([0], [0], color=".3", ls=":", label="Real com custo do planejamento (margem)"),
        ],
        loc="lower center",
        ncol=1,
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    return fig
