from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeling.demand_curve import load_artifact
from src.optimization.price_schedule import (
    diagnose_feasibility,
    margin_vector,
    optimize_prices,
    problem_from_frames,
    select_cost_forecast,
    validate_prices,
    volume_relaxations,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def minerva_problem():
    artifact = load_artifact(ROOT / "models/demand_curve_champion_livro.json")
    uncertainty = load_artifact(ROOT / "models/demand_curve_uncertainty_livro.json")
    development = pd.read_csv(
        ROOT / "data/processed/minerva_modelagem_treino.csv", parse_dates=["data"]
    )
    restrictions = pd.read_csv(ROOT / "data/interim/minerva_restricoes.csv")
    cost = select_cost_forecast(development)
    problem = problem_from_frames(
        artifact,
        restrictions,
        unit_cost=cost["forecast_cost_kg"],
        initial_price=float(development.sort_values("data")["preco_kg"].iloc[-1]),
        uncertainty=uncertainty,
    )
    return problem, cost


def test_cost_is_selected_without_holdout_and_uses_four_week_rule(minerva_problem):
    _, cost = minerva_problem
    assert cost["cutoff"] == "2025-10-31"
    assert cost["method"] == "media_4_semanas"
    assert cost["forecast_cost_kg"] == pytest.approx(988.8425607921679)


def test_official_problem_is_infeasible_and_does_not_emit_plan(minerva_problem):
    problem, _ = minerva_problem
    diagnostic = diagnose_feasibility(problem)
    result = optimize_prices(problem)

    assert diagnostic["status"] == "infeasible_targets"
    assert diagnostic["weeks"]["semana_1"]["maximum_reachable_kg"] == pytest.approx(
        79.2015, abs=1e-3
    )
    assert diagnostic["weeks"]["semana_2"]["maximum_reachable_kg"] == pytest.approx(
        87.0504, abs=1e-3
    )
    assert result["status"] == "infeasible"
    assert result["daily"] is None


def test_removing_only_initial_link_recovers_a_valid_plan(minerva_problem):
    problem, _ = minerva_problem
    result = optimize_prices(problem, enforce_initial=False)

    assert result["status"] == "optimal"
    assert result["daily"] is not None
    checks = validate_prices(
        problem,
        result["daily"]["preco_kg"],
        initial_delta=None,
        daily_delta=problem.daily_variation,
    )
    assert checks["satisfied"]
    assert checks["variation_ok"]
    assert checks["targets_ok"]


def test_margin_recomposes_tax_cost_and_volume(minerva_problem):
    problem, _ = minerva_problem
    result = optimize_prices(problem, enforce_initial=False)
    daily = result["daily"]
    recomposed = (
        (1 - problem.tax_rate) * daily["preco_kg"].to_numpy() - problem.costs
    ) * daily["volume_previsto_kg"].to_numpy()

    assert np.allclose(margin_vector(problem, daily["preco_kg"]), recomposed)
    assert recomposed.sum() == pytest.approx(result["total_margin_rs"])


def test_volume_relaxations_match_official_envelope(minerva_problem):
    problem, _ = minerva_problem
    relaxations = volume_relaxations(problem)

    assert relaxations["weekly_shortage_kg"]["semana_1"] == pytest.approx(36.2985, abs=1e-3)
    assert relaxations["weekly_shortage_kg"]["semana_2"] == pytest.approx(28.4496, abs=1e-3)
    assert relaxations["maximum_common_target_kg"] == pytest.approx(113.1450, abs=1e-3)
    assert relaxations["minimum_common_tolerance"] == pytest.approx(0.519991, abs=1e-5)
