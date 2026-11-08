"""Provas de viabilidade, isolamento de regras e rastreabilidade das flexibilizações."""

from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeling.demand_curve import load_artifact, predict_volume_from_artifact
from src.optimization.planning_inputs import load_planning_inputs, load_relaxation_limits
from src.optimization.relaxation_study import (
    Relaxation,
    RelaxationStudy,
    apply_relaxation,
    compare_margin_relaxations,
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
    limits = load_relaxation_limits(ROOT / "models/otimizacao/limites_flexibilizacoes.json")
    return RelaxationStudy(
        problem,
        daily_variation_ceiling=limits["daily_variation_ceiling"],
        initial_transition_ceiling=limits["initial_transition_ceiling"],
    )


def test_relaxing_internal_changes_preserves_initial_anchor(problem):
    relaxed = apply_relaxation(problem, Relaxation(daily_variation_factor=5))
    assert relaxed.daily_variation == 10
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


def test_daily_variation_alone_does_not_recover_within_the_received_ceiling(study):
    threshold = study.minimum("daily_variation", upper=study.daily_variation_ceiling)
    assert threshold["status"] == "no_recovery_in_range"
    assert threshold["minimum"] is None
    assert threshold["infeasible_value"] == 15


def test_commercial_ceiling_is_enforced_before_solving(study):
    count = len(study.results)
    with pytest.raises(ValueError, match="variação interna excede"):
        study.evaluate(Relaxation(daily_variation_factor=8))
    with pytest.raises(ValueError, match="não pode ser removida"):
        study.evaluate(enforce_variation=False)
    assert len(study.results) == count


def test_initial_transition_is_not_subject_to_the_internal_ceiling(study):
    result = study.evaluate(Relaxation(initial_transition_factor=30, daily_variation_factor=7.5))
    assert result["parameters"]["initial_variation"] == 60
    assert result["parameters"]["daily_variation"] == 15
    assert result["validation"]["satisfied"]


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


def test_financial_dominance_preserves_extra_margin_and_reports_a_witness():
    frame = pd.DataFrame(
        {
            "case_id": ["a", "b", "c", "d", "e", "f"],
            "initial": [2, 3, 4, 4, 1, 4],
            "daily": [2, 2, 2, 2, 1, 2],
            "lower": [0, 0, 0, 0, 0, 0],
            "upper": [0, 0, 0, 5, 0, 0],
            "margem_prevista_rs": [100, 100, 130, 130, 200, 130],
            "limite_superior_margem_rs": [100.02, 100.02, 130.02, 130.02, 200.02, 131],
            "plano_verificado": [True] * 6,
            "status": ["optimal"] * 5 + ["feasible_time_limit"],
        }
    )
    # O ponto e não é um comparador admissível, apesar da margem impressa.
    frame.loc[4, "plano_verificado"] = False
    result = compare_margin_relaxations(frame, ["initial", "daily", "lower", "upper"])
    result = result.set_index("case_id")
    assert result.loc["a", "dominancia_financeira"] == "eficiente"
    assert result.loc["b", "caso_dominante"] == "a"
    assert result.loc["c", "dominancia_financeira"] == "eficiente"
    assert result.loc["d", "caso_dominante"] == "c"
    assert result.loc["e", "dominancia_financeira"] == "nao_comparado"
    assert result.loc["f", "dominancia_financeira"] == "nao_comparado"


def test_financial_dominance_accounts_for_the_solver_bound():
    frame = pd.DataFrame(
        {
            "case_id": ["a", "b"],
            "cost": [1, 2],
            "margem_prevista_rs": [100, 100],
            "limite_superior_margem_rs": [100, 101],
            "plano_verificado": [True, True],
            "status": ["optimal", "optimal"],
        }
    )
    result = compare_margin_relaxations(frame, ["cost"], margin_tolerance=0.10)
    assert result["dominancia_financeira"].eq("eficiente").all()


def test_saved_partial_grid_covers_all_four_families_and_selects_better_margins(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_simulacao_relaxacoes.json")
    grid = pd.DataFrame(payload["partial_combinations"])
    assert set(grid["n_familias_flexibilizadas"]) == {0, 1, 2, 3, 4}
    assert (grid["model_core_sha256"] == problem.artifact["model_core_sha256"]).all()
    for number in [2, 3, 4]:
        assert grid.loc[grid["n_familias_flexibilizadas"] == number, "plano_verificado"].any()
    assert grid["tolerancia_inferior"].nunique() > 1
    assert grid["tolerancia_superior"].nunique() > 1
    assert (
        grid["variacao_interna_rs"]
        .le(payload["relaxation_limits"]["daily_variation_ceiling"])
        .all()
    )
    assert payload["relaxation_limits"]["initial_transition_ceiling"] is None
    alternatives = pd.DataFrame(payload["alternatives"])
    assert alternatives["dominancia_financeira"].eq("eficiente").all()
    assert alternatives["diferenca_referencia_factivel_rs"].gt(0.10).all()
    assert alternatives["n_familias_flexibilizadas"].ge(2).all()
    assert 4 in alternatives["n_familias_flexibilizadas"].to_list()
    assert (
        payload["benchmarks"]["fully_relaxed"]["model_core_sha256"]
        == problem.artifact["model_core_sha256"]
    )
    assert (
        alternatives["margem_prevista_rs"].max()
        <= payload["benchmarks"]["fully_relaxed"]["bound_rs"] + 0.02
    )
    weekly = pd.read_csv(ROOT / "reports/tables/relaxacoes/resumo_semanal_alternativas.csv")
    assert weekly.groupby("case_id").size().eq(len(problem.targets)).all()
    assert weekly["meta_atendida"].all()
    assert weekly["folga_inferior_kg"].ge(-1e-4).all()
    assert weekly["folga_superior_kg"].ge(-1e-4).all()
    reference = payload["cases"][payload["benchmarks"]["minimum_recovery_reference"]["case_id"]]
    assert reference["parameters"]["daily_variation"] <= 15


def test_saved_relaxations_use_the_published_curve_and_fixed_historical_inputs(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_simulacao_relaxacoes.json")
    assert payload["model_core_sha256"] == problem.artifact["model_core_sha256"]
    assert payload["unit_cost_kg"] == pytest.approx(problem.costs[0])
    assert payload["initial_price_observed"] == problem.initial_price
    assert payload["smearing_factor"] == problem.artifact["smearing_factor"]
    assert payload["holdout_used"] is False
    assert payload["cases"]
    for result in payload["cases"].values():
        assert result["parameters"]["daily_variation"] <= 15
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
