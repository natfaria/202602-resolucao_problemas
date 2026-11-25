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
    return RelaxationStudy(problem)


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


def test_daily_variation_alone_recovers_above_a_search_threshold(study):
    threshold = study.minimum("daily_variation", upper=120.0)
    assert threshold["status"] == "bracketed"
    assert 20 < threshold["minimum"] < 30
    assert threshold["infeasible_value"] < threshold["minimum"] <= threshold["feasible_value"]


def test_initial_transition_is_independent_of_daily_variation(study):
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


def test_saved_intro_curves_change_only_the_named_rule(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_sensibilidade_isolada.json")
    inputs = load_artifact(ROOT / payload["planning_inputs_file"])
    assert payload["planning_inputs_sha256"] == inputs["inputs_sha256"]
    assert payload["model_core_sha256"] == problem.artifact["model_core_sha256"]
    base = payload["base"]
    columns = {
        "daily_variation": "variacao_interna_rs",
        "initial_transition": "transicao_inicial_rs",
        "tolerance_lower": "minimo_semanal_kg",
        "tolerance_upper": "maximo_semanal_kg",
    }
    assert {row["regra"] for row in payload["curves"]} == set(columns)
    for row in payload["curves"]:
        for rule, column in columns.items():
            if rule != row["regra"]:
                assert row[column] == pytest.approx(base[column])
        assert row["primeira_mudanca_limitada"]
        assert row["variacao_interna_limitada"]
        assert not row["extrapolacao"]
        assert row["preco_anterior_kg"] == problem.initial_price
        assert row["model_core_sha256"] == payload["model_core_sha256"]
        if not row["minimo_semanal_ativo"]:
            assert row["regra"] == "tolerance_lower" and row["minimo_semanal_kg"] == 0
        if not row["maximo_semanal_ativo"]:
            assert row["regra"] == "tolerance_upper" and row["maximo_semanal_kg"] is None
        if row["status"] == "infeasible":
            assert row["margem_prevista_rs"] is None and not row["plano_verificado"]
        else:
            assert row["status"] == "optimal" and row["plano_verificado"]
            assert row["margem_prevista_rs"] is not None


def test_saved_intro_curves_include_both_sides_of_feasibility(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_sensibilidade_isolada.json")
    for rule in ["initial_transition", "tolerance_lower"]:
        threshold = payload["thresholds"][rule]
        assert threshold["status"] == "bracketed"
        rows = [row for row in payload["curves"] if row["regra"] == rule]
        target = next(iter(problem.targets.values()))
        for boundary, expected in [
            ("infeasible_value", "infeasible"),
            ("feasible_value", "optimal"),
        ]:
            value = threshold[boundary]
            if rule == "tolerance_lower":
                value = target * (1 - value)
            matches = [
                row
                for row in rows
                if row["valor_limite"] is not None and abs(row["valor_limite"] - value) < 1e-9
            ]
            assert len(matches) == 1 and matches[0]["status"] == expected
    assert all(
        row["status"] == "infeasible"
        for row in payload["curves"]
        if row["regra"] in {"daily_variation", "tolerance_upper"}
    )
    assert any(
        row["regra"] == "tolerance_lower" and row["valor_limite"] == 0 and row["plano_verificado"]
        for row in payload["curves"]
    )
    assert any(
        row["regra"] == "tolerance_upper" and row["maximo_semanal_kg"] is None
        for row in payload["curves"]
    )


def test_saved_intro_free_reference_is_separate_from_single_rule_curves(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_sensibilidade_isolada.json")
    assert payload["holdout_used"] is False
    base, extra, free = payload["base"], payload["extrapolation_only"], payload["free_reference"]
    assert base["status"] == extra["status"] == "infeasible"
    assert extra["extrapolacao"] and not base["extrapolacao"]
    for name in [
        "variacao_interna_rs",
        "transicao_inicial_rs",
        "minimo_semanal_kg",
        "maximo_semanal_kg",
    ]:
        assert extra[name] == base[name]
    assert free["status"] == "optimal" and free["plano_verificado"]
    assert not free["scenario"]["enforce_initial_anchor"]
    assert not free["scenario"]["enforce_daily_variation"]
    assert not free["scenario"]["enforce_weekly_targets"]
    assert free["scenario"]["extrapolate"]
    beta = problem.artifact["coefficients"]["ln_preco"]
    expected_price = problem.costs[0] / (1 - problem.tax_rate) * beta / (beta + 1)
    assert free["preco_otimo_kg"] == pytest.approx(expected_price)
    assert free["margem_prevista_rs"] == pytest.approx(free["margem_analitica_rs"], abs=0.02)


def test_initial_price_sensitivity_preserves_every_operational_rule(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_sensibilidade_preco_anterior.json")
    assert payload["holdout_used"] is False
    assert payload["initial_price_observed"] == problem.initial_price
    assert payload["unit_cost_kg"] == problem.costs[0]
    assert payload["tax_rate"] == problem.tax_rate
    assert payload["model_core_sha256"] == problem.artifact["model_core_sha256"]
    cases = payload["cases"]
    assert len(cases) > 10
    assert len({row["preco_anterior_kg"] for row in cases}) == len(cases)
    historical = [row for row in cases if row["historico"]]
    assert len(historical) == 1
    assert historical[0]["preco_anterior_kg"] == problem.initial_price
    assert historical[0]["status"] == "infeasible"
    assert any(row["status"] == "optimal" for row in cases)
    target = next(iter(problem.targets.values()))
    for row in cases:
        assert row["variacao_interna_rs"] == problem.daily_variation
        assert row["primeira_mudanca_rs"] == problem.init_var
        assert row["minimo_semanal_kg"] == target * (1 - problem.tol_lower)
        assert row["maximo_semanal_kg"] == target * (1 + problem.tol_upper)
        assert not row["extrapolacao"]
        assert row["model_core_sha256"] == payload["model_core_sha256"]
        if row["status"] == "infeasible":
            assert row["margem_prevista_rs"] is None
        else:
            assert row["plano_verificado"]


def test_financial_highlights_preserve_single_rule_scope_before_test(problem):
    payload = load_artifact(ROOT / "data/processed/minerva_sensibilidade_isolada.json")
    financial = pd.read_csv(ROOT / "reports/tables/03_comparacao_financeira_uma_regra.csv")
    highlights = payload["financial_highlights"]
    assert len(highlights) == 9
    assert set(financial["cenario"]) == set(highlights)
    base = payload["base"]
    columns = [
        "variacao_interna_rs",
        "transicao_inicial_rs",
        "minimo_semanal_kg",
        "maximo_semanal_kg",
        "extrapolacao",
    ]
    for key, row in highlights.items():
        if key != "livre":
            changed = sum(
                row[col] != base[col]
                if row[col] is None or base[col] is None
                else not np.isclose(row[col], base[col], rtol=0, atol=1e-8)
                for col in columns
            )
            assert changed <= 1
            assert row["primeira_mudanca_limitada"]
            assert row["variacao_interna_limitada"]
        total = financial.loc[
            (financial["cenario"] == key) & (financial["periodo"] == "total")
        ].iloc[0]
        if row["margem_prevista_rs"] is None:
            assert pd.isna(total["margem_prevista_rs"])
        else:
            assert total["margem_prevista_rs"] == pytest.approx(
                row["margem_prevista_rs"], abs=0.02
            )
