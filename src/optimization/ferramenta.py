"""Planejamento de preços para entradas informadas pelo usuário.

A ferramenta reaproveita o problema congelado das entradas de planejamento e substitui somente
os valores escolhidos na interface. Curva, custo de referência e conferências continuam sendo os
do solver; as regras relaxadas são declaradas no resultado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from src.optimization.gurobi_solver import Scenario, solve_scenario
from src.optimization.price_schedule import PriceProblem, diagnose_feasibility

TOLERANCIA_ATIVA = 1e-3

REGRAS_RELAXAVEIS = {
    "primeira_mudanca": "Limite da primeira mudança de preço",
    "entre_dias": "Limite de variação entre dias consecutivos",
    "minimo_semanal": "Volume mínimo semanal",
    "maximo_semanal": "Volume máximo semanal",
    "faixa_precos": "Faixa de preços observada no treino",
}

STATUS_TEXTO = {
    "optimal": "Melhor solução confirmada dentro da tolerância",
    "feasible_time_limit": "Plano válido; tempo de busca esgotado",
    "feasible_suboptimal": "Plano válido; melhor solução não confirmada",
    "feasible_unproven": "Plano válido; melhor solução não confirmada",
    "infeasible": "Não existe plano com essas regras",
    "no_solution": "Busca encerrada sem encontrar plano",
    "validation_failed": "Plano reprovado na conferência",
    "error": "Erro no cálculo",
}


def cenario_da_ferramenta(relaxadas: frozenset[str]) -> Scenario:
    """Converte as regras marcadas como relaxadas em um cenário do solver."""
    desconhecidas = set(relaxadas) - set(REGRAS_RELAXAVEIS)
    if desconhecidas:
        raise ValueError(f"Regras desconhecidas: {sorted(desconhecidas)}")
    nome = (
        "Relaxadas: " + "; ".join(REGRAS_RELAXAVEIS[regra] for regra in sorted(relaxadas))
        if relaxadas
        else "Regras originais"
    )
    return Scenario(
        name=nome,
        enforce_initial_anchor="primeira_mudanca" not in relaxadas,
        enforce_daily_variation="entre_dias" not in relaxadas,
        enforce_weekly_minimum="minimo_semanal" not in relaxadas,
        enforce_weekly_maximum="maximo_semanal" not in relaxadas,
        extrapolate="faixa_precos" in relaxadas,
    )


def problema_da_ferramenta(
    base: PriceProblem,
    *,
    valor_anterior: float,
    variacao_primeira: float,
    variacao_diaria: float,
    meta: float,
    tolerancia_inferior: float,
    tolerancia_superior: float,
    custo: float | Sequence[float],
    imposto: float,
) -> PriceProblem:
    """Substitui os valores informados mantendo o horizonte e a curva congelados.

    O custo pode ser único ou ter um valor por dia do horizonte.
    """
    return replace(
        base,
        initial_price=valor_anterior,
        initial_variation=variacao_primeira,
        daily_variation=variacao_diaria,
        targets={semana: meta for semana in base.targets},
        tolerance=tolerancia_inferior,
        tolerance_lower=tolerancia_inferior,
        tolerance_upper=tolerancia_superior,
        unit_cost=custo,
        tax_rate=imposto,
    )


def planejar(
    problem: PriceProblem,
    relaxadas: frozenset[str] = frozenset(),
    *,
    tempo_limite: float = 30,
) -> dict[str, Any]:
    """Resolve o problema com as regras indicadas e devolve tabelas e diagnósticos."""
    cenario = cenario_da_ferramenta(relaxadas)
    resultado = solve_scenario(problem, cenario, time_limit=tempo_limite, mip_gap=1e-6)
    saida: dict[str, Any] = {
        "cenario": cenario.name,
        "relaxadas": frozenset(relaxadas),
        "status": resultado["status"],
        "status_texto": STATUS_TEXTO.get(resultado["status"], resultado["status"]),
        "margem_total_rs": resultado["total_margin_rs"],
        "gap": resultado["gap"],
        "tempo_s": resultado["runtime"],
        "diario": resultado["daily"],
        "semanal": resultado["weekly"],
        "diagnostico": None,
    }
    if resultado["status"] == "infeasible":
        saida["diagnostico"] = _diagnostico(problem, cenario)
    return saida


def _diagnostico(problem: PriceProblem, cenario: Scenario) -> Any:
    """Mostra o maior volume alcançável por semana com as regras de preço que permanecem."""
    diagnostico = diagnose_feasibility(
        problem,
        initial_delta=problem.init_var if cenario.enforce_initial_anchor else None,
        daily_delta=problem.daily_variation if cenario.enforce_daily_variation else None,
    )
    return diagnostico["weeks"]


def restricoes_da_solucao(problem: PriceProblem, resultado: dict[str, Any]) -> pd.DataFrame:
    """Mostra quais limites estão encostados na solução e quanto a margem melhoraria
    se cada um fosse relaxado sozinho, mantendo as demais regras do plano.

    Só deve ser chamada com um plano válido. A folga é medida na unidade de cada regra
    (kg para volume, R$/kg para variação de preço e faixa de preços). Quando relaxar uma
    regra sozinha não gera plano, o ganho fica vazio e a linha indica isso.
    """
    if resultado["diario"] is None:
        raise ValueError("A análise de restrições exige um plano válido.")
    relaxadas = resultado["relaxadas"]
    diario = resultado["diario"]
    semanal = resultado["semanal"]
    precos = diario["preco_kg"].to_numpy(float)
    variacao = diario["variacao_preco_rs"].to_numpy(float)
    dias = diario["data"].dt.strftime("%d/%m").to_numpy()
    semanas = semanal["semana"].str.replace("_", " ").to_numpy()
    margem_base = float(resultado["margem_total_rs"])

    folgas: dict[str, tuple[np.ndarray, np.ndarray, str]] = {}
    if "minimo_semanal" not in relaxadas:
        folga = semanal["volume_previsto_kg"].to_numpy(float) - semanal[
            "limite_inferior_kg"
        ].to_numpy(float)
        folgas["minimo_semanal"] = (folga, semanas, "kg")
    if "maximo_semanal" not in relaxadas:
        folga = semanal["limite_superior_kg"].to_numpy(float) - semanal[
            "volume_previsto_kg"
        ].to_numpy(float)
        folgas["maximo_semanal"] = (folga, semanas, "kg")
    if "primeira_mudanca" not in relaxadas:
        folga = np.array([problem.init_var - abs(variacao[0])])
        folgas["primeira_mudanca"] = (folga, dias[:1], "R$/kg")
    if "entre_dias" not in relaxadas:
        folga = problem.daily_variation - np.abs(variacao[1:])
        folgas["entre_dias"] = (folga, dias[1:], "R$/kg")
    if "faixa_precos" not in relaxadas:
        suporte_min = diario["preco_min_suporte_kg"].to_numpy(float)
        suporte_max = diario["preco_max_suporte_kg"].to_numpy(float)
        folga = np.minimum(precos - suporte_min, suporte_max - precos)
        folgas["faixa_precos"] = (folga, dias, "R$/kg")

    linhas = []
    for regra, (folga, rotulos, unidade) in folgas.items():
        ativos = folga < TOLERANCIA_ATIVA
        if ativos.any():
            onde = ", ".join(rotulos[ativos])
            situacao = "Ativa"
            margem_relaxada = planejar(problem, relaxadas | {regra})["margem_total_rs"]
            ganho = None if margem_relaxada is None else margem_relaxada - margem_base
        else:
            onde = f"menor folga: {folga.min():.2f} {unidade}"
            situacao = "Folga"
            ganho = None
        linhas.append(
            {
                "regra": regra,
                "limite": REGRAS_RELAXAVEIS[regra],
                "situacao": situacao,
                "onde": onde,
                "ganho_ao_relaxar_rs": ganho,
            }
        )
    for regra in relaxadas:
        linhas.append(
            {
                "regra": regra,
                "limite": REGRAS_RELAXAVEIS[regra],
                "situacao": "Relaxada",
                "onde": "",
                "ganho_ao_relaxar_rs": None,
            }
        )
    tabela = pd.DataFrame(linhas)
    return tabela.sort_values(
        ["situacao", "ganho_ao_relaxar_rs"], ascending=[True, False], na_position="last"
    ).reset_index(drop=True)
