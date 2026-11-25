"""Análise de preços e margem do Produto_A: cenários de consulta e simulação ao vivo.

Execução, a partir da raiz do repositório:

    .venv/bin/python -m streamlit run src/app/analise_precos.py
"""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.optimization.simulacao_restricoes import carregar_problema, simular_preco_anterior, simular_uma_restricao

st.set_page_config(page_title="Análise de preços: Produto_A", layout="wide")

RESULTADOS = ROOT / "data/processed/minerva_otimizacao_resultado.json"
TRES_REFERENCIAS = ROOT / "reports/tables/03_tres_referencias_margem.csv"


def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_numero(valor, casas=2):
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


@st.cache_data
def cenario_salvo(chave):
    return json.loads(RESULTADOS.read_text(encoding="utf-8"))["scenarios"][chave]


@st.cache_data(show_spinner="Resolvendo as flexibilizações com o solver...")
def simulacao_uma_restricao():
    return simular_uma_restricao(carregar_problema(ROOT))


@st.cache_data(show_spinner="Resolvendo preços anteriores com o solver...")
def simulacao_preco_anterior():
    return simular_preco_anterior(carregar_problema(ROOT))


def mostrar_cenario_fixo(chave, titulo, descricao, aviso=None):
    cenario = cenario_salvo(chave)
    st.subheader(titulo)
    st.write(descricao)
    if aviso:
        st.warning(aviso)
    st.caption(f"Consulta somente leitura: resultado salvo pelo notebook 3.0 (cenário `{chave}`).")

    colunas = st.columns(3)
    colunas[0].metric("Margem prevista (duas semanas)", formatar_real(cenario["total_margin_rs"]))
    volume_total = sum(dia["volume_previsto_kg"] for dia in cenario["daily"])
    colunas[1].metric("Volume previsto (kg)", formatar_numero(volume_total, 1))
    colunas[2].metric("Status do solver", cenario["status"])

    diario = pd.DataFrame(cenario["daily"])
    tabela = pd.DataFrame({
        "Data": pd.to_datetime(diario["data"]).dt.strftime("%d/%m/%Y"),
        "Dia": diario["dia_semana"],
        "Preço (R$/kg)": diario["preco_kg"].round(2),
        "Volume previsto (kg)": diario["volume_previsto_kg"].round(2),
        "Margem prevista (R$)": diario["margem_prevista_rs"].round(2),
        "Fora da faixa observada": diario["extrapolado"],
    })
    st.subheader("Plano diário")
    st.dataframe(tabela, hide_index=True, width="stretch")

    semanal = pd.DataFrame(cenario["weekly"])
    st.subheader("Resumo semanal")
    st.dataframe(
        pd.DataFrame({
            "Semana": semanal["semana"].str.replace("_", " "),
            "Mínimo (kg)": semanal["limite_inferior_kg"].round(2),
            "Volume previsto (kg)": semanal["volume_previsto_kg"].round(2),
            "Máximo (kg)": semanal["limite_superior_kg"].round(2),
            "Margem prevista (R$)": semanal["margem_prevista_rs"].round(2),
        }),
        hide_index=True, width="stretch",
    )

    fig, eixos = plt.subplots(1, 2, figsize=(11, 3.8))
    rotulos = [f"{pd.to_datetime(d):%d/%m}" for d in diario["data"]]
    eixos[0].plot(rotulos, diario["preco_kg"], "o-", color="#24547a")
    eixos[0].set(title="Preço por dia", ylabel="R$/kg")
    eixos[1].bar(rotulos, diario["volume_previsto_kg"], color="#a35b20")
    eixos[1].set(title="Volume previsto por dia", ylabel="kg")
    for eixo in eixos:
        eixo.tick_params(axis="x", rotation=45)
        eixo.grid(alpha=.2)
    fig.tight_layout()
    st.pyplot(fig)


st.title("Análise de preços e margem: Produto_A")
st.caption(
    "Premissas: custo de R$ 1.010,45/kg, imposto de 7% sobre a receita e curva de demanda observacional. "
    "As margens são previstas pela curva; o teste não observa os preços sugeridos."
)

aba_livre, aba_sem_extrapolacao, aba_comparacao, aba_simulacao = st.tabs([
    "Ótimo livre (consulta)",
    "Melhor sem extrapolação (consulta)",
    "Otimizado e realizado (consulta)",
    "Simulação (ao vivo)",
])

with aba_livre:
    mostrar_cenario_fixo(
        "var1_meta1_init1_ext1",
        "Ótimo livre",
        "Todas as restrições retiradas, com extrapolação. É uma referência teórica, não um plano para aplicar.",
        aviso="Os preços estão abaixo da faixa observada no treino (R$ 1.201 a R$ 1.365/kg).",
    )

with aba_sem_extrapolacao:
    mostrar_cenario_fixo(
        "var1_meta1_init1_ext0",
        "Melhor margem sem extrapolação",
        "Retira o limite entre dias, o mínimo e máximo semanais e o limite da primeira mudança. "
        "Os preços ficam dentro da faixa observada no treino.",
    )

with aba_comparacao:
    st.subheader("Otimizado, curva no preço praticado e realizado")
    st.write(
        "Margens com o custo do planejamento. O ganho do otimizado é a margem do otimizado dividida pela "
        "referência, menos um. Como a margem do otimizado é prevista pela curva, o percentual também é previsto."
    )
    st.caption("Consulta somente leitura: tabela gerada pelo notebook 3.0 (seção 8.2).")
    referencias = pd.read_csv(TRES_REFERENCIAS)
    st.dataframe(referencias.round(2), hide_index=True, width="stretch")

with aba_simulacao:
    st.subheader("Simulação de sensibilidade")
    st.write(
        "Cada linha resolve o problema com uma única restrição flexibilizada e as demais mantidas. "
        "Os resultados são calculados agora com o solver do projeto."
    )
    simulacao, limiares = simulacao_uma_restricao()

    st.markdown("**Menor flexibilização com plano**")
    st.dataframe(
        limiares.assign(**{
            "Menor valor com plano": limiares["Menor valor com plano"].round(3),
            "Margem no menor valor (R$)": limiares["Margem no menor valor (R$)"].round(2),
        }).drop(columns="Status"),
        hide_index=True, width="stretch",
    )

    fig, eixos = plt.subplots(2, 2, figsize=(12, 7))
    for eixo, (regra, grupo) in zip(eixos.ravel(), simulacao.groupby("regra", sort=False)):
        validos = grupo[grupo["Status"] == "Com plano"]
        eixo.plot(validos["valor"], validos["Margem prevista (R$)"], "o-", ms=3, color="#24547a")
        if not validos.empty:
            eixo.axvline(validos["valor"].min(), color=".4", ls="--", lw=.9)
        eixo.set(title=grupo["Restrição"].iloc[0], xlabel="Valor da flexibilização", ylabel="Margem prevista (R$)")
        eixo.grid(alpha=.2)
    fig.tight_layout()
    st.pyplot(fig)

    with st.expander("Ver todos os pontos simulados"):
        st.dataframe(simulacao.drop(columns="regra").round(4), hide_index=True, width="stretch")

    st.markdown("**Preço anterior**")
    if st.button("Simular preço anterior (cerca de 60 resoluções)"):
        st.session_state["preco_anterior"] = simulacao_preco_anterior()
    if "preco_anterior" in st.session_state:
        st.dataframe(st.session_state["preco_anterior"].round(2), hide_index=True, width="stretch")
