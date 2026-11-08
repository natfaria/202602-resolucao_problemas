"""Provas de separação temporal e preservação das curvas nas análises adicionais."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeling.benchmarks import weekday_mean_forecast
from src.modeling.demand_curve import predict_volume_from_artifact, validate_artifact
from src.optimization.assumption_sensitivity import assumption_problem
from src.optimization.planning_inputs import load_planning_inputs

ROOT = Path(__file__).resolve().parents[1]


def test_weekday_benchmark_uses_only_history_and_preserves_horizon_order():
    history = pd.DataFrame(
        {
            "data": ["2025-09-01", "2025-09-08", "2025-09-05"],
            "dia_semana": ["Segunda", "Segunda", "Sexta"],
            "volume_kg": [10.0, 30.0, 5.0],
        }
    )
    horizon = pd.DataFrame(
        {
            "data": ["2025-09-19", "2025-09-15"],
            "dia_semana": ["Sexta", "Segunda"],
            "volume_kg": [9999.0, 9999.0],
        }
    )
    assert weekday_mean_forecast(history, horizon) == pytest.approx([5.0, 20.0])
    with pytest.raises(ValueError, match="antes"):
        weekday_mean_forecast(pd.concat([history, horizon]), horizon)


def test_sensitivity_rotates_at_pivot_without_mutating_published_model():
    base, _ = load_planning_inputs(
        ROOT / "models/otimizacao/entradas_planejamento.json", root=ROOT
    )
    original = deepcopy(base.artifact)
    stress = assumption_problem(base, elasticity=-7.04, demand_factor=1.2, cost_factor=1.05)
    validate_artifact(stress.artifact)
    for weekday in ["Segunda", "Sexta"]:
        central = predict_volume_from_artifact(base.artifact, 1300.0, weekday)
        assert predict_volume_from_artifact(stress.artifact, 1300.0, weekday) == pytest.approx(
            central * 1.2
        )
    assert stress.artifact["model_core_sha256"] != base.artifact["model_core_sha256"]
    assert base.artifact == original
    assert np.allclose(stress.costs, base.costs * 1.05)
    assert stress.targets == base.targets
    assert stress.daily_variation == base.daily_variation


def test_identity_sensitivity_keeps_model_hash():
    base, _ = load_planning_inputs(
        ROOT / "models/otimizacao/entradas_planejamento.json", root=ROOT
    )
    identity = assumption_problem(base)
    assert identity.artifact["model_core_sha256"] == base.artifact["model_core_sha256"]
    with pytest.raises(ValueError, match="menor que -1"):
        assumption_problem(base, elasticity=-0.5)
