"""Ferramenta de planejamento: reproduz os resultados congelados do notebook 3.0."""

from pathlib import Path

import pytest

pytest.importorskip("gurobipy")

from src.optimization.ferramenta import (
    cenario_da_ferramenta,
    planejar,
    problema_da_ferramenta,
    restricoes_da_solucao,
    rotulos_dias,
)
from src.optimization.planning_inputs import load_planning_inputs

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def base():
    problem, _ = load_planning_inputs(
        ROOT / "models/otimizacao/entradas_planejamento.json", root=ROOT
    )
    return problem


def problema(base, **alteracoes):
    valores = {
        "valor_anterior": base.initial_price,
        "variacao_primeira": 2.0,
        "variacao_diaria": 2.0,
        "meta": 165.0,
        "tolerancia_inferior": 0.30,
        "tolerancia_superior": 0.30,
        "custo": float(base.costs[0]),
        "imposto": 0.07,
    }
    valores.update(alteracoes)
    return problema_da_ferramenta(base, **valores)


def test_regras_originais_nao_tem_plano_e_mostram_o_maximo_alcancavel(base):
    resultado = planejar(problema(base))
    assert resultado["status"] == "infeasible"
    semanas = resultado["diagnostico"]
    assert semanas["semana_1"]["maximum_reachable_kg"] == pytest.approx(76.99, abs=0.01)
    assert semanas["semana_2"]["maximum_reachable_kg"] == pytest.approx(84.62, abs=0.01)


def test_relaxar_primeira_mudanca_reproduz_o_cenario_do_notebook(base):
    resultado = planejar(problema(base), frozenset({"primeira_mudanca"}))
    assert resultado["status"] == "optimal"
    assert resultado["margem_total_rs"] == pytest.approx(48917.58, abs=0.05)
    assert resultado["diario"]["preco_kg"].round(2).nunique() == 1
    assert resultado["semanal"]["volume_previsto_kg"].tolist() == pytest.approx([214.5, 214.5])


def test_saida_diaria_tem_um_dia_por_linha_e_margem_consistente(base):
    diario = planejar(problema(base), frozenset({"primeira_mudanca"}))["diario"]
    assert len(diario) == 10
    recalculada = ((1 - 0.07) * diario["preco_kg"] - diario["custo_kg"]) * diario[
        "volume_previsto_kg"
    ]
    assert recalculada.to_numpy() == pytest.approx(
        diario["margem_prevista_rs"].to_numpy(), abs=0.02
    )


def test_relaxar_limites_semanais_removidos_do_cenario(base):
    cenario = cenario_da_ferramenta(frozenset({"minimo_semanal", "maximo_semanal"}))
    assert not cenario.weekly_minimum_active and not cenario.weekly_maximum_active
    assert cenario.enforce_initial_anchor and cenario.enforce_daily_variation


def test_regra_desconhecida_e_recusada(base):
    with pytest.raises(ValueError, match="desconhecidas"):
        cenario_da_ferramenta(frozenset({"inventada"}))


def test_custo_por_dia_entra_na_margem(base):
    custos = [1000.0, 1010.0, 1020.0, 1030.0, 1000.0, 1000.0, 1010.0, 1020.0, 1030.0, 1000.0]
    resultado = planejar(problema(base, custo=custos), frozenset({"primeira_mudanca"}))
    assert resultado["status"] == "optimal"
    diario = resultado["diario"]
    recalculada = ((1 - 0.07) * diario["preco_kg"] - diario["custo_kg"]) * diario[
        "volume_previsto_kg"
    ]
    assert recalculada.to_numpy() == pytest.approx(
        diario["margem_prevista_rs"].to_numpy(), abs=0.02
    )
    assert diario["custo_kg"].tolist() == pytest.approx(custos)


def test_restricao_mais_forte_no_caso_com_plano(base):
    resultado = planejar(problema(base, valor_anterior=1208.0))
    assert resultado["status"] == "optimal"
    restricoes = restricoes_da_solucao(problema(base, valor_anterior=1208.0), resultado)
    ativas = restricoes[restricoes["situacao"] == "Ativa"].set_index("regra")
    assert "maximo_semanal" in ativas.index
    assert ativas.loc["maximo_semanal", "ganho_ao_relaxar_rs"] > 0
    assert (
        ativas["ganho_ao_relaxar_rs"].max() == ativas.loc["maximo_semanal", "ganho_ao_relaxar_rs"]
    )


def test_rotulos_dias_usam_dia_da_semana_e_semana_sem_datas():
    rotulos = rotulos_dias(["Segunda", "Terça", "Sexta"], ["semana_1", "semana_1", "semana_2"])
    assert rotulos == ["Segunda-feira 1", "Terça-feira 1", "Sexta-feira 2"]
