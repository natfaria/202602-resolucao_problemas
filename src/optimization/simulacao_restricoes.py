"""Simulação ao vivo das flexibilizações de uma restrição, com o solver do projeto."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.optimization.gurobi_solver import Scenario, solve_scenario
from src.optimization.planning_inputs import load_planning_inputs
from src.optimization.relaxation_study import RelaxationStudy

TEMPO_LIMITE = 30
GAP = 1e-6
RÓTULOS = {
    "tolerance_lower": "Mínimo semanal",
    "initial_transition": "Primeiro valor",
    "daily_variation": "Limite entre dias",
    "tolerance_upper": "Máximo semanal",
}


def carregar_problema(raiz: Path):
    problema, _ = load_planning_inputs(raiz / "models/otimizacao/entradas_planejamento.json", root=raiz)
    return problema


def grades(problema) -> dict[str, list[float]]:
    return {
        "tolerance_lower": [problema.tol_lower] + list(np.arange(0.35, 0.951, 0.05)),
        "initial_transition": [problema.init_var] + list(np.arange(5.0, 120.01, 5.0)),
        "daily_variation": [problema.daily_variation] + list(np.arange(4.0, 120.01, 4.0)),
        "tolerance_upper": [problema.tol_upper] + list(np.arange(0.35, 0.951, 0.05)),
    }


def simular_uma_restricao(problema) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve cada flexibilização isolada e a menor flexibilização com plano (bisseção)."""
    estudo = RelaxationStudy(problema, time_limit=TEMPO_LIMITE, mip_gap=GAP)
    linhas = []
    limiares = []
    for regra, valores in grades(problema).items():
        tolerancia = regra.startswith("tolerance")
        limiar = estudo.minimum(regra, upper=0.95 if tolerancia else 120.0,
                                precision=1e-6 if tolerancia else 1e-3)
        limiares.append({"Restrição": RÓTULOS[regra], "Status": limiar["status"],
                         "Menor valor com plano": limiar["minimum"],
                         "Margem no menor valor (R$)": limiar.get("margem_prevista_rs")})
        for valor in sorted(set(valores)):
            resultado = estudo.evaluate(estudo.relaxation_at(regra, float(valor)))
            linhas.append({
                "regra": regra, "Restrição": RÓTULOS[regra], "valor": float(valor),
                "Status": "Com plano" if resultado["status"] == "optimal" else "Sem plano",
                "Margem prevista (R$)": resultado["total_margin_rs"],
            })
    return pd.DataFrame(linhas), pd.DataFrame(limiares)


def simular_preco_anterior(problema) -> pd.DataFrame:
    linhas = []
    for preco in np.arange(1200.0, 1320.01, 2.0):
        resultado = solve_scenario(problema, Scenario(f"Preço anterior {preco:.2f}", initial_price=float(preco)),
                                   time_limit=TEMPO_LIMITE, mip_gap=GAP)
        linhas.append({"Preço anterior (R$/kg)": float(preco),
                       "Status": "Com plano" if resultado["status"] == "optimal" else "Sem plano",
                       "Margem prevista (R$)": resultado["total_margin_rs"]})
    return pd.DataFrame(linhas)

