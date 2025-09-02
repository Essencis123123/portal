import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os  # <- adicionado

st.set_page_config(page_title="Painel Almoxarifado", layout="wide")

# Criar CSV automaticamente se não existir
if not os.path.exists("dados_almoxarifado.csv"):
    df_inicial = pd.DataFrame(columns=[
        "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
        "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
        "OBSERVAÇÃO", "DOC NF"
    ])
    df_inicial.to_csv("dados_almoxarifado.csv", index=False)
    print("CSV inicial criado.")

# Função para carregar ou criar o banco de dados
def carregar_dados():
    try:
        df = pd.read_csv("dados_almoxarifado.csv", parse_dates=["DATA"], dayfirst=True)
    except FileNotFoundError:
        df = pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
            "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
            "OBSERVAÇÃO", "DOC NF"
        ])
    return df

# Função para salvar os dados
def salvar_dados(df):
    df.to_csv("dados_almoxarifado.csv", index=False)

df = carregar_dados()

# === resto do seu código continua exatamente igual ===
st.title("Registro de Notas Fiscais")

# Formulário horizontal
with st.form("formulario_nota"):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        data = st.date_input("Data", datetime.date.today())
    with col2:
        recebedor = st.selectbox("Recebedor", [
            "ARLEY GONCALVES DOS SANTOS",
            "EVIANE DAS GRACAS DE ASSIS",
            "ANDRE CASTRO DE SOUZA",
            "ISABELA CAROLINA DE PAULA SOARES",
            "EMERSON ALMEIDA DE ARAUJO",
            "GABRIEL PEREIRA MARTINS",
            "OUTROS"
        ])
    with col3:
        fornecedor = st.text_input("Fornecedor")
    with col4:
        nf = st.text_input("NF")
    with col5:
        pedido = st.text_input("Pedido")
    with col6:
        volume = st.number_input("Volume", min_value=0)

    col7, col8, col9, col10 = st.columns(4)
    with col7:
        valor_total_nf = st.text_input("V. TOTAL NF", "R$ 0,00")
    with col8:
        condicao_frete = st.selectbox("Condição de Frete", ["CIF", "FOB"])
    with col9:
        valor_frete = st.text_input("Valor Frete", "R$ 0,00")
    with col10:
        observacao = st.text_input("Observação")
    
    doc_nf = st.text_input("Link DOC NF")

    enviar = st.form_submit_button("Registrar Nota")
    if enviar:
        novo_registro = {
            "DATA": data.strftime('%d/%m/%Y'),  # <- Formato Brasil garantido
            "RECEBEDOR": recebedor,
            "FORNECEDOR": fornecedor,
            "NF": nf,
            "PEDIDO": pedido,
            "VOLUME": volume,
            "V. TOTAL NF": valor_total_nf,
            "CONDICAO FRETE": condicao_frete,
            "VALOR FRETE": valor_frete,
            "OBSERVAÇÃO": observacao,
            "DOC NF": doc_nf
        }
        df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
        salvar_dados(df)
        st.success("Nota registrada com sucesso!")



# Lateral: notas do mês
st.sidebar.header("Notas enviadas este mês")

# Converter datas corretamente no formato DD/MM/AAAA
df["DATA_DT"] = pd.to_datetime(df["DATA"], format='%d/%m/%Y', errors='coerce')


mes_atual = datetime.date.today().month
ano_atual = datetime.date.today().year
df_mes = df[(df["DATA_DT"].dt.month == mes_atual) & (df["DATA_DT"].dt.year == ano_atual)]

if not df_mes.empty:
    df_mes_exibir = df_mes[["NF", "V. TOTAL NF"]]
    st.sidebar.dataframe(df_mes_exibir)
else:
    st.sidebar.write("Nenhuma nota registrada neste mês.")

# Dashboard horizontal
st.subheader("Dashboard Resumido")
if not df_mes.empty:
    df_dash = df_mes.copy()
    # Converter valores
    df_dash["V. TOTAL NF"] = df_dash["V. TOTAL NF"].astype(str).str.replace('[R$ ]','', regex=True).str.replace(',','').astype(float)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        fig1 = px.bar(df_dash.groupby("FORNECEDOR")["NF"].count().reset_index(), 
                      x="NF", y="FORNECEDOR", orientation='h', text="NF", 
                      title="Quantidade de Notas por Fornecedor")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.bar(df_dash.groupby("FORNECEDOR")["V. TOTAL NF"].sum().reset_index(), 
                      x="V. TOTAL NF", y="FORNECEDOR", orientation='h', text="V. TOTAL NF", 
                      title="Valor Total por Fornecedor")
        st.plotly_chart(fig2, use_container_width=True)
    with col3:
        mes_anterior = (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).month
        df_anterior = df[df["DATA_DT"].dt.month == mes_anterior]
        df_merge = pd.merge(
            df_dash.groupby("FORNECEDOR")["V. TOTAL NF"].sum().reset_index(),
            df_anterior.groupby("FORNECEDOR")["V. TOTAL NF"].sum().reset_index(),
            on="FORNECEDOR", how="left", suffixes=('_atual','_anterior')).fillna(0)
        df_merge["Diferença"] = df_merge["V. TOTAL NF_atual"] - df_merge["V. TOTAL NF_anterior"]
        fig3 = px.bar(df_merge, x="Diferença", y="FORNECEDOR", orientation='h', text="Diferença", title="Comparativo com Mês Anterior")
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.write("Nenhuma nota registrada neste mês para gerar dashboard.")

# Histórico detalhado
# Histórico detalhado
# Histórico detalhado
# Histórico detalhado
st.subheader("Histórico de Notas")

# Lista de meses disponíveis no histórico
meses = sorted(df["DATA_DT"].dt.month.dropna().unique())

# Apenas filtro de mês
mes_selecionado = st.selectbox("Selecione o mês", meses)

# Filtra apenas pelo mês
df_historico = df[df["DATA_DT"].dt.month == mes_selecionado].copy()

# Criar coluna formatada no formato DD/MM/AAAA
df_historico["DATA_FORMATADA"] = df_historico["DATA_DT"].dt.strftime('%d/%m/%Y')

# Selecionar colunas já com DATA formatada
df_historico_exibir = df_historico[[
    "DATA_FORMATADA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
    "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
    "OBSERVAÇÃO", "DOC NF"
]].copy()

# Transformar DOC NF em link clicável
df_historico_exibir["DOC NF"] = df_historico_exibir["DOC NF"].apply(
    lambda x: f'<a href="{x}" target="_blank">📄Abrir PDF</a>' if pd.notna(x) and str(x).strip() != "" else ""
)

# Exibir tabela com links clicáveis
st.write(df_historico_exibir.to_html(escape=False, index=False), unsafe_allow_html=True)



