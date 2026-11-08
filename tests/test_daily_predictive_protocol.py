"""Provas do domínio, da calibração e do critério diário do estudo preditivo."""

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from src.modeling.demand_curve import (
    load_artifact,
    predict_volume_from_artifact,
    validate_artifact,
    validate_training_data,
)

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports/tables/preditivo_diario"
MODEL = ROOT / "models/preditivo_diario/curva_demanda.json"


@pytest.fixture(scope="module")
def protocol():
    """Carrega só funções puras e declarações, sem executar a análise ou ler holdout."""
    notebook = json.loads((ROOT / "notebooks/2.0.1-minerva-modelo-preditivo.ipynb").read_text())
    weekdays = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    namespace = {
        "np": np,
        "pd": pd,
        "sm": sm,
        "ORDEM_DIAS": weekdays + ["Sábado", "Domingo"],
        "DIAS_UTEIS": weekdays,
    }
    variables = {
        "MAPAS_CONTEXTO",
        "ORDEM_CONTEXTO",
        "FAMILIAS_LOG",
        "CANDIDATOS",
        "ZONA_WMAPE_DIARIO",
        "ZONA_RMSE",
    }
    functions = {
        "especificacao",
        "matriz_desenho",
        "ajustar",
        "prever",
        "painel_erros",
        "aplicar_regra",
    }
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        tree = ast.parse("".join(cell["source"]))
        nodes = [
            node
            for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name in functions)
            or (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in variables for t in node.targets)
            )
        ]
        exec(  # noqa: S102 - Executa apenas as funções e constantes selecionadas pela AST.
            compile(ast.Module(body=nodes, type_ignores=[]), "protocol_functions", "exec"),
            namespace,
        )
    return namespace


def test_smearing_uses_weekday_residuals_without_dropping_coefficient_observations(protocol):
    training = pd.read_csv(ROOT / "data/processed/minerva_modelagem_treino.csv")
    fitted, factor = protocol["ajustar"](training, protocol["CANDIDATOS"]["P3"])
    expected = np.exp(fitted.resid.loc[training["dia_semana"].isin(protocol["DIAS_UTEIS"])])

    assert fitted.nobs == len(training) == 76
    assert len(expected) == 66
    assert factor == pytest.approx(expected.mean())
    assert not np.isclose(factor, np.exp(fitted.resid).mean())
    artifact = load_artifact(MODEL)
    assert artifact["smearing_factor"] == pytest.approx(factor)
    assert artifact["smearing_calibration"]["rows"] == 66


def test_cross_validation_keeps_weekly_origins_and_future_weekday_horizons():
    predictions = pd.read_csv(
        TABLES / "previsoes_validacao_cruzada.csv",
        parse_dates=["origem", "data", "ajuste_ate", "inicio_semana"],
    )
    expected_origins = pd.to_datetime(
        ["2025-09-15", "2025-09-22", "2025-09-29", "2025-10-06", "2025-10-13", "2025-10-20"]
    )
    assert predictions["origem"].drop_duplicates().tolist() == expected_origins.tolist()
    assert (predictions["data"].dt.weekday < 5).all()
    assert (predictions["origem"].dt.weekday == 0).all()
    assert (predictions["ajuste_ate"] < predictions["origem"]).all()
    assert (predictions["data"] >= predictions["origem"]).all()
    assert (predictions["data"] < predictions["origem"] + pd.Timedelta(days=14)).all()
    assert predictions["data"].max() <= pd.Timestamp("2025-10-31")
    assert (predictions.groupby(["candidato", "fold"]).size() == 10).all()
    assert (predictions.groupby(["candidato", "fold"])["inicio_semana"].nunique() == 2).all()


def test_selection_prioritizes_daily_error_even_when_weekly_ranking_disagrees(protocol):
    panel = pd.DataFrame(
        {
            "Parâmetros": [2, 4, 4],
            "WMAPE diário (%)": [80.0, 20.0, 19.0],
            "WMAPE semanal (%)": [1.0, 60.0, 61.0],
            "RMSE (kg)": [10.0, 10.0, 10.0],
            "Válido": [True, True, True],
            "Concorre": [True, True, True],
        },
        index=["P0", "P3", "E1"],
    )
    _, chosen, zone = protocol["aplicar_regra"](panel)
    assert chosen == "P3"
    assert set(zone.index) == {"P3", "E1"}


def test_published_curve_is_reproducible_and_rejects_weekends(protocol):
    artifact = load_artifact(MODEL)
    validate_artifact(artifact)
    validate_training_data(artifact, ROOT)
    assert set(artifact["calendar"]["mapping"]) == set(protocol["DIAS_UTEIS"])
    assert artifact["selection"]["primary_metric"] == "WMAPE_daily"
    assert artifact["selection"]["folds"] == 6

    training = pd.read_csv(ROOT / "data/processed/minerva_modelagem_treino.csv")
    fitted, factor = protocol["ajustar"](training, protocol["CANDIDATOS"]["P3"])
    sample = pd.DataFrame(
        {"dia_semana": protocol["DIAS_UTEIS"], "preco_kg": 1300.0, "ln_preco": np.log(1300.0)}
    )
    expected = protocol["prever"](fitted, factor, sample, protocol["CANDIDATOS"]["P3"])
    actual = [
        predict_volume_from_artifact(artifact, 1300.0, day) for day in protocol["DIAS_UTEIS"]
    ]
    assert actual == pytest.approx(expected)
    for day in ["Sábado", "Domingo"]:
        with pytest.raises(ValueError, match="não reconhecido"):
            predict_volume_from_artifact(artifact, 1300.0, day)
