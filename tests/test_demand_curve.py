import copy

import numpy as np
import pytest

from src.modeling.demand_curve import (
    context_for_weekday,
    model_core_sha256,
    predict_volume_from_artifact,
    validate_artifact,
)


@pytest.fixture
def artifact():
    payload = {
        "artifact_version": 2,
        "model_id": "fixture-power",
        "family": "power",
        "calendar": {
            "baseline": "Dia_util",
            "mapping": {
                "Segunda": "Dia_util",
                "Terça": "Dia_util",
                "Quarta": "Dia_util",
                "Quinta": "Dia_util",
                "Sexta": "Sexta",
                "Sábado": "Fim_de_semana",
                "Domingo": "Fim_de_semana",
            },
        },
        "feature_order": [
            "const",
            "ln_preco",
            "contexto_Sexta",
            "contexto_Fim_de_semana",
        ],
        "coefficients": {
            "const": 10.0,
            "ln_preco": -1.0,
            "contexto_Sexta": -0.5,
            "contexto_Fim_de_semana": -1.0,
        },
        "smearing_factor": 1.1,
        "price_support": {
            "Dia_util": {"min": 100.0, "max": 200.0, "n": 20},
            "Sexta": {"min": 100.0, "max": 200.0, "n": 5},
            "Fim_de_semana": {"min": 100.0, "max": 200.0, "n": 4},
        },
    }
    payload["model_core_sha256"] = model_core_sha256(payload)
    return payload


def test_prediction_reproduces_power_equation(artifact):
    prediction = predict_volume_from_artifact(artifact, 150.0, "Segunda")
    expected = np.exp(10.0 - np.log(150.0)) * 1.1
    assert prediction == pytest.approx(expected)


def test_context_and_scenario_are_applied(artifact):
    uncertainty = {
        "scenario_multipliers": {"conservative": 0.7, "central": 1.0, "optimistic": 1.4}
    }
    friday = predict_volume_from_artifact(artifact, 150.0, "Sexta")
    conservative = predict_volume_from_artifact(
        artifact,
        150.0,
        "Sexta",
        scenario="conservative",
        uncertainty=uncertainty,
    )
    assert context_for_weekday(artifact, "Sábado") == "Fim_de_semana"
    assert conservative == pytest.approx(friday * 0.7)


def test_prediction_blocks_extrapolation(artifact):
    with pytest.raises(ValueError, match="fora do suporte"):
        predict_volume_from_artifact(artifact, 250.0, "Segunda")


def test_integrity_hash_detects_model_changes(artifact):
    changed = copy.deepcopy(artifact)
    changed["coefficients"]["ln_preco"] = -2.0
    with pytest.raises(ValueError, match="hash registrado"):
        validate_artifact(changed)
