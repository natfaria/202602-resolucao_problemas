"""Flexibilizações graduais das regras de preço e volume com a mesma curva congelada."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from src.optimization.gurobi_solver import Scenario, solve_scenario
from src.optimization.price_schedule import PriceProblem, diagnose_feasibility


@dataclass(frozen=True)
class Relaxation:
    """Multiplica limites de mudança e tolerâncias; a meta nominal admite sensibilidade.

    Aumentar uma tolerância flexibiliza somente seu lado da faixa. Alterar a meta
    nominal desloca os dois lados e não constitui uma relaxação monotônica.
    """

    daily_variation_factor: float = 1.0
    initial_transition_factor: float = 1.0
    tolerance_lower_factor: float = 1.0
    tolerance_upper_factor: float = 1.0
    target_nominal_factor: float = 1.0

    def __post_init__(self) -> None:
        values = np.array(list(asdict(self).values()), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Os fatores devem ser finitos.")
        if (values[:4] < 1).any():
            raise ValueError("Fatores de variação e tolerância devem ser >= 1.")
        if self.target_nominal_factor <= 0:
            raise ValueError("O fator de meta nominal deve ser positivo.")

    @property
    def is_identity(self) -> bool:
        return all(value == 1 for value in asdict(self).values())


def apply_relaxation(problem: PriceProblem, relaxation: Relaxation) -> PriceProblem:
    """Produz entradas independentes, mantendo custo, curva e preço anterior observados."""
    return replace(
        problem,
        daily_variation=problem.daily_variation * relaxation.daily_variation_factor,
        initial_variation=problem.init_var * relaxation.initial_transition_factor,
        tolerance_lower=problem.tol_lower * relaxation.tolerance_lower_factor,
        tolerance_upper=problem.tol_upper * relaxation.tolerance_upper_factor,
        targets={w: q * relaxation.target_nominal_factor for w, q in problem.targets.items()},
    )


def solve(
    problem: PriceProblem,
    relaxation: Relaxation | None = None,
    *,
    enforce_initial: bool = True,
    enforce_variation: bool = True,
    enforce_targets: bool = True,
    time_limit: float = 30,
    mip_gap: float = 1e-6,
) -> dict[str, Any]:
    """Resolve e verifica com Gurobi; envelopes podem certificar a inviabilidade.

    Um envelope que intercepta a faixa semanal é apenas uma condição necessária.
    A factibilidade é confirmada por um plano que passa na verificação do solver.
    """
    relaxation = Relaxation() if relaxation is None else relaxation
    relaxed = apply_relaxation(problem, relaxation)
    diagnostic = diagnose_feasibility(
        relaxed,
        initial_delta=relaxed.init_var if enforce_initial else None,
        daily_delta=relaxed.daily_variation if enforce_variation else None,
    )
    scenario = Scenario(
        "Flexibilização declarada",
        enforce_daily_variation=enforce_variation,
        enforce_weekly_targets=enforce_targets,
        enforce_initial_anchor=enforce_initial,
    )
    if enforce_targets and diagnostic["status"] == "infeasible_targets":
        result = {
            "scenario": asdict(scenario),
            "initial_price": relaxed.initial_price,
            "model_core_sha256": relaxed.artifact.get("model_core_sha256"),
            "status": "infeasible",
            "status_code": None,
            "runtime": 0.0,
            "gap": None,
            "bound_rs": None,
            "objective_rs": None,
            "total_margin_rs": None,
            "daily": None,
            "weekly": None,
            "validation": None,
            "certificate": "reachable_volume_bounds",
        }
    else:
        result = solve_scenario(relaxed, scenario, time_limit=time_limit, mip_gap=mip_gap)
        result["certificate"] = "gurobi" if result["status"] in {"optimal", "infeasible"} else None
    result["diagnostics"] = diagnostic
    result["relaxation_applied"] = asdict(relaxation)
    result["parameters"] = {
        "daily_variation": relaxed.daily_variation,
        "initial_variation": relaxed.init_var,
        "tolerance_lower": relaxed.tol_lower,
        "tolerance_upper": relaxed.tol_upper,
        "targets": dict(relaxed.targets),
    }
    return result


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    """Conserva status, certificado e folgas; não converte ausência de solução em inviabilidade."""
    params = result["parameters"]
    row = {
        "case_id": result.get("case_id"),
        "status": result["status"],
        "certificate": result["certificate"],
        "margem_prevista_rs": result["total_margin_rs"],
        "limite_superior_margem_rs": result["bound_rs"],
        "gap": result["gap"],
        "tempo_solver_s": result["runtime"],
        "variacao_interna_rs": params["daily_variation"],
        "transicao_inicial_rs": params["initial_variation"],
        "tolerancia_inferior": params["tolerance_lower"],
        "tolerancia_superior": params["tolerance_upper"],
        "ligacao_inicial_ativa": result["scenario"]["enforce_initial_anchor"],
        "variacao_interna_ativa": result["scenario"]["enforce_daily_variation"],
        "metas_ativas": result["scenario"]["enforce_weekly_targets"],
        "model_core_sha256": result["model_core_sha256"],
        "plano_verificado": bool(result["validation"] and result["validation"]["satisfied"]),
    }
    for w, target in params["targets"].items():
        bounds = result["diagnostics"]["weeks"].get(w, {})
        row.update(
            {
                f"{w}_meta_kg": target,
                f"{w}_piso_kg": target * (1 - params["tolerance_lower"]),
                f"{w}_teto_kg": target * (1 + params["tolerance_upper"]),
                f"{w}_volume_minimo_alcancavel_kg": bounds.get("minimum_reachable_kg"),
                f"{w}_volume_maximo_alcancavel_kg": bounds.get("maximum_reachable_kg"),
                f"{w}_deficit_piso_kg": bounds.get("shortage_kg"),
                f"{w}_excesso_teto_kg": bounds.get("excess_kg"),
            }
        )
        if result["weekly"] is not None:
            week = result["weekly"].set_index("semana").loc[w]
            row.update(
                {
                    f"{w}_volume_previsto_kg": float(week["volume_previsto_kg"]),
                    f"{w}_folga_piso_kg": float(week["folga_inferior_kg"]),
                    f"{w}_folga_teto_kg": float(week["folga_superior_kg"]),
                }
            )
    return row


class RelaxationStudy:
    """Reutiliza resultados de entradas idênticas dentro de um estudo congelado."""

    def __init__(
        self,
        problem: PriceProblem,
        *,
        time_limit: float = 30,
        mip_gap: float = 1e-6,
        daily_variation_ceiling: float | None = None,
        initial_transition_ceiling: float | None = None,
    ):
        self.problem = problem
        self.time_limit = time_limit
        self.mip_gap = mip_gap
        self.daily_variation_ceiling = daily_variation_ceiling
        self.initial_transition_ceiling = initial_transition_ceiling
        for value, nominal in [
            (daily_variation_ceiling, problem.daily_variation),
            (initial_transition_ceiling, problem.init_var),
        ]:
            if value is not None and (not np.isfinite(value) or value < nominal):
                raise ValueError("O teto comercial deve ser finito e não inferior ao nominal.")
        self.results: dict[tuple, dict[str, Any]] = {}

    def evaluate(
        self,
        relaxation: Relaxation | None = None,
        *,
        enforce_initial: bool = True,
        enforce_variation: bool = True,
        enforce_targets: bool = True,
    ) -> dict[str, Any]:
        relaxation = Relaxation() if relaxation is None else relaxation
        if self.daily_variation_ceiling is not None and not enforce_variation:
            raise ValueError("A variação interna não pode ser removida quando há teto comercial.")
        if self.daily_variation_ceiling is not None and (
            self.problem.daily_variation * relaxation.daily_variation_factor
            > self.daily_variation_ceiling + 1e-9
        ):
            raise ValueError("A variação interna excede o teto comercial recebido.")
        if self.initial_transition_ceiling is not None and (
            self.problem.init_var * relaxation.initial_transition_factor
            > self.initial_transition_ceiling + 1e-9
        ):
            raise ValueError("A primeira mudança excede seu teto comercial recebido.")
        key = (*asdict(relaxation).values(), enforce_initial, enforce_variation, enforce_targets)
        if key not in self.results:
            result = solve(
                self.problem,
                relaxation,
                enforce_initial=enforce_initial,
                enforce_variation=enforce_variation,
                enforce_targets=enforce_targets,
                time_limit=self.time_limit,
                mip_gap=self.mip_gap,
            )
            result["case_id"] = f"c{len(self.results):04d}"
            self.results[key] = result
        return self.results[key]

    def relaxation_at(self, rule: str, value: float) -> Relaxation:
        """Recebe valores absolutos de R$/kg ou frações de tolerância."""
        names = {
            "daily_variation": ("daily_variation_factor", self.problem.daily_variation),
            "initial_transition": ("initial_transition_factor", self.problem.init_var),
            "tolerance_lower": ("tolerance_lower_factor", self.problem.tol_lower),
            "tolerance_upper": ("tolerance_upper_factor", self.problem.tol_upper),
        }
        if rule not in names:
            raise ValueError(f"Regra desconhecida: {rule}")
        name, nominal = names[rule]
        if nominal <= 0:
            raise ValueError("A parametrização por fatores exige limite nominal positivo.")
        return Relaxation(**{name: float(value) / nominal})

    def minimum(
        self,
        rule: str,
        *,
        upper: float,
        precision: float = 1e-3,
    ) -> dict[str, Any]:
        """Delimita o mínimo entre um caso inviável provado e um plano factível.

        Somente limites que geram conjuntos admissíveis aninhados são aceitos.
        Alterar a meta nominal não possui essa propriedade.
        """
        nominal = {
            "daily_variation": self.problem.daily_variation,
            "initial_transition": self.problem.init_var,
            "tolerance_lower": self.problem.tol_lower,
            "tolerance_upper": self.problem.tol_upper,
        }
        if rule not in nominal:
            raise ValueError("O mínimo exige uma regra de flexibilização monotônica.")
        if not np.isfinite(upper) or not np.isfinite(precision) or precision <= 0:
            raise ValueError("Limite superior e precisão devem ser finitos; precisão positiva.")
        low, high = nominal[rule], float(upper)
        if high <= low:
            raise ValueError("O limite superior deve superar o nominal.")

        def decision(value):
            result = self.evaluate(self.relaxation_at(rule, value))
            if result["validation"] and result["validation"]["satisfied"]:
                return True, result
            if result["status"] == "infeasible":
                return False, result
            raise RuntimeError(
                f"Viabilidade não determinada: {result['status']} em {rule}={value}."
            )

        base_ok, base = decision(low)
        high_ok, high_result = decision(high)
        if base_ok:
            return {
                "rule": rule,
                "status": "already_feasible",
                "minimum": low,
                "infeasible_value": None,
                "feasible_value": low,
                "precision": precision,
                "case_id": base["case_id"],
                "margem_prevista_rs": base["total_margin_rs"],
            }
        if not high_ok:
            return {
                "rule": rule,
                "status": "no_recovery_in_range",
                "minimum": None,
                "infeasible_value": high,
                "feasible_value": None,
                "precision": precision,
                "case_id": high_result["case_id"],
                "margem_prevista_rs": None,
            }
        while high - low > precision:
            middle = (low + high) / 2
            ok, result = decision(middle)
            if ok:
                high, high_result = middle, result
            else:
                low = middle
        return {
            "rule": rule,
            "status": "bracketed",
            "minimum": high,
            "infeasible_value": low,
            "feasible_value": high,
            "precision": precision,
            "case_id": high_result["case_id"],
            "margem_prevista_rs": high_result["total_margin_rs"],
        }

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(summarize(result) for result in self.results.values())


def pareto_feasible(frame: pd.DataFrame, costs: list[str]) -> pd.DataFrame:
    """Retorna combinações factíveis não dominadas nas folgas operacionais da grade.

    A margem é reportada, mas não entra na dominância entre as alterações de regra.
    """
    candidates = frame.loc[frame["plano_verificado"]].copy()
    if candidates.empty:
        return candidates
    values = candidates[costs].to_numpy(dtype=float)
    keep = [
        not np.any(np.all(values <= row + 1e-9, axis=1) & np.any(values < row - 1e-9, axis=1))
        for row in values
    ]
    return candidates.loc[keep].sort_values(costs).reset_index(drop=True)


def compare_margin_relaxations(
    frame: pd.DataFrame,
    costs: list[str],
    *,
    margin_tolerance: float = 0.10,
    cost_tolerance: float = 1e-8,
) -> pd.DataFrame:
    """Compara quatro folgas operacionais e margem, sem somar unidades distintas.

    A domina B se exige folgas não maiores e sua margem alcança o limitante de B,
    dentro da equivalência monetária declarada. Uma folga deve ser menor ou a
    margem deve superar o limitante além dessa equivalência. Somente planos
    verificados com ótimo certificado participam. O caso dominante é registrado.
    """
    if not np.isfinite(margin_tolerance) or margin_tolerance < 0:
        raise ValueError("A equivalência de margem deve ser finita e não negativa.")
    if not np.isfinite(cost_tolerance) or cost_tolerance < 0:
        raise ValueError("A tolerância das folgas deve ser finita e não negativa.")
    compared = frame.drop_duplicates("case_id").copy().reset_index(drop=True)
    compared["dominancia_financeira"] = "nao_comparado"
    compared["caso_dominante"] = None
    eligible = compared["plano_verificado"] & compared["status"].eq("optimal")
    candidates = compared.loc[eligible]
    values = candidates[costs].to_numpy(dtype=float)
    profits = candidates["margem_prevista_rs"].to_numpy(dtype=float)
    bounds = candidates["limite_superior_margem_rs"].to_numpy(dtype=float)
    if (
        not np.isfinite(values).all()
        or not np.isfinite(profits).all()
        or not np.isfinite(bounds).all()
    ):
        raise ValueError("A comparação exige folgas, margens e limitantes finitos.")
    for position, (index, row) in enumerate(candidates.iterrows()):
        smaller_costs = np.any(values < values[position] - cost_tolerance, axis=1)
        no_larger_costs = np.all(values <= values[position] + cost_tolerance, axis=1)
        no_worse_margin = profits >= bounds[position] - margin_tolerance
        strictly_higher_margin = profits > bounds[position] + margin_tolerance
        dominates = no_larger_costs & no_worse_margin & (smaller_costs | strictly_higher_margin)
        dominates[position] = False
        witnesses = np.flatnonzero(dominates)
        compared.loc[index, "dominancia_financeira"] = (
            "dominado" if len(witnesses) else "eficiente"
        )
        if len(witnesses):
            witness = witnesses[np.argmax(profits[witnesses])]
            compared.loc[index, "caso_dominante"] = candidates.iloc[witness]["case_id"]
    return compared
