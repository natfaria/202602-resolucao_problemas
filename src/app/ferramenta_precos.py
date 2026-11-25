"""Interface Streamlit para planejar preços com entradas informadas pelo usuário.

Execução, a partir da raiz do repositório:

    .venv/bin/python -m streamlit run src/app/ferramenta_precos.py
"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.optimization.diagnostico import diagnosticar
from src.optimization.ferramenta import (
    REGRAS_RELAXAVEIS,
    planejar,
    problema_da_ferramenta,
    restricoes_da_solucao,
    rotulos_dias,
)
from src.optimization.planning_inputs import load_planning_inputs

st.set_page_config(
    page_title="Planejamento de preços: Produto_A",
    page_icon=str(ROOT / "src/app/assets/minerva_foods_icone.png"),
    layout="wide",
)

# Paleta da identidade Minerva Foods.
VERMELHO = "#E84752"
CHUMBO = "#2B3D4A"
PRETO = "#0F0F0F"
DOURADO = "#C1B77E"

ESTILO = """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 6rem; }
h1, h2, h3 { color: #2B3D4A; }
.rodape-originais {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
    background: #FFFFFF; border-top: 3px solid #C1B77E;
    padding: 0.5rem 1rem; font-size: 0.85rem; color: #2B3D4A;
    display: flex; flex-wrap: wrap; justify-content: center; gap: 0.4rem 1.6rem;
}
.rodape-originais span b { color: #E84752; }
</style>
"""


@st.cache_resource
def carregar_entradas():
    return load_planning_inputs(ROOT / "models/otimizacao/entradas_planejamento.json", root=ROOT)


def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_percentual(valor):
    return f"{valor:.0%}".replace(".", ",")


def formatar_faixa(faixa):
    return f"{formatar_real(faixa['min'])} a {formatar_real(faixa['max'])}"


def rotulo_restricao_principal(restricao):
    if restricao["ganho_ao_relaxar_rs"] is None or pd.isna(restricao["ganho_ao_relaxar_rs"]):
        return (
            f"Limite mais restritivo: **{restricao['limite']}** ({restricao['onde']}). "
            "Relaxá-lo sozinho não gera plano."
        )
    return (
        f"Limite mais restritivo: **{restricao['limite']}** ({restricao['onde']}). "
        f"Relaxá-lo sozinho aumenta a margem em {formatar_real(restricao['ganho_ao_relaxar_rs'])}."
    )


def rodape_originais(base):
    """Valores fixos das entradas originais; não mudam com os campos do formulário."""
    suporte = base.artifact["price_support"]
    faixa_seg_qui = suporte["Segunda_a_Quinta"]
    faixa_sexta = suporte["Sexta"]
    itens = [
        f"Preço anterior: <b>{formatar_real(base.initial_price)}/kg</b> (último dia de treino)",
        f"Limite entre dias: <b>{formatar_real(base.daily_variation)}/kg</b>",
        f"Meta semanal: <b>{next(iter(base.targets.values())):.0f} kg</b>",
        f"Tolerância: <b>−{formatar_percentual(base.tol_lower)} / +{formatar_percentual(base.tol_upper)}</b>",
        f"Limites da regressão seg–qui: <b>{formatar_faixa(faixa_seg_qui)}</b>",
        f"Limites da regressão sexta: <b>{formatar_faixa(faixa_sexta)}</b>",
    ]
    corpo = "".join(f"<span>{item}</span>" for item in itens)
    return f'<div class="rodape-originais">{corpo}</div>'


def desenhar_graficos(diario, semanal, valor_anterior):
    rotulos = rotulos_dias(diario["dia_semana"], diario["semana"])
    x = range(len(diario))
    fig, eixos = plt.subplots(2, 2, figsize=(9, 6.2))

    ax = eixos[0, 0]
    ax.plot(x, diario["preco_kg"], marker="o", color=VERMELHO)
    ax.axhline(valor_anterior, color=DOURADO, ls=":", label="Preço anterior")
    ax.set(title="Preço por dia", ylabel="R$/kg")
    ax.legend(fontsize=8)

    ax = eixos[0, 1]
    ax.bar(x, diario["volume_previsto_kg"], color=CHUMBO)
    ax.set(title="Volume previsto por dia", ylabel="kg")

    ax = eixos[1, 0]
    ax.bar(x, diario["margem_prevista_rs"], color=DOURADO)
    ax.set(title="Margem prevista por dia", ylabel="R$")

    ax = eixos[1, 1]
    posicoes = range(len(semanal))
    ax.bar(posicoes, semanal["volume_previsto_kg"], color=CHUMBO, width=0.5)
    for i, linha in enumerate(semanal.itertuples()):
        ax.hlines(
            [linha.limite_inferior_kg, linha.limite_superior_kg],
            i - 0.3,
            i + 0.3,
            color=VERMELHO,
            ls="--",
        )
    ax.set_xticks(list(posicoes), semanal["semana"].str.replace("_", " "))
    ax.set(title="Volume semanal e faixa permitida", ylabel="kg")

    for ax in eixos[0]:
        ax.set_xticks(list(x), rotulos, rotation=45)
    eixos[1, 0].set_xticks(list(x), rotulos, rotation=45)
    eixos[1, 1].grid(alpha=0.2)
    for ax in eixos.ravel():
        ax.spines[["top", "right"]].set_visible(False)
        ax.title.set_color(CHUMBO)
    fig.tight_layout()
    return fig


base, payload = carregar_entradas()
meta_padrao = float(next(iter(base.targets.values())))

st.markdown(ESTILO, unsafe_allow_html=True)
st.markdown(rodape_originais(base), unsafe_allow_html=True)

coluna_logo, coluna_titulo = st.columns([1, 5], vertical_alignment="center")
coluna_logo.image(str(ROOT / "src/app/assets/minerva_foods_logo.png"), width=200)
coluna_titulo.title("Planejamento de preços: Produto_A")
st.caption(
    "Escolhe um preço por dia para maximizar a margem prevista pela curva de demanda congelada. "
    "As margens são previsões condicionais ao modelo."
)


aba_planejamento, aba_livre, aba_sem_extrapolacao, aba_comparacao = st.tabs(
    [
        "Planejamento",
        "Ótimo livre (consulta)",
        "Melhor sem extrapolação (consulta)",
        "Otimizado e realizado (consulta)",
    ]
)

# Abas de consulta.

RESULTADOS = ROOT / "data/processed/minerva_otimizacao_resultado.json"
TRES_REFERENCIAS = ROOT / "reports/tables/03_tres_referencias_margem.csv"


def formatar_numero(valor, casas=2):
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


@st.cache_data
def cenario_salvo(chave):
    return json.loads(RESULTADOS.read_text(encoding="utf-8"))["scenarios"][chave]


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
    tabela = pd.DataFrame(
        {
            "Data": pd.to_datetime(diario["data"]).dt.strftime("%d/%m/%Y"),
            "Dia": diario["dia_semana"],
            "Preço (R$/kg)": diario["preco_kg"].round(2),
            "Volume previsto (kg)": diario["volume_previsto_kg"].round(2),
            "Margem prevista (R$)": diario["margem_prevista_rs"].round(2),
            "Fora da faixa observada": diario["extrapolado"],
        }
    )
    st.subheader("Plano diário")
    st.dataframe(tabela, hide_index=True, width="stretch")
    semanal = pd.DataFrame(cenario["weekly"])
    st.subheader("Resumo semanal")
    st.dataframe(
        pd.DataFrame(
            {
                "Semana": semanal["semana"].str.replace("_", " "),
                "Mínimo (kg)": semanal["limite_inferior_kg"].round(2),
                "Volume previsto (kg)": semanal["volume_previsto_kg"].round(2),
                "Máximo (kg)": semanal["limite_superior_kg"].round(2),
                "Margem prevista (R$)": semanal["margem_prevista_rs"].round(2),
            }
        ),
        hide_index=True,
        width="stretch",
    )
    fig, eixos = plt.subplots(1, 2, figsize=(11, 3.8))
    rotulos = [f"{pd.to_datetime(d):%d/%m}" for d in diario["data"]]
    eixos[0].plot(rotulos, diario["preco_kg"], "o-", color="#24547a")
    eixos[0].set(title="Preço por dia", ylabel="R$/kg")
    eixos[1].bar(rotulos, diario["volume_previsto_kg"], color="#a35b20")
    eixos[1].set(title="Volume previsto por dia", ylabel="kg")
    for eixo in eixos:
        eixo.tick_params(axis="x", rotation=45)
        eixo.grid(alpha=0.2)
    fig.tight_layout()
    st.pyplot(fig)


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

with aba_planejamento:
    with st.form("entradas"):
        colunas_entrada = st.columns(4)
        valor_anterior = colunas_entrada[0].number_input(
            "Preço anterior (R$/kg)",
            value=float(base.initial_price),
            min_value=1.0,
            step=1.0,
            format="%.2f",
        )
        variacao_primeira = colunas_entrada[1].number_input(
            "Limite da primeira mudança (R$/kg)",
            value=float(base.init_var),
            min_value=0.0,
            step=0.5,
        )
        variacao_diaria = colunas_entrada[2].number_input(
            "Limite entre dias consecutivos (R$/kg)",
            value=float(base.daily_variation),
            min_value=0.0,
            step=0.5,
        )
        meta = colunas_entrada[3].number_input(
            "Meta semanal (kg)", value=meta_padrao, min_value=1.0, step=5.0
        )
        colunas_entrada = st.columns(4)
        tolerancia_inferior = (
            colunas_entrada[0].number_input(
                "Tolerância abaixo da meta (%)",
                value=float(base.tol_lower * 100),
                min_value=0.0,
                max_value=99.0,
                step=1.0,
            )
            / 100
        )
        tolerancia_superior = (
            colunas_entrada[1].number_input(
                "Tolerância acima da meta (%)",
                value=float(base.tol_upper * 100),
                min_value=0.0,
                max_value=99.0,
                step=1.0,
            )
            / 100
        )
        custo_unico = colunas_entrada[2].number_input(
            "Custo por kg (R$/kg)",
            value=float(base.costs[0]),
            min_value=0.01,
            step=1.0,
            format="%.2f",
        )
        imposto = (
            colunas_entrada[3].number_input(
                "Imposto sobre a receita (%)",
                value=float(base.tax_rate * 100),
                min_value=0.0,
                max_value=99.0,
                step=1.0,
            )
            / 100
        )

        with st.expander("Custo por dia (usado somente se a opção estiver ligada)"):
            custo_variavel = st.toggle("Usar custo por dia no lugar do custo único", value=False)
            tabela_custos = st.data_editor(
                pd.DataFrame(
                    {
                        "Dia": rotulos_dias(base.weekdays, base.weeks),
                        "Custo (R$/kg)": [float(valor) for valor in base.costs],
                    }
                ),
                column_config={
                    "Custo (R$/kg)": st.column_config.NumberColumn(min_value=0.01, format="%.2f"),
                },
                disabled=["Dia"],
                hide_index=True,
                key="custos_por_dia",
            )
        custo = (
            tabela_custos["Custo (R$/kg)"].astype(float).tolist()
            if custo_variavel
            else custo_unico
        )

        st.markdown(
            "**Regras a relaxar** (marcadas são removidas do cálculo; nenhuma marcada = regras originais)"
        )
        colunas_regras = st.columns(len(REGRAS_RELAXAVEIS))
        relaxadas = frozenset(
            regra
            for coluna, (regra, rotulo) in zip(colunas_regras, REGRAS_RELAXAVEIS.items())
            if coluna.checkbox(rotulo, key=f"relax_{regra}")
        )
        enviado = st.form_submit_button("Calcular plano", type="primary")

    entradas = {
        "valores": {
            "valor_anterior": valor_anterior,
            "variacao_primeira": variacao_primeira,
            "variacao_diaria": variacao_diaria,
            "meta": meta,
            "tolerancia_inferior": tolerancia_inferior,
            "tolerancia_superior": tolerancia_superior,
            "custo": custo,
            "imposto": imposto,
        },
        "relaxadas": relaxadas,
    }

    if enviado or "resultado" not in st.session_state:
        problema = problema_da_ferramenta(base, **entradas["valores"])
        resultado_calculado = planejar(problema, entradas["relaxadas"])
        st.session_state["resultado"] = resultado_calculado
        st.session_state["restricoes"] = (
            restricoes_da_solucao(problema, resultado_calculado)
            if resultado_calculado["diario"] is not None
            else None
        )
        st.session_state["valor_anterior"] = valor_anterior
    resultado = st.session_state["resultado"]

    with st.expander(
        "Diagnóstico: o que precisa mudar para existir um plano",
        expanded=resultado["diario"] is None,
    ):
        st.write(
            "Usa as entradas atuais do formulário. Para cada regra, sozinha, mostra a menor "
            "flexibilização que permite um plano e a margem prevista nesse ponto."
        )
        if st.button("Calcular diagnóstico", key="botao_diagnostico"):
            problema_diagnostico = problema_da_ferramenta(base, **entradas["valores"])
            st.session_state["diagnostico"] = {
                "entradas": entradas,
                "status": planejar(problema_diagnostico)["status_texto"],
                "tabela": diagnosticar(problema_diagnostico),
            }
        if "diagnostico" in st.session_state:
            diagnostico_salvo = st.session_state["diagnostico"]
            st.caption(f"Com as regras originais: {diagnostico_salvo['status'].lower()}.")
            if diagnostico_salvo["entradas"] != entradas:
                st.warning(
                    "As entradas mudaram desde o último diagnóstico. Calcule de novo para atualizar."
                )
            st.dataframe(
                diagnostico_salvo["tabela"].round(4),
                hide_index=True,
                width="stretch",
                column_config={
                    "Menor valor com plano": st.column_config.NumberColumn(format="%.4f"),
                    "Margem no menor valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                },
            )

    if resultado["diario"] is None and not resultado["diagnostico"]:
        st.error(f"{resultado['status_texto']}. {resultado['motivo']}")
        st.stop()

    if resultado["diario"] is None:
        st.error(f"{resultado['status_texto']}. Maior volume alcançável por semana, abaixo.")
        diagnostico = (
            pd.DataFrame.from_dict(resultado["diagnostico"], orient="index")
            .rename_axis("semana")
            .reset_index()
        )
        st.dataframe(
            diagnostico[["semana", "lower_kg", "maximum_reachable_kg", "shortage_kg"]]
            .rename(
                columns={
                    "lower_kg": "Mínimo exigido (kg)",
                    "maximum_reachable_kg": "Maior volume possível (kg)",
                    "shortage_kg": "Falta para o mínimo (kg)",
                }
            )
            .round(2),
            hide_index=True,
        )
        st.stop()

    if resultado["status"] == "optimal":
        st.success(f"{resultado['status_texto']}. Regras: {resultado['cenario']}.")
    else:
        st.warning(f"{resultado['status_texto']}. Regras: {resultado['cenario']}.")

    diario = resultado["diario"].assign(venda_rs=lambda d: d["preco_kg"] * d["volume_previsto_kg"])
    semanal = resultado["semanal"]
    colunas = st.columns(4)
    colunas[0].metric("Margem prevista total", formatar_real(resultado["margem_total_rs"]))
    colunas[1].metric("Venda prevista no período", formatar_real(diario["venda_rs"].sum()))
    colunas[2].metric("Volume semana 1", f"{semanal.iloc[0]['volume_previsto_kg']:.2f} kg")
    colunas[3].metric("Volume semana 2", f"{semanal.iloc[1]['volume_previsto_kg']:.2f} kg")

    restricoes = st.session_state["restricoes"]
    ativas = restricoes[restricoes["situacao"] == "Ativa"]
    if ativas.empty:
        st.info("Nenhum limite está encostado na solução: o plano tem folga em todas as regras.")
    else:
        st.info(rotulo_restricao_principal(ativas.iloc[0]))
    st.subheader("Limites e folgas")
    st.dataframe(
        restricoes.rename(
            columns={
                "limite": "Limite",
                "situacao": "Situação",
                "onde": "Onde (ativo ou menor folga)",
                "ganho_ao_relaxar_rs": "Ganho de margem ao relaxar sozinho (R$)",
            }
        )[
            [
                "Limite",
                "Situação",
                "Onde (ativo ou menor folga)",
                "Ganho de margem ao relaxar sozinho (R$)",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "Ganho de margem ao relaxar sozinho (R$)": st.column_config.NumberColumn(
                format="R$ %.2f"
            ),
        },
    )

    tabela = pd.DataFrame(
        {
            "Dia": rotulos_dias(diario["dia_semana"], diario["semana"]),
            "Preço (R$/kg)": diario["preco_kg"].round(2),
            "Mudança (R$/kg)": diario["variacao_preco_rs"].round(2),
            "Volume previsto (kg)": diario["volume_previsto_kg"].round(2),
            "Venda do dia (R$)": diario["venda_rs"].round(2),
            "Imposto (R$)": diario["imposto_rs"].round(2),
            "Margem prevista (R$)": diario["margem_prevista_rs"].round(2),
            "Fora da faixa observada": diario["extrapolado"],
        }
    )
    st.subheader("Plano diário")
    st.caption("Venda do dia = preço × volume previsto, antes do imposto.")
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={
            "Preço (R$/kg)": st.column_config.NumberColumn(format="%.2f"),
            "Mudança (R$/kg)": st.column_config.NumberColumn(format="%.2f"),
            "Volume previsto (kg)": st.column_config.NumberColumn(format="%.2f"),
            "Venda do dia (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Imposto (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Margem prevista (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    st.download_button(
        "Baixar plano diário (CSV)",
        tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="plano_precos.csv",
        mime="text/csv",
    )

    st.subheader("Resumo semanal")
    resumo = pd.DataFrame(
        {
            "Semana": semanal["semana"].str.replace("_", " "),
            "Mínimo (kg)": semanal["limite_inferior_kg"].round(2),
            "Volume previsto (kg)": semanal["volume_previsto_kg"].round(2),
            "Máximo (kg)": semanal["limite_superior_kg"].round(2),
            "Margem prevista (R$)": semanal["margem_prevista_rs"].round(2),
            "Preço médio (R$/kg)": semanal["preco_medio_kg"].round(2),
        }
    )
    st.dataframe(resumo, hide_index=True, width="stretch")

    st.subheader("Gráficos")
    st.pyplot(desenhar_graficos(diario, semanal, st.session_state["valor_anterior"]), width=820)
