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

# Configuração da página com layout wide e ícone
st.set_page_page(page_title="Painel de Consulta", layout="wide", page_icon="🔎")

# --- CSS Personalizado para o Tema Essencis ---
st.markdown(
    """
    <style>
    /* Cor do menu lateral e texto */
    [data-testid="stSidebar"] {
        background-color: #1C4D86;
        color: white;
    }
    
    /* Regras para garantir que TODO o texto no sidebar seja branco */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    .stDownloadButton button p {
        color: white !important;
    }

    /* Estilo para o radio button, garantindo que o texto dele também seja branco */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span {
        color: white !important;
    }
    
    /* Estilo para deixar a letra dos botões preta */
    .stButton button p {
        color: black !important;
    }
    .stDownloadButton button {
        background-color: #0055a5;
    }
    .stDownloadButton button p {
        color: white !important;
    }
    /* Estilo para a cor do texto do multiselect */
    .stMultiSelect, .stSelectbox {
        color: black !important;
    }
    .stMultiSelect div[data-baseweb="select"] {
        background-color: #f0f2f5 !important;
    }
    
    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 80%;
        border-radius: 10px;
        padding: 10px 0;
    }

    /* Estilo para o container principal da página */
    .main-container {
        background-color: white;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        color: #333;
    }
    
    /* Estilo para o cabeçalho principal da página */
    .header-container {
        background: linear-gradient(135deg, #0055a5 0%, #1C4D86 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        text-align: center;
        color: white;
    }
    
    .header-container h1 {
        color: white;
        margin: 0;
    }

    .header-container p {
        color: white;
        margin: 5px 0 0 0;
        font-size: 18px;
    }
    
    /* Estilo para os sub-cabeçalhos dentro da área principal */
    h2, h3 {
        color: #1C4D86;
        font-weight: 600;
    }
    
    /* Estilo para os botões de ação */
    .stButton button {
        background-color: #0055a5;
        color: white;
        border-radius: 8px;
        transition: background-color 0.3s;
    }
    .stButton button:hover {
        background-color: #007ea7;
    }
    
    /* Estilo para os cards de métricas */
    [data-testid="stMetric"] > div {
        background-color: #f0f2f5;
        color: #1C4D86;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
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
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- Funções de Conexão e Carregamento de Dados ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """
    Conecta com o Google Sheets usando os secrets do Streamlit.
    """
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    credentials_info = st.secrets["gcp_service_account"]
    
    if isinstance(credentials_info, str):
        try:
            credentials_info = json.loads(credentials_info)
        except json.JSONDecodeError as e:
            st.error(f"Erro ao decodificar as credenciais JSON: {e}. Verifique a formatação do secrets.toml.")
            return None
    
    creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600)  # Cache de 10 minutos
def carregar_dados_pedidos():
    """Carrega os dados de pedidos do Google Sheets."""
    try:
        gc = get_gspread_client()
        
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Trata colunas de data
        date_cols = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']
        for col in date_cols:
            if col in df.columns and not df[col].empty:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # Trata colunas numéricas: Substitui vírgula por ponto e converte para numérico
        numeric_cols = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']
        for col in numeric_cols:
            if col in df.columns and not df[col].empty:
                # Remove separador de milhar (ponto) e substitui vírgula por ponto decimal
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Garante que colunas importantes existam
        if 'STATUS_PEDIDO' not in df.columns:
            df['STATUS_PEDIDO'] = ''
        if 'ORDEM_COMPRA' not in df.columns:
            df['ORDEM_COMPRA'] = ''
        if 'FORNECEDOR' not in df.columns:
            df['FORNECEDOR'] = ''
        if 'PREVISAO_ENTREGA' not in df.columns:
            df['PREVISAO_ENTREGA'] = pd.NaT
        if 'CODIGO_MATERIAL' not in df.columns:
            df['CODIGO_MATERIAL'] = ''

        # Define o status do pedido com base na data de entrega
        df['STATUS_PEDIDO'] = df['DATA_ENTREGA'].apply(
            lambda x: 'ENTREGUE' if pd.notna(x) else 'PENDENTE'
        )

        # Calcula a coluna VALOR_TOTAL após a conversão numérica
        if 'QUANTIDADE' in df.columns and 'VALOR_ITEM' in df.columns:
            df['VALOR_TOTAL'] = df['QUANTIDADE'] * df['VALOR_ITEM']
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        st.info("Verifique suas credenciais e a planilha.")
        return pd.DataFrame(columns=[
            "DATA", "SOLICITANTE", "DEPARTAMENTO", "REQUISICAO", "CODIGO_MATERIAL", "MATERIAL",
            "STATUS_PEDIDO", "DATA_APROVACAO", "DATA_ENTREGA", "ORDEM_COMPRA", "VALOR_ITEM", "FORNECEDOR", "PREVISAO_ENTREGA"
        ])


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

    if 'DATA' in df_pedidos.columns and not df_pedidos['DATA'].isnull().all():
        df_pedidos['MES'] = df_pedidos['DATA'].dt.month
        df_pedidos['ANO'] = df_pedidos['DATA'].dt.year
        meses_disponiveis = sorted(df_pedidos['MES'].dropna().unique())
        anos_disponiveis = sorted(df_pedidos['ANO'].dropna().unique(), reverse=True)
        meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                       7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        
        # Filtro de Mês como multiselect
        filtro_mes_dash = st.multiselect(
            "Selecione o(s) Mês(es):", 
            options=meses_disponiveis, 
            default=meses_disponiveis,
            format_func=lambda x: meses_nomes.get(x, x)
        )
        
        # Filtro de Ano como multiselect
        filtro_ano_dash = st.multiselect(
            "Selecione o(s) Ano(s):", 
            options=anos_disponiveis,
            default=anos_disponiveis
        )
    else:
        filtro_mes_dash = []
        filtro_ano_dash = []
        st.info("Nenhum dado com data disponível para filtrar.")


# Exibe o cabeçalho temático principal
st.markdown("""
    <div class='header-container'>
        <h1>🔎 PAINEL DE CONSULTA DE REQUISIÇÕES</h1>
        <p>Visualize e analise o histórico completo de pedidos de compra</p>
    </div>
""", unsafe_allow_html=True)


# Verifica se o DataFrame não está vazio antes de continuar
if df_pedidos.empty:
    st.info("Nenhum pedido registrado no sistema.")
    st.stop()


# --- FILTROS MOVIDOS PARA A PÁGINA PRINCIPAL ---
st.markdown("---")
st.subheader("Filtros de Dados")

col_filters1, col_filters2, col_filters3, col_filters4 = st.columns(4)

with col_filters1:
    filtro_solicitante = 'Todos'
    if 'SOLICITANTE' in df_pedidos.columns and not df_pedidos.empty:
        solicitantes_disponiveis = sorted(df_pedidos['SOLICITANTE'].dropna().unique().tolist())
        filtro_solicitante = st.selectbox(
            "Solicitante:",
            options=['Todos'] + solicitantes_disponiveis
        )

with col_filters2:
    filtro_departamento = 'Todos'
    if 'DEPARTAMENTO' in df_pedidos.columns and not df_pedidos.empty:
        departamentos_disponiveis = sorted(df_pedidos['DEPARTAMENTO'].dropna().unique().tolist())
        filtro_departamento = st.selectbox(
            "Departamento:",
            options=['Todos'] + departamentos_disponiveis
        )

with col_filters3:
    filtro_status = 'Todos'
    if 'STATUS_PEDIDO' in df_pedidos.columns and not df_pedidos.empty:
        status_disponiveis = df_pedidos['STATUS_PEDIDO'].dropna().unique().tolist()
        filtro_status = st.selectbox(
            "Status:",
            options=['Todos'] + sorted(status_disponiveis)
        )
with col_filters4:
    filtro_material_cod = 'Todos'
    if 'CODIGO_MATERIAL' in df_pedidos.columns and not df_pedidos.empty:
        cod_materiais_disponiveis = sorted(df_pedidos['CODIGO_MATERIAL'].dropna().unique().tolist())
        filtro_material_cod = st.selectbox(
            "Cód. Material:",
            options=['Todos'] + cod_materiais_disponiveis
        )

# --- Aplicação dos Filtros na Tabela Principal ---
df_filtrado = df_pedidos.copy()

# Aplica os filtros de meses e anos
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

df_tabela = df_filtrado.copy()

def formatar_status(status):
    if status == 'ENTREGUE':
        return '🟢 ENTREGUE'
    elif status == 'PENDENTE':
        return '⚪ PENDENTE'
    else:
        return '🟡 EM ANDAMENTO'

df_tabela['STATUS'] = df_tabela['STATUS_PEDIDO'].apply(formatar_status)

if 'DATA' in df_tabela.columns:
    df_tabela['DATA REQUISIÇÃO'] = df_tabela['DATA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
else:
    df_tabela['DATA REQUISIÇÃO'] = 'N/A'

if 'DATA_ENTREGA' in df_tabela.columns:
    df_tabela['DATA ENTREGA'] = df_tabela['DATA_ENTREGA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
else:
    df_tabela['DATA ENTREGA'] = 'N/A'

if 'PREVISAO_ENTREGA' in df_tabela.columns:
    df_tabela['PREVISÃO ENTREGA'] = df_tabela['PREVISAO_ENTREGA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
else:
    df_tabela['PREVISÃO ENTREGA'] = 'N/A'
    
# Converte o VALOR_TOTAL para string apenas para exibição
df_tabela['VALOR_TOTAL_str'] = df_tabela['VALOR_TOTAL'].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.dataframe(
    df_tabela[[
        'DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'CODIGO_MATERIAL', 'MATERIAL',
        'QUANTIDADE', 'VALOR_TOTAL_str', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'PREVISÃO ENTREGA', 'DATA ENTREGA'
    ]],
    use_container_width=True,
    hide_index=True,
    column_order=[
        'DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'CODIGO_MATERIAL', 'MATERIAL',
        'QUANTIDADE', 'VALOR_TOTAL_str', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'PREVISÃO ENTREGA', 'DATA ENTREGA'
    ],
    column_config={
        "DATA REQUISIÇÃO": st.column_config.DateColumn("Data Requisição"),
        "REQUISICAO": "N° Requisição",
        "SOLICITANTE": "Solicitante",
        "DEPARTAMENTO": "Departamento",
        "CODIGO_MATERIAL": "Cód. Material",
        "MATERIAL": "Material",
        "QUANTIDADE": "Quantidade",
        "VALOR_TOTAL_str": "Valor Total",  # Usa a nova coluna formatada
        "STATUS": "Status",
        "ORDEM_COMPRA": "N° Ordem de Compra",
        "FORNECEDOR": "Fornecedor",
        "PREVISÃO ENTREGA": st.column_config.DateColumn("Previsão Entrega"),
        "DATA ENTREGA": st.column_config.DateColumn("Data Entrega")
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
