"""Cenários determinísticos de premissas, separados das flexibilizações de regras."""

from copy import deepcopy
from dataclasses import replace

import numpy as np

from src.modeling.demand_curve import model_core_sha256
from src.optimization.price_schedule import PriceProblem


def assumption_problem(
    problem: PriceProblem,
    *,
    demand_factor: float = 1.0,
    cost_factor: float = 1.0,
    tax_rate: float | None = None,
    elasticity: float | None = None,
    reference_price: float = 1300.0,
) -> PriceProblem:
    """Cria uma instância independente, preservando as regras e o artefato original.

    Alterar a elasticidade gira a curva em torno do volume central em R$ 1.300/kg
    em cada contexto. O multiplicador de demanda desloca o nível dessa curva.
    São hipóteses de estresse, sem probabilidades ou cobertura conjunta de confiança.
    """
    if problem.artifact["family"] != "power" or problem.scenario != "central":
        raise ValueError("A sensibilidade exige a curva central de potência.")
    if (
        not np.isfinite([demand_factor, cost_factor, reference_price]).all()
        or min(demand_factor, cost_factor, reference_price) <= 0
    ):
        raise ValueError("Fatores e preço de referência devem ser positivos e finitos.")
    curve = deepcopy(dict(problem.artifact))
    old_beta = float(curve["coefficients"]["ln_preco"])
    beta = old_beta if elasticity is None else float(elasticity)
    if not np.isfinite(beta) or beta >= -1:
        raise ValueError("A elasticidade deve ser finita e menor que -1 para este solver.")
    curve["coefficients"]["const"] += (old_beta - beta) * np.log(reference_price)
    curve["coefficients"]["ln_preco"] = beta
    curve["smearing_factor"] *= demand_factor
    if beta != old_beta or demand_factor != 1:
        curve["model_id"] = f"{curve['model_id']}-stress-{demand_factor:g}-{beta:g}"
        curve["sensitivity"] = {
            "base_model_core_sha256": problem.artifact["model_core_sha256"],
            "demand_factor": demand_factor,
            "elasticity": beta,
            "pivot_price": reference_price,
            "interpretation": "deterministic_stress_not_prediction_interval",
        }
    curve["model_core_sha256"] = model_core_sha256(curve)
    return replace(
        problem,
        artifact=curve,
        unit_cost=problem.costs * cost_factor,
        tax_rate=problem.tax_rate if tax_rate is None else tax_rate,
        uncertainty=None,
    )
