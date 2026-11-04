"""Otimização contínua de preços e comparação explícita de regras operacionais.

A demanda é recebida de um artefato congelado. O solver não estima parâmetros
nem modifica o suporte estatístico; extrapolações são cenários identificados.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.demand_curve import context_for_weekday, predict_volume_from_artifact
from src.optimization.price_schedule import PriceProblem


@dataclass(frozen=True)
class Scenario:
    """Regras ativadas e condição inicial de uma comparação de políticas."""

    name: str
    enforce_daily_variation: bool = True
    enforce_weekly_targets: bool = True
    enforce_initial_anchor: bool = True
    extrapolate: bool = False
    initial_price: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("O cenário precisa de um nome.")
        if self.initial_price is not None and (
            not np.isfinite(self.initial_price) or self.initial_price <= 0
        ):
            raise ValueError("O preço inicial hipotético precisa ser finito e positivo.")


def _warm_prices(
    problem: PriceProblem,
    scenario: Scenario,
    lower: np.ndarray,
    upper: np.ndarray,
    qref: np.ndarray,
    beta: float,
    reference: float,
    initial_price: float,
) -> np.ndarray | None:
    """Propõe uma política; somente pontos factíveis são enviados como início."""
    lo, hi = lower.copy(), upper.copy()
    if scenario.enforce_initial_anchor:
        lo[0] = max(lo[0], initial_price - problem.init_var)
        hi[0] = min(hi[0], initial_price + problem.init_var)
    if scenario.enforce_daily_variation:
        delta = problem.daily_variation
        for t in range(1, problem.n_days):
            lo[t] = max(lo[t], lo[t - 1] - delta)
            hi[t] = min(hi[t], hi[t - 1] + delta)
        for t in range(problem.n_days - 2, -1, -1):
            lo[t] = max(lo[t], lo[t + 1] - delta)
            hi[t] = min(hi[t], hi[t + 1] + delta)
    if np.any(lo > hi):
        return None

    rho = 1 + 1 / beta
    prices = np.clip(problem.costs / ((1 - problem.tax_rate) * rho), lo, hi)
    if scenario.enforce_weekly_targets and np.ptp(problem.costs) < 1e-9:
        for week, target in problem.targets.items():
            mask = np.asarray(problem.weeks) == week
            unconstrained_volume = np.sum(qref[mask] * (prices[mask] / reference) ** beta)
            desired_volume = np.clip(
                unconstrained_volume,
                target * (1 - problem.tol_lower),
                target * (1 + problem.tol_upper),
            )
            constant_price = reference * (desired_volume / qref[mask].sum()) ** (1 / beta)
            prices[mask] = np.clip(constant_price, lo[mask], hi[mask])
    if scenario.enforce_daily_variation:
        for t in range(1, problem.n_days):
            prices[t] = np.clip(
                prices[t],
                max(lo[t], prices[t - 1] - problem.daily_variation),
                min(hi[t], prices[t - 1] + problem.daily_variation),
            )
    volumes = qref * (prices / reference) ** beta
    if scenario.enforce_weekly_targets:
        for week, target in problem.targets.items():
            volume = volumes[np.asarray(problem.weeks) == week].sum()
            if (
                not target * (1 - problem.tol_lower) - 1e-6
                <= volume
                <= (target * (1 + problem.tol_upper) + 1e-6)
            ):
                return None
    return prices


def solve_scenario(
    problem: PriceProblem,
    scenario: Scenario,
    *,
    time_limit: float = 30,
    mip_gap: float = 1e-6,
    extrapolation_bounds: tuple[float, float] = (800.0, 2000.0),
) -> dict[str, Any]:
    """Resolve e verifica uma política com curva de potência e elasticidade < -1.

    A variação interna e a ligação inicial são regras independentes. Sem suporte
    estatístico, os limites técnicos positivos continuam finitos e são informados
    no resultado. Valores em reais e kg são recalculados pela inferência canônica.
    """
    try:
        import gurobipy as gp
    except ImportError as exc:
        raise ImportError("Instale gurobipy para executar a otimização de preços.") from exc

    if problem.artifact["family"] != "power":
        raise ValueError("A formulação exige uma curva de demanda de potência.")
    beta = float(problem.artifact["coefficients"]["ln_preco"])
    if beta >= -1:
        raise ValueError("A formulação de receita exige elasticidade menor que -1.")
    if problem.day_rule != "decision":
        raise ValueError("A regra de variação deve usar decisões consecutivas.")
    if not np.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("O limite de tempo precisa ser positivo e finito.")
    if not np.isfinite(mip_gap) or not 0 < mip_gap < 1:
        raise ValueError("O gap precisa estar no intervalo (0, 1).")
    technical_lower, technical_upper = map(float, extrapolation_bounds)
    if not 0 < technical_lower < technical_upper < np.inf:
        raise ValueError("Os limites técnicos de extrapolação devem ser positivos e finitos.")

    reference = 1300.0
    n = problem.n_days
    contexts = [context_for_weekday(problem.artifact, d) for d in problem.weekdays]
    support = problem.artifact["price_support"]
    observed_lower = np.array([support[c]["min"] for c in contexts], dtype=float)
    observed_upper = np.array([support[c]["max"] for c in contexts], dtype=float)
    lower = np.full(n, technical_lower) if scenario.extrapolate else observed_lower.copy()
    upper = np.full(n, technical_upper) if scenario.extrapolate else observed_upper.copy()
    initial_price = (
        problem.initial_price if scenario.initial_price is None else scenario.initial_price
    )
    qref = np.array(
        [
            predict_volume_from_artifact(
                problem.artifact,
                reference,
                d,
                scenario=problem.scenario,
                uncertainty=problem.uncertainty,
            )
            for d in problem.weekdays
        ]
    )
    qmin = qref * (upper / reference) ** beta
    qmax = qref * (lower / reference) ** beta
    rho = 1 + 1 / beta
    result: dict[str, Any] = {
        "scenario": asdict(scenario),
        "initial_price": float(initial_price),
        "model_core_sha256": problem.artifact.get("model_core_sha256"),
        "solver_version": ".".join(map(str, gp.gurobi.version())),
        "price_reference": reference,
        "extrapolation_bounds": [technical_lower, technical_upper]
        if scenario.extrapolate
        else None,
        "status": "no_solution",
        "status_code": None,
        "runtime": None,
        "gap": None,
        "bound_rs": None,
        "objective_rs": None,
        "total_margin_rs": None,
        "daily": None,
        "weekly": None,
        "validation": None,
    }

    try:
        with gp.Env(empty=True) as env:
            env.setParam("OutputFlag", 0)
            env.start()
            with gp.Model("precificacao", env=env) as model:
                model.Params.OutputFlag = 0
                model.Params.TimeLimit = time_limit
                model.Params.MIPGap = mip_gap
                model.Params.MIPGapAbs = 1e-6  # Mil reais: equivale a R$ 0,001.
                model.Params.FeasibilityTol = 1e-8
                model.Params.DualReductions = 0
                u = [
                    model.addVar(lb=lower[t] / reference, ub=upper[t] / reference, name=f"u_{t}")
                    for t in range(n)
                ]
                q = [model.addVar(lb=qmin[t], ub=qmax[t], name=f"q_{t}") for t in range(n)]
                rmax = (1 - problem.tax_rate) * reference * qref * (qmax / qref) ** rho / 1000
                revenue = [model.addVar(lb=0, ub=rmax[t], name=f"receita_{t}") for t in range(n)]
                for t in range(n):
                    model.addGenConstrNL(q[t], float(qref[t]) * u[t] ** beta, name=f"demanda_{t}")
                    # Inversão exata da mesma curva: receita côncava em volume.
                    model.addGenConstrNL(
                        revenue[t],
                        (1 - problem.tax_rate)
                        * reference
                        * float(qref[t])
                        * (q[t] / float(qref[t])) ** rho
                        / 1000,
                        name=f"receita_liquida_{t}",
                    )
                    if t and scenario.enforce_daily_variation:
                        difference = reference * (u[t] - u[t - 1])
                        model.addConstr(
                            difference <= problem.daily_variation, name=f"variacao_max_{t}"
                        )
                        model.addConstr(
                            difference >= -problem.daily_variation, name=f"variacao_min_{t}"
                        )
                if scenario.enforce_initial_anchor:
                    change = reference * u[0] - initial_price
                    model.addConstr(change <= problem.init_var, name="transicao_inicial_max")
                    model.addConstr(change >= -problem.init_var, name="transicao_inicial_min")
                if scenario.enforce_weekly_targets:
                    for week, target in problem.targets.items():
                        total = gp.quicksum(q[t] for t in range(n) if problem.weeks[t] == week)
                        model.addConstr(
                            total >= target * (1 - problem.tol_lower), name=f"meta_min_{week}"
                        )
                        model.addConstr(
                            total <= target * (1 + problem.tol_upper), name=f"meta_max_{week}"
                        )
                model.setObjective(
                    gp.quicksum(revenue)
                    - gp.quicksum(float(problem.costs[t]) * q[t] / 1000 for t in range(n)),
                    gp.GRB.MAXIMIZE,
                )
                warm = _warm_prices(
                    problem, scenario, lower, upper, qref, beta, reference, initial_price
                )
                if warm is not None:
                    for t in range(n):
                        volume = float(qref[t] * (warm[t] / reference) ** beta)
                        u[t].Start = warm[t] / reference
                        q[t].Start = volume
                        revenue[t].Start = (1 - problem.tax_rate) * warm[t] * volume / 1000
                model.optimize()
                result.update(status_code=model.Status, runtime=model.Runtime)
                if model.Status == gp.GRB.INFEASIBLE:
                    result["status"] = "infeasible"
                    return result
                if model.SolCount == 0:
                    result["termination"] = (
                        "time_limit" if model.Status == gp.GRB.TIME_LIMIT else "no_incumbent"
                    )
                    return result
                result["status"] = {
                    gp.GRB.OPTIMAL: "optimal",
                    gp.GRB.TIME_LIMIT: "feasible_time_limit",
                    gp.GRB.SUBOPTIMAL: "feasible_suboptimal",
                }.get(model.Status, "feasible_unproven")
                for key, attribute, scale in [
                    ("gap", "MIPGap", 1),
                    ("bound_rs", "ObjBound", 1000),
                    ("objective_rs", "ObjVal", 1000),
                ]:
                    value = float(getattr(model, attribute)) * scale
                    result[key] = value if np.isfinite(value) else None
                prices = np.array([v.X * reference for v in u])
                solver_volumes = np.array([v.X for v in q])
                solver_revenue = np.array([v.X * 1000 for v in revenue])
    except gp.GurobiError as exc:
        result.update(status="error", error_code=exc.errno, error=str(exc))
        return result

    raw_domain_violation = float(np.maximum(lower - prices, prices - upper).clip(min=0).max())
    if raw_domain_violation <= 1e-5:
        prices = np.clip(prices, lower, upper)
    volumes = np.array(
        [
            predict_volume_from_artifact(
                problem.artifact,
                float(price),
                weekday,
                scenario=problem.scenario,
                uncertainty=problem.uncertainty,
                allow_extrapolation=scenario.extrapolate,
            )
            for price, weekday in zip(prices, problem.weekdays, strict=True)
        ]
    )
    margin = ((1 - problem.tax_rate) * prices - problem.costs) * volumes
    changes = np.diff(prices, prepend=initial_price)
    outside = (prices < observed_lower - 1e-5) | (prices > observed_upper + 1e-5)
    daily = pd.DataFrame(
        {
            "data": problem.dates,
            "dia_semana": problem.weekdays,
            "semana": problem.weeks,
            "contexto": contexts,
            "preco_kg": prices,
            "volume_previsto_kg": volumes,
            "custo_kg": problem.costs,
            "aliquota_imposto": problem.tax_rate,
            "imposto": problem.tax_rate,
            "imposto_rs": problem.tax_rate * prices * volumes,
            "margem_prevista_rs": margin,
            "extrapolado": outside,
            "variacao_preco_rs": changes,
            "preco_min_suporte_kg": observed_lower,
            "preco_max_suporte_kg": observed_upper,
        }
    )
    weekly = daily.groupby("semana", sort=False).agg(
        volume_previsto_kg=("volume_previsto_kg", "sum"),
        margem_prevista_rs=("margem_prevista_rs", "sum"),
        preco_medio_kg=("preco_kg", "mean"),
        dias_extrapolados=("extrapolado", "sum"),
    )
    weekly["meta_kg"] = pd.Series(problem.targets)
    weekly["limite_inferior_kg"] = weekly["meta_kg"] * (1 - problem.tol_lower)
    weekly["limite_superior_kg"] = weekly["meta_kg"] * (1 + problem.tol_upper)
    weekly["folga_inferior_kg"] = weekly["volume_previsto_kg"] - weekly["limite_inferior_kg"]
    weekly["folga_superior_kg"] = weekly["limite_superior_kg"] - weekly["volume_previsto_kg"]
    weekly["meta_atendida"] = (weekly["folga_inferior_kg"] >= -1e-4) & (
        weekly["folga_superior_kg"] >= -1e-4
    )
    weekly["meta_ativa"] = scenario.enforce_weekly_targets
    weekly = weekly.reset_index()
    demand_residual = float(np.max(np.abs(volumes - solver_volumes)))
    revenue_residual = float(
        np.max(np.abs((1 - problem.tax_rate) * prices * volumes - solver_revenue))
    )
    margin_residual = float(abs(margin.sum() - result["objective_rs"]))
    variation_ok = bool(np.all(abs(changes[1:]) <= problem.daily_variation + 1e-4))
    initial_ok = bool(abs(changes[0]) <= problem.init_var + 1e-4)
    targets_ok = bool(weekly["meta_atendida"].all())
    bounds_ok = raw_domain_violation <= 1e-5
    validation = {
        "bounds_ok": bounds_ok,
        "support_ok": bool(not outside.any()),
        "variation_ok": variation_ok,
        "initial_ok": initial_ok,
        "targets_ok": targets_ok,
        "required_variation_ok": variation_ok or not scenario.enforce_daily_variation,
        "required_initial_ok": initial_ok or not scenario.enforce_initial_anchor,
        "required_targets_ok": targets_ok or not scenario.enforce_weekly_targets,
        "active_constraints": {
            "price_support": not scenario.extrapolate,
            "daily_variation": scenario.enforce_daily_variation,
            "weekly_targets": scenario.enforce_weekly_targets,
            "initial_anchor": scenario.enforce_initial_anchor,
        },
        "max_daily_change_rs": float(np.max(abs(changes[1:]))) if n > 1 else 0.0,
        "initial_change_rs": float(abs(changes[0])),
        "demand_residual_kg": demand_residual,
        "revenue_residual_rs": revenue_residual,
        "margin_residual_rs": margin_residual,
        "solver_domain_violation_rs": raw_domain_violation,
    }
    validation["satisfied"] = bool(
        bounds_ok
        and validation["required_variation_ok"]
        and validation["required_initial_ok"]
        and validation["required_targets_ok"]
        and demand_residual <= 1e-4
        and revenue_residual <= 0.02
        and margin_residual <= 0.02
    )
    result.update(
        total_margin_rs=float(margin.sum()), daily=daily, weekly=weekly, validation=validation
    )
    if not validation["satisfied"]:
        result["status"] = "validation_failed"
    return result
