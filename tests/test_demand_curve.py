import pandas as pd
import pytest

from src.modeling.demand_curve import (
    assign_cluster,
    build_artifact,
    fit_demand_curve,
    is_within_price_support,
    load_artifact,
    predict_volume,
    predict_volume_from_artifact,
    save_artifact,
)


@pytest.fixture(scope="module")
def fitted_model():
    training = pd.read_csv("data/interim/.treino.csv")
    return fit_demand_curve(training)


def test_final_model_reproduces_selected_ols_coefficients(fitted_model):
    assert fitted_model.params["ln_preco"] == pytest.approx(-12.458103, abs=1e-6)
    assert fitted_model.params["Segunda"] == pytest.approx(0.338230, abs=1e-6)
    assert fitted_model.params["Sexta"] == pytest.approx(-1.255048, abs=1e-6)
    assert fitted_model.params["FimDeSemana"] == pytest.approx(-2.883045, abs=1e-6)
    assert fitted_model.smearing_factor == pytest.approx(1.117873, abs=1e-6)


def test_prediction_uses_smearing_and_respects_cluster_support(fitted_model):
    assert is_within_price_support(fitted_model, 1300.0, "TerQuaQui")
    prediction = predict_volume(fitted_model, 1300.0, "TerQuaQui")
    assert prediction > 0

    with pytest.raises(ValueError, match="fora do suporte"):
        predict_volume(fitted_model, 1500.0, "TerQuaQui")


def test_test_period_prices_are_inside_their_cluster_support(fitted_model):
    test = pd.read_csv("data/interim/.teste.csv")
    for _, row in test.iterrows():
        cluster = assign_cluster(row["Dia da Semana"])
        assert is_within_price_support(fitted_model, row["Preço"], cluster)


def test_json_artifact_reproduces_the_fitted_prediction(fitted_model, tmp_path):
    training_path = "data/interim/.treino.csv"
    training = pd.read_csv(training_path)
    artifact = build_artifact(fitted_model, training_path, training)
    artifact_path = tmp_path / "demand_curve_ols.json"
    save_artifact(artifact, artifact_path)
    restored = load_artifact(artifact_path)

    assert restored.metadata["training_rows"] == 76
    assert restored.metadata["training_data_sha256"] == artifact.metadata["training_data_sha256"]
    assert predict_volume_from_artifact(restored, 1300.0, "TerQuaQui") == pytest.approx(
        predict_volume(fitted_model, 1300.0, "TerQuaQui")
    )
