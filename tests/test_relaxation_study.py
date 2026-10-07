"""Testes para a Etapa 1: estrutura de Relaxation e generalização de PriceProblem."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeling.demand_curve import load_artifact
from src.optimization.price_schedule import (
    PriceProblem,
    problem_from_frames,
    select_cost_forecast,
    diagnose_feasibility,
)
from src.optimization.relaxation_study import (
    Relaxation,
    apply_relaxation,
    solve,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def minerva_problem():
    """Fixture com problema oficial da Minerva."""
    artifact = load_artifact(ROOT / "models/demand_curve_champion_livro.json")
    uncertainty = load_artifact(ROOT / "models/demand_curve_uncertainty_livro.json")
    development = pd.read_csv(
        ROOT / "data/processed/minerva_modelagem_treino.csv", parse_dates=["data"]
    )
    restrictions = pd.read_csv(ROOT / "data/interim/minerva_restricoes.csv")
    cost = select_cost_forecast(development)
    problem = problem_from_frames(
        artifact,
        restrictions,
        unit_cost=cost["forecast_cost_kg"],
        initial_price=float(development.sort_values("data")["preco_kg"].iloc[-1]),
        uncertainty=uncertainty,
    )
    return problem


class TestRelaxationStructure:
    """Testa a estrutura Relaxation e suas invariantes."""

    def test_identity_relaxation(self):
        """Uma Relaxation() com todos os fatores = 1 é identidade."""
        relax = Relaxation()
        assert relax.is_identity

    def test_partial_relaxation_not_identity(self):
        """Uma Relaxation com qualquer fator > 1 não é identidade."""
        relax = Relaxation(daily_variation_factor=1.5)
        assert not relax.is_identity

    def test_all_factors_must_be_gte_one(self):
        """Nenhum fator pode ser menor que 1."""
        with pytest.raises(ValueError, match="Fatores de variação"):
            Relaxation(daily_variation_factor=0.9)

    def test_relaxation_with_multiple_factors(self):
        """Relaxation pode ter múltiplos fatores aplicados simultaneamente."""
        relax = Relaxation(
            daily_variation_factor=2.0,
            initial_transition_factor=1.5,
            tolerance_lower_factor=1.3,
            tolerance_upper_factor=1.2,
            target_nominal_factor=1.1,
        )
        assert not relax.is_identity
        assert relax.daily_variation_factor == 2.0
        assert relax.initial_transition_factor == 1.5


class TestSeparatedTolerances:
    """Testa tolerâncias separadas em PriceProblem."""

    def test_tolerance_lower_upper_default_to_tolerance(self, minerva_problem):
        """Quando não especificadas, tolerance_lower/upper usam o valor de tolerance."""
        assert minerva_problem.tolerance_lower is None
        assert minerva_problem.tolerance_upper is None
        assert minerva_problem.tol_lower == minerva_problem.tolerance
        assert minerva_problem.tol_upper == minerva_problem.tolerance

    def test_can_create_problem_with_separated_tolerances(self, minerva_problem):
        """É possível criar um PriceProblem com tolerâncias separadas diferentes."""
        new_problem = PriceProblem(
            artifact=minerva_problem.artifact,
            dates=minerva_problem.dates,
            weekdays=minerva_problem.weekdays,
            weeks=minerva_problem.weeks,
            targets=minerva_problem.targets,
            tolerance=minerva_problem.tolerance,
            initial_price=minerva_problem.initial_price,
            daily_variation=minerva_problem.daily_variation,
            unit_cost=minerva_problem.unit_cost,
            tax_rate=minerva_problem.tax_rate,
            scenario=minerva_problem.scenario,
            uncertainty=minerva_problem.uncertainty,
            tolerance_lower=0.20,
            tolerance_upper=0.40,
        )
        assert new_problem.tol_lower == 0.20
        assert new_problem.tol_upper == 0.40

    def test_separated_tolerances_must_be_valid(self, minerva_problem):
        """Tolerâncias separadas devem estar em [0, 1)."""
        with pytest.raises(ValueError, match="Tolerâncias separadas"):
            PriceProblem(
                artifact=minerva_problem.artifact,
                dates=minerva_problem.dates,
                weekdays=minerva_problem.weekdays,
                weeks=minerva_problem.weeks,
                targets=minerva_problem.targets,
                tolerance=minerva_problem.tolerance,
                initial_price=minerva_problem.initial_price,
                daily_variation=minerva_problem.daily_variation,
                unit_cost=minerva_problem.unit_cost,
                tolerance_lower=-0.1,
            )


class TestApplyRelaxation:
    """Testa apply_relaxation mantendo compatibilidade com problema original."""

    def test_identity_relaxation_preserves_problem(self, minerva_problem):
        """Aplicar Relaxation() (identidade) deve preservar o problema."""
        relax = Relaxation()
        relaxed = apply_relaxation(minerva_problem, relax)

        assert relaxed.daily_variation == minerva_problem.daily_variation
        assert relaxed.targets == minerva_problem.targets
        assert relaxed.tol_lower == minerva_problem.tol_lower
        assert relaxed.tol_upper == minerva_problem.tol_upper

    def test_daily_variation_relaxation_scales_correctly(self, minerva_problem):
        """Fator de variação diária deve escalar daily_variation."""
        relax = Relaxation(daily_variation_factor=2.0)
        relaxed = apply_relaxation(minerva_problem, relax)

        assert relaxed.daily_variation == pytest.approx(
            minerva_problem.daily_variation * 2.0
        )

    def test_tolerance_relaxation_scales_correctly(self, minerva_problem):
        """Fatores de tolerância devem escalar as tolerâncias."""
        relax = Relaxation(
            tolerance_lower_factor=1.5,
            tolerance_upper_factor=2.0,
        )
        relaxed = apply_relaxation(minerva_problem, relax)

        assert relaxed.tol_lower == pytest.approx(
            minerva_problem.tolerance * 1.5
        )
        assert relaxed.tol_upper == pytest.approx(
            minerva_problem.tolerance * 2.0
        )

    def test_target_nominal_relaxation_scales_correctly(self, minerva_problem):
        """Fator de meta nominal deve escalar todas as metas."""
        relax = Relaxation(target_nominal_factor=0.8)
        relaxed = apply_relaxation(minerva_problem, relax)

        for week, target in minerva_problem.targets.items():
            assert relaxed.targets[week] == pytest.approx(target * 0.8)


class TestBehaviorPreservation:
    """Testa que Etapa 1 preserva comportamento de Etapa 0."""

    def test_official_problem_still_infeasible_with_identity(self, minerva_problem):
        """O problema oficial permanece infactível com Relaxation() identidade."""
        diagnostic = diagnose_feasibility(minerva_problem)
        assert diagnostic["status"] == "infeasible_targets"

    def test_separated_tolerances_not_affecting_default_behavior(self, minerva_problem):
        """Tolerâncias separadas não afetam behavior quando iguais à original."""
        relax = Relaxation()
        relaxed = apply_relaxation(minerva_problem, relax)
        diagnostic_original = diagnose_feasibility(minerva_problem)
        diagnostic_relaxed = diagnose_feasibility(relaxed)

        # Ambos devem ter mesmo status de viabilidade
        assert diagnostic_original["potentially_feasible"] == diagnostic_relaxed["potentially_feasible"]

    def test_solve_with_identity_relaxation_produces_same_result_as_optimize(self, minerva_problem):
        """solve() com identidade deve concordar com optimize_prices em infactibilidade."""
        from src.optimization.price_schedule import optimize_prices

        result_optimize = optimize_prices(minerva_problem)
        result_solve = solve(minerva_problem, Relaxation())

        assert result_optimize["status"] == result_solve["status"]
        assert result_optimize["status"] == "infeasible"


class TestSolveFunction:
    """Testa a função solve com multi-start."""

    def test_solve_with_default_relaxation(self, minerva_problem):
        """solve() sem relaxation usa Relaxation() implicitamente."""
        result = solve(minerva_problem)
        assert result["status"] == "infeasible"
        assert result["relaxation_applied"].is_identity

    def test_solve_returns_convergence_info(self, minerva_problem):
        """solve() retorna dict com convergence para cada ponto inicial (quando factível)."""
        # Use uma relaxação forte que torna o problema factível para testar convergence
        relax = Relaxation(
            daily_variation_factor=15.0,
            tolerance_lower_factor=2.0,
            tolerance_upper_factor=2.0,
        )
        result = solve(minerva_problem, relax, n_starts=5)
        assert "convergence" in result
        assert isinstance(result["convergence"], dict)
        # Com 5 starts, devem haver 5 inícios reportados
        assert len(result["convergence"]) == 5

    def test_solve_respects_n_starts_parameter(self, minerva_problem):
        """solve() usa exatamente n_starts pontos iniciais."""
        # Use uma relaxação que torna o problema factível
        relax = Relaxation(
            daily_variation_factor=15.0,
            tolerance_lower_factor=2.0,
            tolerance_upper_factor=2.0,
        )
        for n_starts in [3, 5, 10]:
            result = solve(minerva_problem, relax, n_starts=n_starts)
            assert len(result["convergence"]) == n_starts

    def test_solve_with_easier_relaxation(self, minerva_problem):
        """solve() com relaxação mais forte deve produzir resultado factível."""
        relax = Relaxation(
            daily_variation_factor=15.0,
            tolerance_lower_factor=2.0,
            tolerance_upper_factor=2.0,
        )
        result = solve(minerva_problem, relax, n_starts=3)
        assert result["status"] == "optimal"
        assert result["daily"] is not None
        assert result["weekly"] is not None
        assert result["total_margin_rs"] is not None

    def test_solve_returns_slacks_and_active_constraints(self, minerva_problem):
        """solve() retorna folgas de restrições e quais estão ativas."""
        relax = Relaxation(daily_variation_factor=10.0)
        result = solve(minerva_problem, relax, n_starts=3)
        assert "slacks" in result
        assert "active_constraints" in result
        assert isinstance(result["slacks"], dict)
        assert isinstance(result["active_constraints"], list)


class TestIsolableRelaxations:
    """Testa que R1 e R2 são isoláveis (variação diária e salto inicial)."""

    def test_r1_and_r2_are_isolable(self, minerva_problem):
        """R1 (variação diária) e R2 (salto inicial) devem ser independentes.

        daily_factor=8 com initial_factor=1 mantém o salto inicial em R$ 2.
        """
        relax = Relaxation(
            daily_variation_factor=8.0,
            initial_transition_factor=1.0,  # Sem relaxação no salto
        )
        result = solve(minerva_problem, relax, n_starts=3)

        # Mesmo que daily_variation tenha sido ampliado, initial_transition não deve
        daily = result["daily"]
        if daily is not None:
            # O salto inicial deve respeitar o initial_transition_factor
            initial_change = abs(daily["preco_kg"].iloc[0] - minerva_problem.initial_price)
            assert initial_change <= minerva_problem.daily_variation + 1e-5

    def test_r2_can_be_relaxed_independently_of_r1(self, minerva_problem):
        """R2 (salto inicial) pode ser relaxado mesmo sem relaxar R1 (variação diária)."""
        relax = Relaxation(
            daily_variation_factor=1.0,  # Sem relaxação em variação diária
            initial_transition_factor=2.5,  # Relaxação no salto inicial
        )
        result = solve(minerva_problem, relax, n_starts=3)

        # Com inicial_transition ampliado, deveria ser mais fácil ser factível
        daily = result["daily"]
        if daily is not None:
            # O salto inicial deve poder ser maior
            initial_change = abs(daily["preco_kg"].iloc[0] - minerva_problem.initial_price)
            assert initial_change <= minerva_problem.daily_variation * 2.5 + 1e-5
