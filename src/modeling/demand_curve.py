"""Curva final de demanda preço-volume.

Especificação definida no EDA:

``ln(volume) = intercepto_do_cluster + beta * ln(preço) + erro``

O modelo usa OLS, quatro interceptos de nível e uma elasticidade compartilhada.
As previsões retornam em quilogramas com correção global de smearing de Duan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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
