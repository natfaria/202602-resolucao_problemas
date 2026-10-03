"""Diagnóstico de viabilidade e otimização da agenda diária de preços.

O módulo mantém separados três problemas: previsão de custo sem vazamento,
diagnóstico determinístico das restrições e maximização de margem somente
quando a formulação é viável.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

from src.modeling.demand_curve import (
    context_for_weekday,
    predict_volume_from_artifact,
    validate_artifact,
)

Artifact = Mapping[str, Any]
_DEFAULT = object()

WEEKDAY_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}

COST_METHOD_LABELS = {
    "ultimo": "Último custo unitário",
    "media_1_semana": "Média ponderada — 1 semana",
    "media_2_semanas": "Média ponderada — 2 semanas",
    "media_4_semanas": "Média ponderada — 4 semanas",
    "media_expansiva": "Média ponderada expansiva",
    "media_exponencial": "Média móvel exponencial (α=0,30)",
}


@dataclass(frozen=True)
class PriceProblem:
    """Entradas congeladas de um problema de preço."""

    artifact: Artifact
    dates: tuple[pd.Timestamp, ...]
    weekdays: tuple[str, ...]
    weeks: tuple[str, ...]
    targets: Mapping[str, float]
    tolerance: float
    initial_price: float
    daily_variation: float
    unit_cost: float | Sequence[float]
    tax_rate: float = 0.07
    scenario: str = "central"
    uncertainty: Artifact | None = None

    def __post_init__(self) -> None:
        validate_artifact(self.artifact)
        n = len(self.dates)
        if not n or len(self.weekdays) != n or len(self.weeks) != n:
            raise ValueError("Datas, dias da semana e semanas precisam ter o mesmo tamanho positivo.")
        if set(self.weeks) != set(self.targets):
            raise ValueError("Cada semana do horizonte precisa ter uma meta.")
        if not 0 <= self.tolerance < 1:
            raise ValueError("A tolerância precisa estar no intervalo [0, 1).")
        if not 0 <= self.tax_rate < 1:
            raise ValueError("A alíquota precisa estar no intervalo [0, 1).")
        if self.initial_price <= 0 or self.daily_variation < 0:
            raise ValueError("Preço inicial deve ser positivo e variação não pode ser negativa.")
        costs = np.asarray(self.unit_cost, dtype=float)
        if costs.ndim > 1 or (costs.size not in {1, n}) or np.any(costs <= 0):
            raise ValueError("Custo deve ser positivo, escalar ou possuir um valor por dia.")

    @property
    def n_days(self) -> int:
        return len(self.dates)

    @property
    def costs(self) -> np.ndarray:
        values = np.asarray(self.unit_cost, dtype=float)
        return np.repeat(values.item(), self.n_days) if values.size == 1 else values.copy()


def build_horizon(start: str | pd.Timestamp = "2025-11-03", periods: int = 10) -> pd.DataFrame:
    """Cria o horizonte oficial de dias úteis e seus identificadores semanais."""
    dates = pd.bdate_range(start=pd.Timestamp(start), periods=periods)
    iso = dates.isocalendar()
    first_week = int(iso.week.iloc[0])
    return pd.DataFrame(
        {
            "data": dates,
            "dia_semana": [WEEKDAY_PT[date.weekday()] for date in dates],
            "semana": [f"semana_{int(week) - first_week + 1}" for week in iso.week],
        }
    )


def problem_from_frames(
    artifact: Artifact,
    restrictions: pd.DataFrame,
    *,
    horizon: pd.DataFrame | None = None,
    unit_cost: float | Sequence[float],
    initial_price: float,
    tax_rate: float = 0.07,
    scenario: str = "central",
    uncertainty: Artifact | None = None,
) -> PriceProblem:
    """Monta o contrato do otimizador usando as restrições lidas da instância."""
    horizon = build_horizon() if horizon is None else horizon.copy()
    required = {
        "Semana",
        "Meta (kg)",
        "Tolerância %",
        "Variação Máxima Preço Entre Dias Consecutivos (R$)",
    }
    missing = required - set(restrictions)
    if missing:
        raise ValueError(f"Tabela de restrições sem colunas: {sorted(missing)}")
    tolerances = restrictions["Tolerância %"].astype(float).unique()
    variations = restrictions[
        "Variação Máxima Preço Entre Dias Consecutivos (R$)"
    ].astype(float).unique()
    if len(tolerances) != 1 or len(variations) != 1:
        raise ValueError("Tolerância e variação precisam ser únicas no horizonte.")
    targets = dict(
        zip(restrictions["Semana"], restrictions["Meta (kg)"].astype(float), strict=True)
    )
    return PriceProblem(
        artifact=dict(artifact),
        dates=tuple(pd.to_datetime(horizon["data"])),
        weekdays=tuple(horizon["dia_semana"].astype(str)),
        weeks=tuple(horizon["semana"].astype(str)),
        targets=targets,
        tolerance=float(tolerances[0]),
        initial_price=float(initial_price),
        daily_variation=float(variations[0]),
        unit_cost=unit_cost,
        tax_rate=tax_rate,
        scenario=scenario,
        uncertainty=uncertainty,
    )


def _weighted_cost(frame: pd.DataFrame) -> float:
    volume = float(frame["volume_kg"].sum())
    if volume <= 0:
        raise ValueError("A janela de custo não possui volume positivo.")
    return float(frame["custo_rs"].sum() / volume)


def _cost_candidates(history: pd.DataFrame, cutoff: pd.Timestamp) -> dict[str, float]:
    past = history.loc[history["data"] <= cutoff].sort_values("data")
    if past.empty:
        raise ValueError("Não há histórico disponível no corte informado.")
    candidates = {
        "ultimo": float(past["custo_kg"].iloc[-1]),
        "media_expansiva": _weighted_cost(past),
        "media_exponencial": float(
            past["custo_kg"].ewm(alpha=0.30, adjust=False).mean().iloc[-1]
        ),
    }
    for weeks in (1, 2, 4):
        window = past.loc[past["data"] > cutoff - pd.Timedelta(weeks=weeks)]
        candidates[f"media_{weeks}_semana" if weeks == 1 else f"media_{weeks}_semanas"] = (
            _weighted_cost(window)
        )
    return candidates


def validate_cost_forecasts(
    development: pd.DataFrame,
    *,
    horizon_days: int = 14,
    minimum_history_days: int = 28,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara previsores de custo em origens móveis sem consultar o holdout."""
    required = {"data", "volume_kg", "custo_rs", "custo_kg"}
    missing = required - set(development)
    if missing:
        raise ValueError(f"Base de custo sem colunas: {sorted(missing)}")
    data = development.loc[:, sorted(required)].copy()
    data["data"] = pd.to_datetime(data["data"])
    data = data.sort_values("data")
    start = data["data"].min() + pd.Timedelta(days=minimum_history_days)
    last_cutoff = data["data"].max() - pd.Timedelta(days=horizon_days)
    cutoffs = data.loc[
        (data["data"].dt.weekday == 4)
        & (data["data"] >= start)
        & (data["data"] <= last_cutoff),
        "data",
    ]
    rows: list[dict[str, Any]] = []
    for cutoff in cutoffs:
        future = data.loc[
            (data["data"] > cutoff)
            & (data["data"] <= cutoff + pd.Timedelta(days=horizon_days))
        ]
        if future.empty:
            continue
        actual = _weighted_cost(future)
        for method, prediction in _cost_candidates(data, cutoff).items():
            error = prediction - actual
            rows.append(
                {
                    "data_corte": cutoff,
                    "metodo": method,
                    "previsao_custo_kg": prediction,
                    "realizado_custo_kg": actual,
                    "erro": error,
                    "erro_absoluto": abs(error),
                }
            )
    details = pd.DataFrame(rows)
    if details.empty:
        raise ValueError("Histórico insuficiente para a validação temporal de custo.")
    summary = (
        details.groupby("metodo", as_index=False)
        .agg(
            MAE=("erro_absoluto", "mean"),
            RMSE=("erro", lambda values: float(np.sqrt(np.mean(np.square(values))))),
            vies=("erro", "mean"),
            desvio_erro=("erro", "std"),
            janelas=("erro", "size"),
        )
        .sort_values(["MAE", "metodo"])
        .reset_index(drop=True)
    )
    best_mae = float(summary["MAE"].min())
    summary["equivalente_5pct"] = summary["MAE"] <= best_mae * 1.05
    summary["rotulo"] = summary["metodo"].map(COST_METHOD_LABELS)
    return details, summary


def select_cost_forecast(development: pd.DataFrame) -> dict[str, Any]:
    """Seleciona e congela o custo futuro pela regra pré-registrada."""
    details, summary = validate_cost_forecasts(development)
    equivalent = summary.loc[summary["equivalente_5pct"]].copy()
    complexity = {
        "ultimo": 0,
        "media_1_semana": 1,
        "media_2_semanas": 2,
        "media_4_semanas": 3,
        "media_expansiva": 4,
        "media_exponencial": 5,
    }
    equivalent["complexidade"] = equivalent["metodo"].map(complexity)
    # O limiar de MAE define equivalência. Dentro dele, viés e estabilidade
    # evitam escolher uma regra simples porém sistematicamente deslocada.
    winner = equivalent.sort_values(
        ["complexidade", "vies", "desvio_erro"],
        key=lambda column: column.abs() if column.name == "vies" else column,
    ).iloc[0]
    data = development.copy()
    data["data"] = pd.to_datetime(data["data"])
    cutoff = data["data"].max()
    candidates = _cost_candidates(data, cutoff)
    errors = details.loc[details["metodo"] == winner["metodo"], "erro"]
    return {
        "method": str(winner["metodo"]),
        "label": COST_METHOD_LABELS[str(winner["metodo"])],
        "forecast_cost_kg": float(candidates[str(winner["metodo"])]),
        # erro = previsão - realizado; portanto realizado plausível = previsão - erro.
        "low_cost_kg": float(candidates[str(winner["metodo"])] - errors.quantile(0.90)),
        "high_cost_kg": float(candidates[str(winner["metodo"])] - errors.quantile(0.10)),
        "cutoff": cutoff.date().isoformat(),
        "details": details,
        "summary": summary,
    }


def price_bounds(problem: PriceProblem) -> list[tuple[float, float]]:
    """Obtém os limites diários diretamente do suporte congelado."""
    bounds = []
    for weekday in problem.weekdays:
        context = context_for_weekday(problem.artifact, weekday)
        support = problem.artifact["price_support"][context]
        bounds.append((float(support["min"]), float(support["max"])))
    return bounds


def demand_vector(problem: PriceProblem, prices: Sequence[float]) -> np.ndarray:
    """Recalcula a demanda diária pelo artefato, sem coeficientes duplicados."""
    if len(prices) != problem.n_days:
        raise ValueError("A agenda deve possuir um preço por dia.")
    return np.array(
        [
            predict_volume_from_artifact(
                problem.artifact,
                float(price),
                weekday,
                scenario=problem.scenario,
                uncertainty=problem.uncertainty,
            )
            for price, weekday in zip(prices, problem.weekdays, strict=True)
        ]
    )


def margin_vector(problem: PriceProblem, prices: Sequence[float]) -> np.ndarray:
    """Calcula margem após imposto e custo, linha a linha."""
    prices_array = np.asarray(prices, dtype=float)
    volumes = demand_vector(problem, prices_array)
    return ((1.0 - problem.tax_rate) * prices_array - problem.costs) * volumes


def _path_matrices(
    problem: PriceProblem,
    *,
    initial_delta: float | None,
    daily_delta: float | None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    rows: list[np.ndarray] = []
    limits: list[float] = []
    n = problem.n_days
    if initial_delta is not None:
        row = np.zeros(n)
        row[0] = 1.0
        rows.extend([row, -row])
        limits.extend(
            [problem.initial_price + initial_delta, -problem.initial_price + initial_delta]
        )
    if daily_delta is not None:
        for index in range(1, n):
            row = np.zeros(n)
            row[index] = 1.0
            row[index - 1] = -1.0
            rows.extend([row, -row])
            limits.extend([daily_delta, daily_delta])
    if not rows:
        return None, None
    return np.vstack(rows), np.asarray(limits)


def reachable_price_path(
    problem: PriceProblem,
    *,
    direction: str,
    initial_delta: float | None,
    daily_delta: float | None,
) -> np.ndarray | None:
    """Encontra o caminho componente a componente mais baixo ou mais alto alcançável."""
    if direction not in {"low", "high"}:
        raise ValueError("direction deve ser 'low' ou 'high'.")
    a_ub, b_ub = _path_matrices(
        problem, initial_delta=initial_delta, daily_delta=daily_delta
    )
    objective = np.ones(problem.n_days) * (1.0 if direction == "low" else -1.0)
    result = linprog(
        objective,
        A_ub=a_ub,
        b_ub=b_ub,
        bounds=price_bounds(problem),
        method="highs",
    )
    return np.asarray(result.x) if result.success else None


def _weekly_values(problem: PriceProblem, values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        week: float(array[np.array(problem.weeks) == week].sum())
        for week in dict.fromkeys(problem.weeks)
    }


def diagnose_feasibility(
    problem: PriceProblem,
    *,
    initial_delta: float | None | object = _DEFAULT,
    daily_delta: float | None | object = _DEFAULT,
) -> dict[str, Any]:
    """Calcula envelopes alcançáveis antes de chamar o solver de margem."""
    initial_delta = problem.daily_variation if initial_delta is _DEFAULT else initial_delta
    daily_delta = problem.daily_variation if daily_delta is _DEFAULT else daily_delta
    low_path = reachable_price_path(
        problem, direction="low", initial_delta=initial_delta, daily_delta=daily_delta
    )
    high_path = reachable_price_path(
        problem, direction="high", initial_delta=initial_delta, daily_delta=daily_delta
    )
    if low_path is None or high_path is None:
        return {
            "status": "infeasible_price_path",
            "potentially_feasible": False,
            "weeks": {},
            "low_price_path": None,
            "high_price_path": None,
            "low_path_details": [],
        }
    maximum = _weekly_values(problem, demand_vector(problem, low_path))
    minimum = _weekly_values(problem, demand_vector(problem, high_path))
    weeks: dict[str, dict[str, float | bool]] = {}
    viable = True
    for week, target in problem.targets.items():
        lower = target * (1.0 - problem.tolerance)
        upper = target * (1.0 + problem.tolerance)
        shortage = max(lower - maximum[week], 0.0)
        excess = max(minimum[week] - upper, 0.0)
        week_viable = shortage <= 1e-7 and excess <= 1e-7
        viable = viable and week_viable
        weeks[week] = {
            "target_kg": target,
            "lower_kg": lower,
            "upper_kg": upper,
            "minimum_reachable_kg": minimum[week],
            "maximum_reachable_kg": maximum[week],
            "shortage_kg": shortage,
            "shortage_pct_lower": shortage / lower if lower else 0.0,
            "excess_kg": excess,
            "potentially_feasible": week_viable,
        }
    low_path_details = []
    previous = problem.initial_price
    for index, (date, weekday, week, price, bounds) in enumerate(
        zip(
            problem.dates,
            problem.weekdays,
            problem.weeks,
            low_path,
            price_bounds(problem),
            strict=True,
        )
    ):
        applicable_delta = initial_delta if index == 0 else daily_delta
        change = abs(float(price) - float(previous))
        variation_slack = (
            None if applicable_delta is None else float(applicable_delta) - change
        )
        low_path_details.append(
            {
                "date": date.date().isoformat(),
                "weekday": weekday,
                "week": week,
                "context": context_for_weekday(problem.artifact, weekday),
                "price": float(price),
                "support_lower": bounds[0],
                "support_upper": bounds[1],
                "at_lower_support": abs(float(price) - bounds[0]) <= 1e-6,
                "absolute_change": change,
                "variation_slack": variation_slack,
                "at_variation_limit": (
                    variation_slack is not None and abs(variation_slack) <= 1e-6
                ),
            }
        )
        previous = float(price)
    return {
        "status": "potentially_feasible" if viable else "infeasible_targets",
        "potentially_feasible": viable,
        "weeks": weeks,
        "low_price_path": low_path.tolist(),
        "high_price_path": high_path.tolist(),
        "low_path_details": low_path_details,
    }


def validate_prices(
    problem: PriceProblem,
    prices: Sequence[float],
    *,
    initial_delta: float | None,
    daily_delta: float | None,
    enforce_targets: bool = True,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    """Recomputa todas as folgas de uma solução candidata."""
    values = np.asarray(prices, dtype=float)
    bounds = price_bounds(problem)
    support_slacks = [
        min(value - lower, upper - value)
        for value, (lower, upper) in zip(values, bounds, strict=True)
    ]
    initial_change = abs(values[0] - problem.initial_price)
    changes = np.abs(np.diff(values))
    volumes = demand_vector(problem, values)
    weekly = _weekly_values(problem, volumes)
    week_checks = {}
    target_ok = True
    for week, target in problem.targets.items():
        lower = target * (1.0 - problem.tolerance)
        upper = target * (1.0 + problem.tolerance)
        lower_slack = weekly[week] - lower
        upper_slack = upper - weekly[week]
        target_ok = target_ok and lower_slack >= -tolerance and upper_slack >= -tolerance
        week_checks[week] = {
            "volume_kg": weekly[week],
            "lower_slack_kg": lower_slack,
            "upper_slack_kg": upper_slack,
            "satisfied": lower_slack >= -tolerance and upper_slack >= -tolerance,
        }
    initial_ok = initial_delta is None or initial_change <= initial_delta + tolerance
    variation_ok = daily_delta is None or bool(np.all(changes <= daily_delta + tolerance))
    support_ok = min(support_slacks) >= -tolerance
    return {
        "satisfied": support_ok and initial_ok and variation_ok and (
            target_ok or not enforce_targets
        ),
        "support_ok": support_ok,
        "initial_ok": initial_ok,
        "variation_ok": variation_ok,
        "targets_ok": target_ok,
        "minimum_support_slack": float(min(support_slacks)),
        "initial_change": float(initial_change),
        "maximum_daily_change": float(changes.max()) if changes.size else 0.0,
        "weeks": week_checks,
    }


def _nonlinear_constraints(
    problem: PriceProblem,
    *,
    initial_delta: float | None,
    daily_delta: float | None,
    enforce_targets: bool,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    a_ub, b_ub = _path_matrices(
        problem, initial_delta=initial_delta, daily_delta=daily_delta
    )
    if a_ub is not None and b_ub is not None:
        constraints.append({"type": "ineq", "fun": lambda p: b_ub - a_ub @ p})
    if enforce_targets:
        for week, target in problem.targets.items():
            mask = np.array(problem.weeks) == week
            lower = target * (1.0 - problem.tolerance)
            upper = target * (1.0 + problem.tolerance)
            constraints.extend(
                [
                    {
                        "type": "ineq",
                        "fun": lambda p, m=mask, bound=lower: demand_vector(problem, p)[m].sum()
                        - bound,
                    },
                    {
                        "type": "ineq",
                        "fun": lambda p, m=mask, bound=upper: bound
                        - demand_vector(problem, p)[m].sum(),
                    },
                ]
            )
    return constraints


def optimize_prices(
    problem: PriceProblem,
    *,
    initial_delta: float | None = None,
    daily_delta: float | None = None,
    enforce_initial: bool = True,
    enforce_variation: bool = True,
    enforce_targets: bool = True,
    seed: int = 42,
) -> dict[str, Any]:
    """Maximiza margem e nunca devolve plano para uma formulação infactível."""
    initial_delta = (
        problem.daily_variation if initial_delta is None and enforce_initial else initial_delta
    )
    daily_delta = (
        problem.daily_variation if daily_delta is None and enforce_variation else daily_delta
    )
    if not enforce_initial:
        initial_delta = None
    if not enforce_variation:
        daily_delta = None
    diagnostic = diagnose_feasibility(
        problem, initial_delta=initial_delta, daily_delta=daily_delta
    )
    if enforce_targets and not diagnostic["potentially_feasible"]:
        return {
            "status": "infeasible",
            "message": "As metas ficam fora do envelope alcançável.",
            "diagnostic": diagnostic,
            "daily": None,
            "weekly": None,
            "total_margin_rs": None,
        }

    low = reachable_price_path(
        problem, direction="low", initial_delta=initial_delta, daily_delta=daily_delta
    )
    high = reachable_price_path(
        problem, direction="high", initial_delta=initial_delta, daily_delta=daily_delta
    )
    if low is None or high is None:
        return {
            "status": "infeasible",
            "message": "Não existe trajetória de preços dentro do suporte.",
            "diagnostic": diagnostic,
            "daily": None,
            "weekly": None,
            "total_margin_rs": None,
        }
    rng = np.random.default_rng(seed)
    starts = [low, high, (low + high) / 2]
    starts.extend((weight * low + (1 - weight) * high) for weight in rng.uniform(0, 1, 5))
    constraints = _nonlinear_constraints(
        problem,
        initial_delta=initial_delta,
        daily_delta=daily_delta,
        enforce_targets=enforce_targets,
    )
    candidates = []
    for start in starts:
        result = minimize(
            lambda prices: -float(margin_vector(problem, prices).sum()),
            np.asarray(start),
            method="SLSQP",
            bounds=price_bounds(problem),
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
        if checks["satisfied"]:
            candidates.append((float(margin_vector(problem, result.x).sum()), result, checks))
    if not candidates:
        return {
            "status": "solver_failed",
            "message": "O envelope permite a meta, mas nenhuma solução numérica foi validada.",
            "diagnostic": diagnostic,
            "daily": None,
            "weekly": None,
            "total_margin_rs": None,
        }
    total_margin, result, checks = max(candidates, key=lambda item: item[0])
    prices = np.asarray(result.x)
    volumes = demand_vector(problem, prices)
    margins = margin_vector(problem, prices)
    daily = pd.DataFrame(
        {
            "data": problem.dates,
            "dia_semana": problem.weekdays,
            "semana": problem.weeks,
            "preco_kg": prices,
            "volume_previsto_kg": volumes,
            "custo_kg": problem.costs,
            "aliquota_imposto": problem.tax_rate,
            "margem_prevista_rs": margins,
            "variacao_preco_rs": np.r_[prices[0] - problem.initial_price, np.diff(prices)],
        }
    )
    weekly = (
        daily.groupby("semana", as_index=False)
        .agg(
            volume_previsto_kg=("volume_previsto_kg", "sum"),
            margem_prevista_rs=("margem_prevista_rs", "sum"),
            preco_medio_kg=("preco_kg", "mean"),
        )
    )
    weekly["meta_kg"] = weekly["semana"].map(problem.targets)
    weekly["limite_inferior_kg"] = weekly["meta_kg"] * (1 - problem.tolerance)
    weekly["limite_superior_kg"] = weekly["meta_kg"] * (1 + problem.tolerance)
    return {
        "status": "optimal",
        "message": str(result.message),
        "diagnostic": diagnostic,
        "daily": daily,
        "weekly": weekly,
        "total_margin_rs": total_margin,
        "validation": checks,
        "initial_delta": initial_delta,
        "daily_delta": daily_delta,
    }


def minimum_relaxation(
    problem: PriceProblem,
    *,
    kind: str,
    upper: float = 512.0,
    precision: float = 1e-4,
) -> dict[str, Any]:
    """Minimiza uma relaxação de preço e só então maximiza a margem."""
    if kind not in {"daily_variation", "initial_transition"}:
        raise ValueError("Relaxação deve ser 'daily_variation' ou 'initial_transition'.")

    def diagnostic_at(value: float) -> dict[str, Any]:
        if kind == "daily_variation":
            return diagnose_feasibility(problem, initial_delta=value, daily_delta=value)
        return diagnose_feasibility(
            problem, initial_delta=value, daily_delta=problem.daily_variation
        )

    low, high = 0.0, max(problem.daily_variation, 1.0)
    while high < upper and not diagnostic_at(high)["potentially_feasible"]:
        high *= 2.0
    if not diagnostic_at(high)["potentially_feasible"]:
        return {"status": "infeasible", "minimum": None, "solution": None}
    while high - low > precision:
        middle = (low + high) / 2.0
        if diagnostic_at(middle)["potentially_feasible"]:
            high = middle
        else:
            low = middle
    minimum = high + precision
    if kind == "daily_variation":
        solution = optimize_prices(
            problem, initial_delta=minimum, daily_delta=minimum
        )
    else:
        solution = optimize_prices(
            problem,
            initial_delta=minimum,
            daily_delta=problem.daily_variation,
        )
    return {"status": solution["status"], "minimum": minimum, "solution": solution}


def volume_relaxations(problem: PriceProblem) -> dict[str, Any]:
    """Calcula as menores alterações de volume mantendo as regras de preço oficiais."""
    diagnostic = diagnose_feasibility(problem)
    maximums = {
        week: float(values["maximum_reachable_kg"])
        for week, values in diagnostic["weeks"].items()
    }
    common_target = min(
        maximums[week] / (1.0 - problem.tolerance) for week in problem.targets
    )
    tolerance = max(
        1.0 - maximums[week] / problem.targets[week] for week in problem.targets
    )
    return {
        "weekly_shortage_kg": {
            week: max(
                problem.targets[week] * (1.0 - problem.tolerance) - maximums[week],
                0.0,
            )
            for week in problem.targets
        },
        "maximum_common_target_kg": float(common_target),
        "minimum_common_tolerance": float(max(tolerance, 0.0)),
        "maximum_weekly_volume_kg": maximums,
    }


def pareto_relaxations(
    problem: PriceProblem,
    *,
    initial_grid: Sequence[float],
    daily_grid: Sequence[float],
) -> pd.DataFrame:
    """Constrói uma fronteira não dominada entre duas relaxações e déficit."""
    rows = []
    for initial_delta in initial_grid:
        for daily_delta in daily_grid:
            diagnostic = diagnose_feasibility(
                problem, initial_delta=initial_delta, daily_delta=daily_delta
            )
            shortage = sum(
                float(values["shortage_kg"]) for values in diagnostic["weeks"].values()
            )
            rows.append(
                {
                    "salto_inicial_max_rs": float(initial_delta),
                    "variacao_diaria_max_rs": float(daily_delta),
                    "deficit_total_kg": shortage,
                }
            )
    candidates = pd.DataFrame(rows).drop_duplicates()
    non_dominated = []
    values = candidates.to_numpy(dtype=float)
    for index, row in enumerate(values):
        dominated = np.any(
            np.all(values <= row + 1e-9, axis=1)
            & np.any(values < row - 1e-9, axis=1)
            & (np.arange(len(values)) != index)
        )
        non_dominated.append(not dominated)
    return candidates.loc[non_dominated].sort_values(
        ["deficit_total_kg", "salto_inicial_max_rs", "variacao_diaria_max_rs"]
    ).reset_index(drop=True)
