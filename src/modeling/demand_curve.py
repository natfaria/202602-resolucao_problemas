"""Curva final de demanda preço-volume.

Especificação definida no EDA:

``ln(volume) = intercepto_do_cluster + beta * ln(preço) + erro``

O modelo usa OLS, quatro interceptos de nível e uma elasticidade compartilhada.
As previsões retornam em quilogramas com correção global de smearing de Duan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper


CLUSTER_BASE = "TerQuaQui"
CLUSTERS = ("Segunda", "TerQuaQui", "Sexta", "FimDeSemana")
COLUNAS_MODELO = ("const", "ln_preco", "Segunda", "Sexta", "FimDeSemana")


def assign_cluster(dia_da_semana: str) -> str:
    """Mapeia o dia da semana para o cluster de nível selecionado no EDA."""
    if dia_da_semana == "Segunda":
        return "Segunda"
    if dia_da_semana in ("Terça", "Quarta", "Quinta"):
        return "TerQuaQui"
    if dia_da_semana == "Sexta":
        return "Sexta"
    if dia_da_semana in ("Sábado", "Domingo"):
        return "FimDeSemana"
    raise ValueError(f"Dia da semana não reconhecido: {dia_da_semana!r}")


@dataclass(frozen=True)
class DemandCurveModel:
    """Artefato necessário para prever volume em kg de forma reproduzível."""

    regression: RegressionResultsWrapper
    smearing_factor: float
    price_support: Mapping[str, tuple[float, float]]

    @property
    def params(self) -> pd.Series:
        """Coeficientes OLS, expostos para inspeção no notebook e relatórios."""
        return self.regression.params

    @property
    def pvalues(self) -> pd.Series:
        """p-valores OLS dos coeficientes estimados."""
        return self.regression.pvalues


@dataclass(frozen=True)
class DemandCurveArtifact:
    """Representação JSON, auditável e independente de pickle do modelo final."""

    params: Mapping[str, float]
    smearing_factor: float
    price_support: Mapping[str, tuple[float, float]]
    metadata: Mapping[str, Any]


def _validate_training_data(df: pd.DataFrame) -> None:
    required = {"Preço", "Volume Realizado (kg)"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dados de treino sem as colunas obrigatórias: {sorted(missing)}")
    if "Cluster" not in df.columns and "Dia da Semana" not in df.columns:
        raise ValueError("Informe a coluna 'Cluster' ou 'Dia da Semana'.")
    if (df["Preço"] <= 0).any() or (df["Volume Realizado (kg)"] <= 0).any():
        raise ValueError("Preço e volume precisam ser estritamente positivos para a transformação logarítmica.")


def _with_cluster(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "Cluster" not in result.columns:
        result["Cluster"] = result["Dia da Semana"].map(assign_cluster)
    invalid = set(result["Cluster"].dropna().unique()) - set(CLUSTERS)
    if invalid:
        raise ValueError(f"Clusters não reconhecidos: {sorted(invalid)}")
    if result["Cluster"].isna().any():
        raise ValueError("Há observações sem cluster.")
    return result


def _design_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Cria uma matriz fixa, com TerQuaQui como categoria de referência."""
    dummies = pd.get_dummies(df["Cluster"], dtype=float).drop(columns=CLUSTER_BASE, errors="ignore")
    X = pd.concat([np.log(df["Preço"]).rename("ln_preco"), dummies], axis=1)
    X = sm.add_constant(X, has_constant="add")
    return X.reindex(columns=COLUNAS_MODELO, fill_value=0.0)


def fit_demand_curve(df: pd.DataFrame) -> DemandCurveModel:
    """Ajusta a curva OLS final e estima o fator global de smearing.

    O ajuste deve receber somente o conjunto de treino disponível naquele
    momento. Nenhum ponto é removido ou limitado antes da regressão.
    """
    _validate_training_data(df)
    training = _with_cluster(df)
    X = _design_matrix(training)
    y = np.log(training["Volume Realizado (kg)"])
    regression = sm.OLS(y, X).fit()
    smearing_factor = float(np.exp(regression.resid).mean())
    price_support = {
        cluster: (float(group["Preço"].min()), float(group["Preço"].max()))
        for cluster, group in training.groupby("Cluster", observed=True)
    }
    return DemandCurveModel(regression, smearing_factor, price_support)


def _validate_prediction_inputs(model: DemandCurveModel, preco: float, cluster: str) -> None:
    if preco <= 0:
        raise ValueError("Preço precisa ser estritamente positivo.")
    if cluster not in CLUSTERS:
        raise ValueError(f"Cluster não reconhecido: {cluster!r}")
    if cluster not in model.price_support:
        raise ValueError(f"O modelo não foi treinado com observações do cluster {cluster!r}.")


def is_within_price_support(model: DemandCurveModel, preco: float, cluster: str) -> bool:
    """Informa se o preço pertence ao intervalo observado no cluster."""
    _validate_prediction_inputs(model, preco, cluster)
    lower, upper = model.price_support[cluster]
    return lower <= preco <= upper


def predict_volume(
    model: DemandCurveModel,
    preco: float,
    cluster: str,
    *,
    allow_extrapolation: bool = False,
) -> float:
    """Prevê volume médio em kg com a correção global de smearing.

    Por padrão, bloqueia extrapolações, pois o EDA não validou a curva fora da
    faixa de preço observada no respectivo cluster.
    """
    _validate_prediction_inputs(model, preco, cluster)
    if not allow_extrapolation and not is_within_price_support(model, preco, cluster):
        lower, upper = model.price_support[cluster]
        raise ValueError(
            f"Preço {preco:.2f} fora do suporte observado para {cluster}: "
            f"[{lower:.2f}, {upper:.2f}]."
        )
    row = pd.DataFrame({"Preço": [preco], "Cluster": [cluster]})
    prediction_log = float(model.regression.predict(_design_matrix(row)).iloc[0])
    return float(np.exp(prediction_log) * model.smearing_factor)


def data_sha256(path: str | Path) -> str:
    """Calcula o hash SHA-256 da base exata usada no ajuste."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact(
    model: DemandCurveModel,
    training_data_path: str | Path,
    training_data: pd.DataFrame,
    *,
    code_version: str = "ols-4-intercepts-shared-elasticity-smearing-v1",
) -> DemandCurveArtifact:
    """Cria um artefato que permite auditar a origem exata da curva."""
    dates = pd.to_datetime(training_data["Data"])
    metadata = {
        "artifact_version": 1,
        "model_specification": "OLS ln(volume) ~ ln(price) + Segunda + Sexta + FimDeSemana",
        "code_version": code_version,
        "training_rows": int(len(training_data)),
        "training_period": {"start": dates.min().date().isoformat(), "end": dates.max().date().isoformat()},
        "training_data_file": Path(training_data_path).name,
        "training_data_sha256": data_sha256(training_data_path),
        "demand_curve_module_sha256": data_sha256(Path(__file__)),
        "python_pandas_version": pd.__version__,
        "statsmodels_version": sm.__version__,
    }
    return DemandCurveArtifact(
        params={key: float(value) for key, value in model.params.items()},
        smearing_factor=float(model.smearing_factor),
        price_support={key: (float(lower), float(upper)) for key, (lower, upper) in model.price_support.items()},
        metadata=metadata,
    )


def save_artifact(artifact: DemandCurveArtifact, path: str | Path) -> None:
    """Persiste o artefato em JSON legível e determinístico."""
    payload = {
        "params": dict(artifact.params),
        "smearing_factor": artifact.smearing_factor,
        "price_support": {key: list(value) for key, value in artifact.price_support.items()},
        "metadata": dict(artifact.metadata),
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_artifact(path: str | Path) -> DemandCurveArtifact:
    """Carrega o artefato JSON sem desserializar código executável."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return DemandCurveArtifact(
        params={key: float(value) for key, value in payload["params"].items()},
        smearing_factor=float(payload["smearing_factor"]),
        price_support={key: (float(value[0]), float(value[1])) for key, value in payload["price_support"].items()},
        metadata=payload["metadata"],
    )


def predict_volume_from_artifact(
    artifact: DemandCurveArtifact,
    preco: float,
    cluster: str,
    *,
    allow_extrapolation: bool = False,
) -> float:
    """Prevê em kg diretamente dos coeficientes persistidos em JSON."""
    if preco <= 0:
        raise ValueError("Preço precisa ser estritamente positivo.")
    if cluster not in CLUSTERS or cluster not in artifact.price_support:
        raise ValueError(f"Cluster não reconhecido ou ausente no artefato: {cluster!r}")
    lower, upper = artifact.price_support[cluster]
    if not allow_extrapolation and not lower <= preco <= upper:
        raise ValueError(f"Preço {preco:.2f} fora do suporte observado para {cluster}: [{lower:.2f}, {upper:.2f}].")
    params = artifact.params
    prediction_log = params["const"] + params["ln_preco"] * np.log(preco)
    if cluster != CLUSTER_BASE:
        prediction_log += params.get(cluster, 0.0)
    return float(np.exp(prediction_log) * artifact.smearing_factor)
