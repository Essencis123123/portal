import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta


# Configuração do painel
st.set_page_config(page_title="Painel de Serviços", layout="wide")

# Inicializa banco de dados em memória
if "servicos" not in st.session_state:
    st.session_state["servicos"] = pd.DataFrame(columns=[
        "Fornecedor", "Solicitante", "Inicio", "Fim", "Descricao", "Status", "Avaliacao", "Comentario"
    ])

st.title("📊 Painel de Fornecedores - Prestação de Serviços")

# Criação das abas
abas = st.tabs(["➕ Cadastrar Serviço", "📌 Acompanhamento", "⭐ Avaliações", "📈 Dashboard"])

# --- CADASTRAR ---
with abas[0]:
    st.subheader("Cadastrar Novo Serviço")
    col1, col2 = st.columns(2)
    with col1:
        fornecedor = st.text_input("Fornecedor")
        inicio = st.date_input("Data de Início", datetime.today(), format="DD/MM/YYYY")
    with col2:
        solicitante = st.text_input("Solicitante")
        fim = st.date_input("Data de Fim Prevista", datetime.today() + timedelta(days=7), format="DD/MM/YYYY")
    descricao = st.text_area("Descrição do Serviço")

    if st.button("Salvar Serviço"):
        novo = {
            "Fornecedor": fornecedor,
            "Solicitante": solicitante,
            "Inicio": pd.to_datetime(inicio),
            "Fim": pd.to_datetime(fim),
            "Descricao": descricao,
            "Status": "Em andamento",
            "Avaliacao": None,
            "Comentario": None
        }
        st.session_state["servicos"] = pd.concat(
            [st.session_state["servicos"], pd.DataFrame([novo])],
            ignore_index=True
        )
        st.success("✅ Serviço cadastrado com sucesso!")

# --- ACOMPANHAMENTO ---
with abas[1]:
    st.subheader("Serviços em Andamento e Concluídos")

    servicos_display = st.session_state["servicos"].copy()
    if not servicos_display.empty:
        servicos_display["Inicio"] = pd.to_datetime(servicos_display["Inicio"]).dt.strftime("%d/%m/%Y")
        servicos_display["Fim"] = pd.to_datetime(servicos_display["Fim"]).dt.strftime("%d/%m/%Y")

    st.dataframe(servicos_display)

# --- AVALIAÇÕES ---
with abas[2]:
    st.subheader("Avaliar Serviço")
    servicos = st.session_state["servicos"]
    lista = servicos[servicos["Status"] == "Em andamento"].index.tolist()
    if lista:
        escolha = st.selectbox(
            "Selecione o serviço",
            lista,
            format_func=lambda i: f"{servicos.at[i, 'Fornecedor']} - {servicos.at[i, 'Descricao']}"
        )
        nota = st.slider("Nota (1-5)", 1, 5)
        comentario = st.text_area("Comentário")
        if st.button("Concluir e Avaliar"):
            st.session_state["servicos"].at[escolha, "Avaliacao"] = nota
            st.session_state["servicos"].at[escolha, "Comentario"] = comentario
            st.session_state["servicos"].at[escolha, "Status"] = "Concluído"
            st.success("⭐ Avaliação registrada!")
    else:
        st.info("Nenhum serviço em andamento para avaliar.")

# --- DASHBOARD ---
with abas[3]:
    st.subheader("📊 Indicadores de Desempenho")
    servicos = st.session_state["servicos"]

    if not servicos.empty:
        col1, col2, col3 = st.columns(3)
        ativos = len(servicos[servicos["Status"] == "Em andamento"])
        concluidos = len(servicos[servicos["Status"] == "Concluído"])
        media_avaliacao = servicos["Avaliacao"].dropna().mean()

        col1.metric("Serviços Ativos", ativos)
        col2.metric("Serviços Concluídos", concluidos)
        col3.metric("Média de Avaliação", f"{media_avaliacao:.1f}" if not pd.isna(media_avaliacao) else "-")

        # Gráfico de barras - média de avaliação por fornecedor
        st.write("### Média de Avaliações por Fornecedor")
        media = servicos.groupby("Fornecedor")["Avaliacao"].mean().dropna()
        if not media.empty:
            fig = px.bar(
                media,
                x=media.index,
                y=media.values,
                text=media.values,
                color=media.values,
                color_continuous_scale="Blues"
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        # Timeline dos serviços
        st.write("### Linha do Tempo dos Serviços")
        df_timeline = servicos.copy()
        df_timeline["Inicio"] = pd.to_datetime(df_timeline["Inicio"])
        df_timeline["Fim"] = pd.to_datetime(df_timeline["Fim"])
        fig2 = px.timeline(
            df_timeline,
            x_start="Inicio",
            x_end="Fim",
            y="Fornecedor",
            color="Status",
            hover_data=["Descricao", "Solicitante"]
        )
        fig2.update_yaxes(autorange="reversed")
        fig2.update_xaxes(tickformat="%d/%m/%Y")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum dado disponível ainda.")
