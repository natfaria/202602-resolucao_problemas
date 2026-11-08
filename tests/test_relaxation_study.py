"""Provas de viabilidade, isolamento de regras e rastreabilidade das flexibilizações."""

from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeling.demand_curve import load_artifact, predict_volume_from_artifact
from src.optimization.planning_inputs import load_planning_inputs
from src.optimization.relaxation_study import (
    Relaxation,
    RelaxationStudy,
    apply_relaxation,
    pareto_feasible,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def problem():
    return load_planning_inputs(ROOT / "models/otimizacao/entradas_planejamento.json", root=ROOT)[
        0
    ]


@pytest.fixture(scope="module")
def study(problem):
    return RelaxationStudy(problem)


def test_relaxing_internal_changes_preserves_initial_anchor(problem):
    relaxed = apply_relaxation(problem, Relaxation(daily_variation_factor=10))
    assert relaxed.daily_variation == 20
    assert relaxed.init_var == 2
    assert relaxed.initial_price == problem.initial_price
    assert relaxed.artifact is problem.artifact
    initial = apply_relaxation(problem, Relaxation(initial_transition_factor=30))
    assert initial.init_var == 60 and initial.daily_variation == 2


def test_weekly_sides_are_independent_and_target_shift_is_distinct(problem):
    lower = apply_relaxation(problem, Relaxation(tolerance_lower_factor=2))
    upper = apply_relaxation(problem, Relaxation(tolerance_upper_factor=2))
    shifted = apply_relaxation(problem, Relaxation(target_nominal_factor=0.5))
    assert lower.tol_lower == 0.6 and lower.tol_upper == 0.3
    assert upper.tol_lower == 0.3 and upper.tol_upper == 0.6
    assert shifted.targets["semana_1"] == 82.5
    assert shifted.tol_lower == shifted.tol_upper == 0.3
    with pytest.raises(ValueError, match="Tolerâncias separadas"):
        apply_relaxation(problem, Relaxation(tolerance_lower_factor=4))
    with pytest.raises(ValueError, match="finitos"):
        Relaxation(daily_variation_factor=np.inf)


def test_official_infeasibility_has_a_volume_certificate_and_no_plan(study):
    result = study.evaluate()
    assert result["status"] == "infeasible"
    assert result["certificate"] == "reachable_volume_bounds"
    assert result["daily"] is None and result["weekly"] is None
    assert result["diagnostics"]["weeks"]["semana_1"]["maximum_reachable_kg"] == pytest.approx(
        76.98681844
    )
    assert study.evaluate() is result


@pytest.mark.parametrize(
    "rule,upper,precision",
    [
        ("daily_variation", 35, 0.01),
        ("initial_transition", 120, 0.01),
        ("tolerance_lower", 0.9, 1e-5),
    ],
)
def test_minimum_is_bracketed_by_infeasibility_and_a_verified_plan(study, rule, upper, precision):
    threshold = study.minimum(rule, upper=upper, precision=precision)
    assert threshold["status"] == "bracketed"
    assert 0 < threshold["feasible_value"] - threshold["infeasible_value"] <= precision
    below = study.evaluate(study.relaxation_at(rule, threshold["infeasible_value"]))
    above = study.evaluate(study.relaxation_at(rule, threshold["feasible_value"]))
    assert below["status"] == "infeasible" and below["daily"] is None
    assert above["validation"]["satisfied"]
    assert above["status"] == "optimal"
    assert not above["daily"]["extrapolado"].any()


def test_upper_limit_alone_cannot_recover_a_shortage(study):
    result = study.evaluate(Relaxation(tolerance_upper_factor=3))
    assert result["status"] == "infeasible"
    assert result["diagnostics"]["weeks"]["semana_1"]["shortage_kg"] > 38


def test_margin_bounds_are_consistent_with_nested_feasible_sets(study):
    results = [study.evaluate(Relaxation(initial_transition_factor=x / 2)) for x in [60, 80, 110]]
    for result in results:
        assert result["status"] == "optimal"
        assert result["validation"]["satisfied"]
    for smaller, larger in pairwise(results):
        assert smaller["total_margin_rs"] <= larger["bound_rs"] + 0.02
        assert larger["total_margin_rs"] >= smaller["total_margin_rs"] - 0.10


def test_unknown_solver_outcome_does_not_become_infeasibility(problem, monkeypatch):
    import src.optimization.relaxation_study as module

    monkeypatch.setattr(
        module, "solve_scenario", lambda *a, **k: {"status": "no_solution", "validation": None}
    )
    with pytest.raises(RuntimeError, match="não determinada"):
        RelaxationStudy(problem).minimum("initial_transition", upper=120)


def test_nominal_target_sensitivity_is_not_bisected_as_a_relaxation(study):
    with pytest.raises(ValueError, match="monotônica"):
        study.minimum("target_nominal", upper=200)


def test_pareto_uses_only_verified_cases_and_keeps_operational_tradeoffs():
    frame = pd.DataFrame(
        {
            "a": [2, 4, 5, 1],
            "b": [5, 2, 6, 1],
            "plano_verificado": [True, True, True, False],
            "margem_prevista_rs": [100, 90, 150, None],
        }
    )
    frontier = pareto_feasible(frame, ["a", "b"])
    assert list(zip(frontier["a"], frontier["b"], strict=True)) == [(2, 5), (4, 2)]


def test_saved_relaxations_use_the_published_curve_and_fixed_historical_inputs(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_simulacao_relaxacoes.json")
    assert payload["model_core_sha256"] == problem.artifact["model_core_sha256"]
    assert payload["unit_cost_kg"] == pytest.approx(problem.costs[0])
    assert payload["initial_price_observed"] == problem.initial_price
    assert payload["smearing_factor"] == problem.artifact["smearing_factor"]
    assert payload["holdout_used"] is False
    assert payload["cases"]
    for result in payload["cases"].values():
        assert result["initial_price"] == problem.initial_price
        assert result["model_core_sha256"] == problem.artifact["model_core_sha256"]
        if result["daily"] is None:
            continue
        daily = pd.DataFrame(result["daily"])
        predicted = [
            predict_volume_from_artifact(problem.artifact, p, d)
            for p, d in zip(daily["preco_kg"], daily["dia_semana"], strict=True)
        ]
        assert daily["volume_previsto_kg"].to_numpy() == pytest.approx(predicted)
        assert result["validation"]["satisfied"]
        assert not daily["extrapolado"].any()
