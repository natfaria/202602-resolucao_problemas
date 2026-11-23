"""Identidades financeiras e comparação de cenários já planejados com o realizado."""

import numpy as np
import pandas as pd
import pytest

from src.optimization.holdout_comparison import (
    FORECAST_COLUMNS,
    build_actual_daily,
    compare_scenarios,
    summarize_actual,
)


@pytest.fixture
def inputs():
    dates = pd.to_datetime(["2025-11-03", "2025-11-04", "2025-11-10", "2025-11-11"])
    horizon = pd.DataFrame({"data": dates, "semana": ["semana_1"] * 2 + ["semana_2"] * 2})
    holdout = pd.DataFrame(
        {
            "Data": dates,
            "Volume Realizado (kg)": [1.0, 2.0, 3.0, 4.0],
            "Receita Realizada (R$)": [150.0, 300.0, 450.0, 600.0],
            "Custo Realizado (R$)": [70.0, 100.0, 90.0, 110.0],
        }
    )
    daily = pd.DataFrame(
        {
            "data": dates,
            "preco_kg": [160.0, 170.0, 180.0, 190.0],
            "volume_previsto_kg": [2.0] * 4,
            "custo_kg": [100.0] * 4,
            "aliquota_imposto": [0.1] * 4,
        }
    )
    result = {
        "status": "optimal",
        "daily": daily.iloc[::-1],
        "total_margin_rs": 460.0,
        "validation": {"satisfied": True},
    }
    return holdout, horizon, result


def reference(holdout, horizon):
    return build_actual_daily(holdout, horizon, unit_cost=100.0, tax_rate=0.1)


def compare(result, actual):
    return compare_scenarios(
        {"caso": result}, actual, {"caso": {"identificacao": "A1", "descricao": "Plano de teste"}}
    )


def test_actual_margin_uses_registered_cost_and_distinct_standardized_cost(inputs):
    holdout, horizon, _ = inputs
    actual = reference(holdout.iloc[::-1], horizon)
    summary = summarize_actual(actual).set_index("periodo")
    total = summary.loc["total"]
    assert total["volume_real_kg"] == 10
    assert total["receita_real_rs"] == 1500
    assert total["custo_real_rs"] == 370
    assert total["imposto_real_rs"] == 150
    assert total["margem_real_rs"] == 980
    assert total["margem_real_custo_planejamento_rs"] == 350
    assert summary.loc[["semana_1", "semana_2"], "margem_real_rs"].sum() == total["margem_real_rs"]


def test_forecast_is_recalculated_and_totals_use_sums_not_mean_percentages(inputs):
    holdout, horizon, result = inputs
    table = compare(result, reference(holdout, horizon)).set_index("periodo")
    total = table.loc["total"]
    assert total["receita_prevista_rs"] == 1400
    assert total["custo_previsto_rs"] == 800
    assert total["imposto_previsto_rs"] == 140
    assert total["margem_prevista_rs"] == 460
    assert total["diferenca_margem_real_rs"] == -520
    assert total["diferenca_margem_custo_planejamento_rs"] == 110
    assert total["diferenca_margem_real_pct"] == pytest.approx(-520 / 980 * 100)
    assert total["diferenca_receita_pct"] == pytest.approx(-100 / 1500 * 100)
    assert table.loc["semana_1", "margem_prevista_rs"] == 194
    assert (
        table.loc[["semana_1", "semana_2"], "margem_prevista_rs"].sum()
        == total["margem_prevista_rs"]
    )
    assert not np.isclose(
        table.loc[["semana_1", "semana_2"], "diferenca_receita_pct"].mean(),
        total["diferenca_receita_pct"],
    )


def test_infeasible_case_has_actual_reference_but_no_forecast(inputs):
    holdout, horizon, _ = inputs
    result = {"status": "infeasible", "daily": None, "validation": None}
    table = compare(result, reference(holdout, horizon))
    assert len(table) == 3
    assert not table["plano_disponivel"].any()
    assert table[FORECAST_COLUMNS].isna().all().all()
    assert table["diferenca_margem_real_rs"].isna().all()
    assert table["receita_real_rs"].notna().all()


@pytest.mark.parametrize("registered_cost", [135.0, 300.0])
def test_zero_or_negative_real_margin_has_no_percentage(inputs, registered_cost):
    holdout, horizon, result = inputs
    holdout["Custo Realizado (R$)"] = [registered_cost * i for i in [1, 2, 3, 4]]
    table = compare(result, reference(holdout, horizon))
    assert table["diferenca_margem_real_pct"].isna().all()
    assert table["diferenca_margem_real_rs"].notna().all()


@pytest.mark.parametrize("change", ["missing", "duplicate"])
def test_dates_cannot_be_dropped_or_counted_twice(inputs, change):
    holdout, horizon, _ = inputs
    holdout = holdout.iloc[:-1] if change == "missing" else pd.concat([holdout, holdout.iloc[:1]])
    with pytest.raises(ValueError, match="datas|data"):
        reference(holdout, horizon)


@pytest.mark.parametrize("change", ["cost", "tax", "validation", "margin", "dates"])
def test_inconsistent_or_unverified_plan_is_rejected(inputs, change):
    holdout, horizon, result = inputs
    if change == "cost":
        result["daily"] = result["daily"].assign(custo_kg=90.0)
    elif change == "tax":
        result["daily"] = result["daily"].assign(aliquota_imposto=0.2)
    elif change == "validation":
        result["validation"]["satisfied"] = False
    elif change == "margin":
        result["total_margin_rs"] = 999.0
    else:
        result["daily"] = result["daily"].iloc[:-1]
    with pytest.raises(ValueError):
        compare(result, reference(holdout, horizon))
