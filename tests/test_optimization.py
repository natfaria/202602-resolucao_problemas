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
    validate_prices,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def minerva_problem():
    development = pd.read_csv(
        ROOT / "data/processed/minerva_modelagem_treino.csv", parse_dates=["data"]
    ).sort_values("data")
    last_day = development.iloc[-1]
    return problem_from_frames(
        load_artifact(ROOT / "models/preditivo_diario/curva_demanda.json"),
        pd.read_csv(ROOT / "data/interim/minerva_restricoes.csv"),
        unit_cost=float(last_day["custo_kg"]),
        initial_price=float(last_day["preco_kg"]),
    )


def test_official_problem_is_infeasible_and_does_not_emit_plan(minerva_problem):
    problem = minerva_problem
    diagnostic = diagnose_feasibility(problem)
    result = optimize_prices(problem)

    assert diagnostic["status"] == "infeasible_targets"
    assert diagnostic["weeks"]["semana_1"]["maximum_reachable_kg"] == pytest.approx(
        76.9868, abs=1e-3
    )
    assert diagnostic["weeks"]["semana_2"]["maximum_reachable_kg"] == pytest.approx(
        84.6162, abs=1e-3
    )
    assert result["status"] == "infeasible"
    assert result["daily"] is None


def test_removing_only_initial_link_recovers_a_valid_plan(minerva_problem):
    problem = minerva_problem
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
    problem = minerva_problem
    result = optimize_prices(problem, enforce_initial=False)
    daily = result["daily"]
    recomposed = (
        (1 - problem.tax_rate) * daily["preco_kg"].to_numpy() - problem.costs
    ) * daily["volume_previsto_kg"].to_numpy()

    assert np.allclose(margin_vector(problem, daily["preco_kg"]), recomposed)
    assert recomposed.sum() == pytest.approx(result["total_margin_rs"])


def test_removing_all_initial_constraints_reproduces_reference(minerva_problem):
    """Sem a ligação inicial, a margem é R$ 48.917,58 (cenário R1 publicado)."""
    problem = minerva_problem
    result = optimize_prices(problem, enforce_initial=False)

    assert result["status"] == "optimal"
    assert result["total_margin_rs"] == pytest.approx(48917.58, abs=0.01)


def test_removing_all_volume_targets_reproduces_reference(minerva_problem):
    """Sem metas semanais e com a ligação inicial mantida, a margem é R$ 33.336,94."""
    problem = minerva_problem
    result = optimize_prices(problem, enforce_targets=False)

    assert result["status"] == "optimal"
    assert result["total_margin_rs"] == pytest.approx(33336.94, abs=0.01)
