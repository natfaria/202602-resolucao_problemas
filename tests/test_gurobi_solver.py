"""Verificações por identidade financeira, viabilidade e soluções analíticas."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("gurobipy")

from src.modeling.demand_curve import load_artifact, predict_volume_from_artifact
from src.optimization.gurobi_solver import Scenario, solve_scenario
from src.optimization.price_schedule import problem_from_frames

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def problem():
    training = pd.read_csv(
        ROOT / "data/processed/minerva_modelagem_treino.csv", parse_dates=["data"]
    ).sort_values("data")
    return problem_from_frames(
        load_artifact(ROOT / "models/preditivo/curva_demanda.json"),
        pd.read_csv(ROOT / "data/interim/minerva_restricoes.csv"),
        unit_cost=float(training.iloc[-1]["custo_kg"]),
        initial_price=float(training.iloc[-1]["preco_kg"]),
    )


def test_historical_initial_condition_has_no_feasible_plan(problem):
    result = solve_scenario(problem, Scenario("Condições operacionais"))
    assert result["status"] == "infeasible"
    assert result["status_code"] == 3
    assert result["daily"] is None
    assert result["weekly"] is None


@pytest.fixture(scope="module")
def free_initial_result(problem):
    return solve_scenario(problem, Scenario("Entrada livre", enforce_initial_anchor=False))


def test_unanchored_policy_matches_weekly_analytic_solution(problem, free_initial_result):
    result = free_initial_result
    assert result["status"] == "optimal"
    assert result["validation"]["satisfied"]
    assert result["gap"] <= 1e-6
    qref = sum(
        predict_volume_from_artifact(problem.artifact, 1300, day) for day in problem.weekdays[:5]
    )
    beta = problem.artifact["coefficients"]["ln_preco"]
    expected_price = 1300 * (214.5 / qref) ** (1 / beta)
    assert result["daily"]["preco_kg"].to_numpy() == pytest.approx(expected_price, abs=0.02)
    assert result["weekly"]["volume_previsto_kg"].to_numpy() == pytest.approx(214.5, abs=1e-4)
    assert not result["daily"]["extrapolado"].any()


def test_financial_values_are_recomputed_from_canonical_demand(problem, free_initial_result):
    result = free_initial_result
    daily = result["daily"]
    expected_volume = np.array(
        [
            predict_volume_from_artifact(problem.artifact, p, d)
            for p, d in zip(daily["preco_kg"], daily["dia_semana"], strict=True)
        ]
    )
    expected_margin = (
        (1 - problem.tax_rate) * daily["preco_kg"] - problem.costs
    ) * expected_volume
    assert daily["volume_previsto_kg"].to_numpy() == pytest.approx(expected_volume)
    assert result["total_margin_rs"] == pytest.approx(expected_margin.sum())
    assert abs(result["objective_rs"] - result["total_margin_rs"]) < 0.02


def test_extrapolated_free_policy_matches_isolated_day_optimum(problem):
    beta = problem.artifact["coefficients"]["ln_preco"]
    expected_price = problem.costs[0] / (1 - problem.tax_rate) * beta / (beta + 1)
    result = solve_scenario(
        problem,
        Scenario(
            "Sem limites operacionais e com extrapolação",
            enforce_daily_variation=False,
            enforce_weekly_targets=False,
            enforce_initial_anchor=False,
            extrapolate=True,
        ),
    )
    assert result["status"] == "optimal"
    assert result["validation"]["satisfied"]
    assert result["daily"]["preco_kg"].to_numpy() == pytest.approx(expected_price, abs=0.1)
    assert result["daily"]["extrapolado"].all()
    assert not result["validation"]["support_ok"]
    assert result["extrapolation_bounds"] == [800.0, 2000.0]


def test_initial_scenario_does_not_mutate_historical_problem(problem):
    historical = problem.initial_price
    result = solve_scenario(
        problem,
        Scenario("Preço inicial hipotético", initial_price=1200, enforce_weekly_targets=False),
    )
    assert result["validation"]["satisfied"]
    assert problem.initial_price == historical
    assert result["initial_price"] == 1200
    assert not result["daily"]["extrapolado"].any()


def test_incompatible_elasticity_is_rejected(problem):
    artifact = dict(problem.artifact)
    artifact["coefficients"] = dict(artifact["coefficients"], ln_preco=-0.5)
    artifact.pop("model_core_sha256")
    with pytest.raises(ValueError, match="elasticidade"):
        solve_scenario(replace(problem, artifact=artifact), Scenario("Elasticidade incompatível"))
