import copy
from pathlib import Path

import numpy as np
import pytest

from src.modeling.demand_curve import (
    load_artifact,
    context_for_weekday,
    file_sha256,
    model_core_sha256,
    predict_volume_from_artifact,
    validate_artifact,
    validate_training_data,
)

ROOT = Path(__file__).resolve().parents[1]


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


def test_prediction_blocks_extrapolation(artifact):
    with pytest.raises(ValueError, match="fora do suporte"):
        predict_volume_from_artifact(artifact, 250.0, "Segunda")


def test_integrity_hash_detects_model_changes(artifact):
    changed = copy.deepcopy(artifact)
    changed["coefficients"]["ln_preco"] = -2.0
    with pytest.raises(ValueError, match="hash registrado"):
        validate_artifact(changed)


def test_context_is_applied_and_prediction_is_positive(artifact):
    assert context_for_weekday(artifact, "Sábado") == "Fim_de_semana"
    assert predict_volume_from_artifact(artifact, 150.0, "Sexta") > 0


def test_published_artifact_matches_its_hash_and_training_data():
    artifact = load_artifact(ROOT / "models/preditivo_diario/curva_demanda.json")

    assert artifact["artifact_version"] == 2
    assert model_core_sha256(artifact) == artifact["model_core_sha256"]
    training_path = validate_training_data(artifact, ROOT)
    assert file_sha256(training_path) == artifact["training"]["data_sha256"]
