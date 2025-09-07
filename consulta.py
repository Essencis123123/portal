import streamlit as st
import pandas as pd
import datetime
import requests
from PIL import Image
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px
from pandas.errors import EmptyDataError
import numpy as np

# Configuração da página
st.set_page_config(page_title="Painel de Consulta", layout="wide", page_icon="🔎")

# --- CSS Personalizado para o Tema Essencis ---
st.markdown(
    """
    <style>
    /* ... (seu código CSS existente, que está ótimo) ... */
    </style>
    """,
    unsafe_allow_html=True
)

# Carregar a imagem do logo a partir da URL (com cache)
@st.cache_data(show_spinner=False)
def load_logo(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception:
        st.error("Não foi possível carregar o logo.")
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- Funções de Conexão e Tratamento de Dados ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro de autenticação com o Google Sheets: {e}")
        return None

def limpar_e_processar_df(df):
    """Função auxiliar para tratar e limpar os dados do DataFrame."""
    if df.empty:
        return df

    # Trata colunas de data
    date_cols = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']
    for col in date_cols:
        if col in df.columns and not df[col].empty:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    
    # Converte colunas numéricas
    numeric_cols = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']
    for col in numeric_cols:
        if col in df.columns and not df[col].empty:
            df[col] = df[col].astype(str).str.replace('.', '').str.replace(',', '.').apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # Garante que colunas importantes existam
    required_cols = ['STATUS_PEDIDO', 'ORDEM_COMPRA', 'FORNECEDOR', 'PREVISAO_ENTREGA', 'CODIGO_MATERIAL', 'DATA_ENTREGA', 'QUANTIDADE', 'VALOR_ITEM', 'DATA']
    for col in required_cols:
        if col not in df.columns:
            df[col] = '' if 'DATA' not in col else pd.NaT

    # Define o status do pedido
    df['STATUS_PEDIDO'] = df['DATA_ENTREGA'].apply(lambda x: 'ENTREGUE' if pd.notna(x) else 'PENDENTE')

    # Calcula o valor total
    df['VALOR_TOTAL'] = df['QUANTIDADE'] * df['VALOR_ITEM']
    
    return df

@st.cache_data(ttl=600, show_spinner="Carregando dados do Google Sheets...")
def carregar_dados_pedidos():
    """Carrega os dados de pedidos do Google Sheets."""
    gc = get_gspread_client()
    if not gc:
        return pd.DataFrame()
    
    try:
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return limpar_e_processar_df(df)

    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha não encontrada. Verifique o ID no `secrets.toml`.")
        return pd.DataFrame()
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de API ao acessar a planilha: {e.args[0]}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro inesperado ao carregar dados: {e}")
        return pd.DataFrame()

# Carrega os dados uma vez para o app
df_pedidos = carregar_dados_pedidos()

# --- LAYOUT DO SIDEBAR ---
with st.sidebar:
    if logo_img:
        st.image(logo_img, use_container_width=True)
    
    st.title("🔎 Painel de Consulta")
    st.divider()
    
    if st.button("🔄 Recarregar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Filtros de Período")

    filtro_mes_dash = []
    filtro_ano_dash = []
    if 'DATA' in df_pedidos.columns and not df_pedidos['DATA'].isnull().all():
        df_pedidos['MES'] = df_pedidos['DATA'].dt.month
        df_pedidos['ANO'] = df_pedidos['DATA'].dt.year
        meses_disponiveis = sorted(df_pedidos['MES'].dropna().unique())
        anos_disponiveis = sorted(df_pedidos['ANO'].dropna().unique(), reverse=True)
        meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                       7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        
        filtro_mes_dash = st.multiselect(
            "Selecione o(s) Mês(es):", 
            options=meses_disponiveis, 
            default=meses_disponiveis,
            format_func=lambda x: meses_nomes.get(x, x)
        )
        
        filtro_ano_dash = st.multiselect(
            "Selecione o(s) Ano(s):", 
            options=anos_disponiveis,
            default=anos_disponiveis
        )
    else:
        st.info("Nenhum dado com data disponível para filtrar.")

# Exibe o cabeçalho temático principal
st.markdown("""
    <div class='header-container'>
        <h1>🔎 PAINEL DE CONSULTA DE REQUISIÇÕES</h1>
        <p>Visualize e analise o histórico completo de pedidos de compra</p>
    </div>
""", unsafe_allow_html=True)

# Verifica se o DataFrame não está vazio
if df_pedidos.empty:
    st.info("Nenhum pedido registrado no sistema ou erro ao carregar dados.")
    st.stop()

# --- FILTROS MOVIDOS PARA A PÁGINA PRINCIPAL ---
st.markdown("---")
st.subheader("Filtros de Dados")

col_filters1, col_filters2, col_filters3, col_filters4 = st.columns(4)

with col_filters1:
    solicitantes_disponiveis = sorted(df_pedidos['SOLICITANTE'].dropna().unique().tolist())
    filtro_solicitante = st.selectbox("Solicitante:", options=['Todos'] + solicitantes_disponiveis)

with col_filters2:
    departamentos_disponiveis = sorted(df_pedidos['DEPARTAMENTO'].dropna().unique().tolist())
    filtro_departamento = st.selectbox("Departamento:", options=['Todos'] + departamentos_disponiveis)

with col_filters3:
    status_disponiveis = df_pedidos['STATUS_PEDIDO'].dropna().unique().tolist()
    filtro_status = st.selectbox("Status:", options=['Todos'] + sorted(status_disponiveis))

with col_filters4:
    cod_materiais_disponiveis = sorted(df_pedidos['CODIGO_MATERIAL'].dropna().unique().tolist())
    filtro_material_cod = st.selectbox("Cód. Material:", options=['Todos'] + cod_materiais_disponiveis)

# --- Aplicação dos Filtros na Tabela Principal ---
df_filtrado = df_pedidos.copy()

if filtro_mes_dash:
    df_filtrado = df_filtrado[df_filtrado['DATA'].dt.month.isin(filtro_mes_dash)]
if filtro_ano_dash:
    df_filtrado = df_filtrado[df_filtrado['DATA'].dt.year.isin(filtro_ano_dash)]
if filtro_solicitante != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['SOLICITANTE'] == filtro_solicitante]
if filtro_departamento != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['DEPARTAMENTO'] == filtro_departamento]
if filtro_status != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['STATUS_PEDIDO'] == filtro_status]
if filtro_material_cod != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['CODIGO_MATERIAL'] == filtro_material_cod]

if df_filtrado.empty:
    st.warning("Nenhum pedido encontrado com os filtros aplicados.")
    st.stop()

# --- Análise e Métricas ---
st.subheader("Visão Geral do Período")
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_pedidos = len(df_filtrado)
    st.metric("Total de Pedidos", total_pedidos)
with col2:
    pedidos_pendentes = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'PENDENTE'])
    st.metric("Pedidos Pendentes", pedidos_pendentes)
with col3:
    pedidos_entregues = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'ENTREGUE'])
    st.metric("Pedidos Entregues", pedidos_entregues)
with col4:
    valor_total_soma = df_filtrado['VALOR_TOTAL'].sum()
    st.metric("Valor Total dos Pedidos", f"R$ {valor_total_soma:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# --- Gráfico de Análise Visual ---
st.subheader("Distribuição do Status dos Pedidos")
status_counts = df_filtrado['STATUS_PEDIDO'].value_counts().reset_index()
status_counts.columns = ['Status', 'Quantidade']
fig_status = px.pie(
    status_counts,
    values='Quantidade',
    names='Status',
    title='Distribuição do Status dos Pedidos',
    color_discrete_map={'PENDENTE': '#ffcc00', 'ENTREGUE': '#009933', 'EM ANDAMENTO': '#3366ff'}
)
st.plotly_chart(fig_status, use_container_width=True)

st.markdown("---")

# --- Tabela de Visualização Detalhada ---
st.subheader("Detalhes dos Pedidos")
st.info("A tabela abaixo é apenas para visualização e não permite edição.")

# Prepara o DataFrame para exibição
df_tabela = df_filtrado.copy()

def formatar_status(status):
    if status == 'ENTREGUE':
        return '🟢 ENTREGUE'
    elif status == 'PENDENTE':
        return '⚪ PENDENTE'
    return '🟡 EM ANDAMENTO'

df_tabela['STATUS'] = df_tabela['STATUS_PEDIDO'].apply(formatar_status)
df_tabela['DATA REQUISIÇÃO'] = df_tabela['DATA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
df_tabela['DATA ENTREGA'] = df_tabela['DATA_ENTREGA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
df_tabela['PREVISÃO ENTREGA'] = df_tabela['PREVISAO_ENTREGA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
df_tabela['VALOR TOTAL'] = df_tabela['VALOR_TOTAL'].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.dataframe(
    df_tabela[[
        'DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'CODIGO_MATERIAL', 'MATERIAL',
        'QUANTIDADE', 'VALOR TOTAL', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'PREVISÃO ENTREGA', 'DATA ENTREGA'
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "DATA REQUISIÇÃO": "Data Requisição",
        "REQUISICAO": "N° Requisição",
        "SOLICITANTE": "Solicitante",
        "DEPARTAMENTO": "Departamento",
        "CODIGO_MATERIAL": "Cód. Material",
        "MATERIAL": "Material",
        "QUANTIDADE": "Quantidade",
        "VALOR TOTAL": "Valor Total",
        "STATUS": "Status",
        "ORDEM_COMPRA": "N° Ordem de Compra",
        "FORNECEDOR": "Fornecedor",
        "PREVISÃO ENTREGA": "Previsão Entrega",
        "DATA ENTREGA": "Data Entrega"
    }
)

# --- Adiciona a autosoma do valor total abaixo da tabela ---
if not df_filtrado.empty:
    valor_total_soma = df_filtrado['VALOR_TOTAL'].sum()
    st.markdown(f"<div style='text-align: right; font-size: 20px; font-weight: bold; padding-top: 15px;'>Valor Total dos Itens Filtrados: R$ {valor_total_soma:,.2f}</div>".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)

# Botão de download para o CSV
csv_pedidos = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Exportar Tabela para CSV",
    data=csv_pedidos,
    file_name=f"pedidos_consulta_{datetime.date.today()}.csv",
    mime="text/csv",
    help="Clique para baixar os dados da tabela filtrada."
)
