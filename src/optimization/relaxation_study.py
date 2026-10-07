"""Estudo de relaxações para recuperar factibilidade com máxima margem.

Este módulo estende o otimizador de preços base para explorar combinações
de folgas em variação diária, transição inicial, metas e tolerâncias.
Mantém compatibilidade com PriceProblem e introduce a estrutura Relaxation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.optimization.price_schedule import (
    PriceProblem,
    _nonlinear_constraints,
    demand_vector,
    diagnose_feasibility,
    margin_vector,
    price_bounds,
    reachable_price_path,
    validate_prices,
)


@dataclass(frozen=True)
class Relaxation:
    """Descreve todas as folgas de uma rodada de otimização.

    Todos os fatores são multiplicadores (≥1) sobre o valor nominal.
    fator=1 significa sem relaxação; fator>1 significa afrouxamento.
    """

    daily_variation_factor: float = 1.0
    initial_transition_factor: float = 1.0
    tolerance_lower_factor: float = 1.0
    tolerance_upper_factor: float = 1.0
    target_nominal_factor: float = 1.0

    def __post_init__(self) -> None:
        # Variação e tolerância: devem ser >= 1.0 (maior = mais fácil)
        if not all(f >= 1.0 for f in [
            self.daily_variation_factor,
            self.initial_transition_factor,
            self.tolerance_lower_factor,
            self.tolerance_upper_factor,
        ]):
            raise ValueError("Fatores de variação e tolerância devem ser ≥ 1.0.")
        # Meta nominal pode ser reduzida ou aumentada (fator > 0)
        if self.target_nominal_factor <= 0:
            raise ValueError("Fator de meta nominal deve ser > 0.")

    @property
    def is_identity(self) -> bool:
        """True se nenhuma relaxação foi aplicada (todos os fatores = 1.0)."""
        return all(f == 1.0 for f in [
            self.daily_variation_factor,
            self.initial_transition_factor,
            self.tolerance_lower_factor,
            self.tolerance_upper_factor,
            self.target_nominal_factor,
        ])


def apply_relaxation(problem: PriceProblem, relaxation: Relaxation) -> PriceProblem:
    """Cria um novo PriceProblem com as relaxações aplicadas.

    Mantém o comportamento padrão: se relaxation.is_identity,
    retorna um problema equivalente ao original.

    O salto inicial (R2) é independente da variação diária (R1):
    - daily_variation é multiplicado por daily_variation_factor
    - initial_transition é nominal * initial_transition_factor
    """
    # Variação diária (R1)
    new_daily_variation = problem.daily_variation * relaxation.daily_variation_factor

    # Tolerâncias separadas (R3/R4/R5)
    tolerance_lower = problem.tol_lower * relaxation.tolerance_lower_factor
    tolerance_upper = problem.tol_upper * relaxation.tolerance_upper_factor

    # Metas nominais por semana (R5)
    new_targets = {
        week: target * relaxation.target_nominal_factor
        for week, target in problem.targets.items()
    }

    return PriceProblem(
        artifact=problem.artifact,
        dates=problem.dates,
        weekdays=problem.weekdays,
        weeks=problem.weeks,
        targets=new_targets,
        tolerance=problem.tolerance,
        initial_price=problem.initial_price,
        daily_variation=new_daily_variation,
        unit_cost=problem.unit_cost,
        tax_rate=problem.tax_rate,
        scenario=problem.scenario,
        uncertainty=problem.uncertainty,
        tolerance_lower=tolerance_lower if tolerance_lower != problem.tolerance else None,
        tolerance_upper=tolerance_upper if tolerance_upper != problem.tolerance else None,
    )


def _generate_initial_points(
    low: np.ndarray,
    high: np.ndarray,
    n_starts: int,
    seed: int = 42,
) -> list[np.ndarray]:
    """Gera n_starts pontos iniciais com diversidade de pesos por dia.

    Retorna:
    - 3 pontos determinísticos: baixo, alto, médio
    - (n_starts - 3) pontos com pesos diferentes por dia (não apenas combinação linear)
    """
    rng = np.random.default_rng(seed)
    starts = [np.copy(low), np.copy(high), (low + high) / 2]

    if n_starts > 3:
        n_random = n_starts - 3

        for _ in range(n_random):
            # Gerar pesos diferentes para cada dia, não só uma combinação linear
            weights = rng.uniform(0, 1, len(low))
            start = low * weights + high * (1 - weights)
            starts.append(start)

    return starts


def _multistart_optimization(
    problem: PriceProblem,
    initial_delta: float | None,
    daily_delta: float | None,
    enforce_targets: bool,
    n_starts: int = 10,
    seed: int = 42,
) -> dict[str, Any]:
    """Executa otimização multi-start e retorna candidatos e convergência.

    Retorna:
    - candidates: lista de (margin, result, checks) ordenada por margem
    - convergence: dict com status de cada ponto inicial
    """
    low = reachable_price_path(
        problem,
        direction="low",
        initial_delta=initial_delta,
        daily_delta=daily_delta,
    )
    high = reachable_price_path(
        problem,
        direction="high",
        initial_delta=initial_delta,
        daily_delta=daily_delta,
    )

    if low is None or high is None:
        return {
            "candidates": [],
            "convergence": {},
            "feasible": False,
        }

    # Gerar pontos iniciais com diversidade
    starts = _generate_initial_points(low, high, n_starts, seed=seed)

    # Resolver com cada ponto inicial
    convergence = {}
    candidates = []

    constraints = _nonlinear_constraints(
        problem,
        initial_delta=initial_delta,
        daily_delta=daily_delta,
        enforce_targets=enforce_targets,
    )
    bounds = price_bounds(problem)

    for i, start in enumerate(starts):
        result = minimize(
            lambda prices: -float(margin_vector(problem, prices).sum()),
            np.asarray(start),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1500},
        )

        checks = validate_prices(
            problem,
            result.x,
            initial_delta=initial_delta,
            daily_delta=daily_delta,
            enforce_targets=enforce_targets,
        )

        total_margin = float(margin_vector(problem, result.x).sum())
        convergence[f"start_{i}"] = {
            "margin_rs": total_margin,
            "satisfied": checks["satisfied"],
        }

        if checks["satisfied"]:
            candidates.append((total_margin, result, checks))

    return {
        "candidates": candidates,
        "convergence": convergence,
        "feasible": len(candidates) > 0,
    }


def solve(
    problem: PriceProblem,
    relaxation: Relaxation | None = None,
    *,
    n_starts: int = 10,
    seed: int = 42,
    enforce_initial: bool = True,
    enforce_variation: bool = True,
    enforce_targets: bool = True,
) -> dict[str, Any]:
    """Resolve o problema com relaxações aplicadas, usando n_starts pontos iniciais.

    Quando relaxation=None, usa Relaxation() (identidade, sem folgas).

    R1 e R2 são isoláveis:
    - R1 (variação diária): problem.daily_variation * daily_variation_factor
    - R2 (salto inicial): problem.daily_variation * initial_transition_factor

    Retorna:
    - status: 'optimal', 'infeasible', 'solver_failed'
    - daily: DataFrame com preços, volumes e margem (None se infactível)
    - weekly: Dict com volumes e margens por semana
    - total_margin_rs: Margem total acumulada
    - diagnostics: Detalhes de restrições e envelopes
    - convergence: Dict com margens alcançadas por cada ponto inicial
    - relaxation_applied: A instância de Relaxation usada
    - slacks: Folgas de cada restrição
    - active_constraints: Restrições ativas
    """
    if relaxation is None:
        relaxation = Relaxation()

    # Aplicar relaxações ao problema
    relaxed_problem = apply_relaxation(problem, relaxation)

    # Executar diagnóstico
    # R2 (salto inicial) é independente de R1 (variação diária)
    initial_delta = (
        problem.daily_variation * relaxation.initial_transition_factor
        if enforce_initial
        else None
    )
    # R1 (variação diária)
    daily_delta = relaxed_problem.daily_variation if enforce_variation else None

    diagnostic = diagnose_feasibility(
        relaxed_problem, initial_delta=initial_delta, daily_delta=daily_delta
    )

    if enforce_targets and not diagnostic["potentially_feasible"]:
        return {
            "status": "infeasible",
            "daily": None,
            "weekly": None,
            "total_margin_rs": None,
            "diagnostics": diagnostic,
            "convergence": {},
            "relaxation_applied": relaxation,
            "slacks": {},
            "active_constraints": [],
        }

    # Multi-start
    result = _multistart_optimization(
        relaxed_problem,
        initial_delta=initial_delta,
        daily_delta=daily_delta,
        enforce_targets=enforce_targets,
        n_starts=n_starts,
        seed=seed,
    )

    if not result["feasible"]:
        return {
            "status": "solver_failed",
            "daily": None,
            "weekly": None,
            "total_margin_rs": None,
            "diagnostics": diagnostic,
            "convergence": result["convergence"],
            "relaxation_applied": relaxation,
            "slacks": {},
            "active_constraints": [],
        }

    # Melhor candidato
    total_margin, optimizer_result, checks = max(
        result["candidates"], key=lambda item: item[0]
    )
    prices = np.asarray(optimizer_result.x)
    volumes = demand_vector(relaxed_problem, prices)
    margins = margin_vector(relaxed_problem, prices)

    daily = pd.DataFrame(
        {
            "data": relaxed_problem.dates,
            "dia_semana": relaxed_problem.weekdays,
            "semana": relaxed_problem.weeks,
            "preco_kg": prices,
            "volume_previsto_kg": volumes,
            "custo_kg": relaxed_problem.costs,
            "margem_rs": margins,
        }
    )

    weekly = {}
    for week in dict.fromkeys(relaxed_problem.weeks):
        mask = np.array(relaxed_problem.weeks) == week
        weekly[week] = {
            "volume_kg": float(volumes[mask].sum()),
            "margem_rs": float(margins[mask].sum()),
            "target_kg": relaxed_problem.targets[week],
        }

    # Extrair folgas e restrições ativas de validate_prices
    slacks = {
        "support": checks["minimum_support_slack"],
        "initial_change": initial_delta - checks["initial_change"] if initial_delta else None,
        "maximum_daily_change": (
            daily_delta - checks["maximum_daily_change"] if daily_delta else None
        ),
        "weeks": checks["weeks"],
    }

    active_constraints = []
    if initial_delta and checks["initial_change"] >= initial_delta - 1e-6:
        active_constraints.append("initial_transition")
    if daily_delta and checks["maximum_daily_change"] >= daily_delta - 1e-6:
        active_constraints.append("daily_variation")
    for week, week_check in checks["weeks"].items():
        if week_check["lower_slack_kg"] <= 1e-6:
            active_constraints.append(f"target_lower_{week}")
        if week_check["upper_slack_kg"] <= 1e-6:
            active_constraints.append(f"target_upper_{week}")

    return {
        "status": "optimal",
        "daily": daily,
        "weekly": weekly,
        "total_margin_rs": total_margin,
        "diagnostics": diagnostic,
        "convergence": result["convergence"],
        "relaxation_applied": relaxation,
        "slacks": slacks,
        "active_constraints": active_constraints,
    }
