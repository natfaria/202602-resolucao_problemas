"""Diagnóstico de viabilidade: menor flexibilização de cada regra que permite um plano."""

from __future__ import annotations

import pandas as pd

from src.optimization.relaxation_study import RelaxationStudy

REGRAS_DIAGNOSTICO = [
    # (nome interno, rótulo para a operação, limite da busca, precisão)
    ("initial_transition", "Limite da primeira mudança de preço (R$/kg)", 120.0, 1e-3),
    ("daily_variation", "Limite de variação entre dias (R$/kg)", 120.0, 1e-3),
    ("tolerance_lower", "Mínimo semanal (kg)", 0.95, 1e-6),
    ("tolerance_upper", "Máximo semanal (kg)", 0.95, 1e-6),
]


def diagnosticar(problema, *, tempo_limite: float = 30, mip_gap: float = 1e-6) -> pd.DataFrame:
    """Para cada regra, sozinha, procura o menor valor que permite um plano.

    Cada linha informa o menor valor com plano, a margem prevista nesse ponto e
    a situação. Quando nenhum valor até o limite da busca dá plano, a linha diz isso.
    """
    estudo = RelaxationStudy(problema, time_limit=tempo_limite, mip_gap=mip_gap)
    if estudo.evaluate()["status"] == "optimal":
        return pd.DataFrame(
            [
                {
                    "Regra": "Todas as regras originais",
                    "Menor valor com plano": None,
                    "Margem no menor valor (R$)": None,
                    "Situação": "Já existe plano; nenhuma regra precisa ser flexibilizada",
                }
            ]
        )
    meta = float(next(iter(problema.targets.values())))
    linhas = []
    for regra, rotulo, limite, precisao in REGRAS_DIAGNOSTICO:
        tolerancia = regra.startswith("tolerance")
        limiar = estudo.minimum(regra, upper=limite, precision=precisao)
        if limiar["status"] == "bracketed":
            valor = limiar["minimum"]
            if regra == "tolerance_lower":
                valor = meta * (1 - valor)
            elif regra == "tolerance_upper":
                valor = meta * (1 + valor)
            situacao = "Plano a partir deste valor"
            margem = limiar["margem_prevista_rs"]
        else:
            valor = None
            margem = None
            situacao = (
                f"Nenhum plano até o limite da busca ({limite:g})"
                if not tolerancia
                else "Nenhum plano na faixa testada"
            )
        linhas.append(
            {
                "Regra": rotulo,
                "Menor valor com plano": valor,
                "Margem no menor valor (R$)": margem,
                "Situação": situacao,
            }
        )
    return pd.DataFrame(linhas)
