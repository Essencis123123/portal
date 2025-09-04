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

# Configuração da página com layout wide e ícone
st.set_page_config(page_title="Painel de Consulta", layout="wide", page_icon="🔎")

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
    .stDownloadButton button p {
        color: white !important;
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
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_string = st.secrets["gcp_service_account"]
    creds_json = json.loads(creds_string)
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
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

        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
            if col in df.columns and not df[col].empty:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        for col in ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']:
            if col in df.columns and not df[col].empty:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        if 'STATUS_PEDIDO' not in df.columns:
            df['STATUS_PEDIDO'] = ''
        if 'ORDEM_COMPRA' not in df.columns:
            df['ORDEM_COMPRA'] = ''
        if 'FORNECEDOR' not in df.columns:
            df['FORNECEDOR'] = ''

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        st.info("Verifique suas credenciais e a planilha.")
        return pd.DataFrame(columns=[
            "DATA", "SOLICITANTE", "DEPARTAMENTO", "REQUISICAO", "MATERIAL",
            "STATUS_PEDIDO", "DATA_APROVACAO", "DATA_ENTREGA", "ORDEM_COMPRA", "VALOR_ITEM", "FORNECEDOR"
        ])


# --- LAYOUT E FILTROS DO SIDEBAR ---
with st.sidebar:
    if logo_img:
        st.image(logo_img, use_container_width=True)
    
    st.title("🔎 Painel de Consulta")
    st.divider()
    
    df_pedidos = carregar_dados_pedidos()
    
    # Adicionando um botão de recarregar dados
    if st.button("🔄 Recarregar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.subheader("Filtros de Período")
    if 'DATA' in df_pedidos.columns and not df_pedidos['DATA'].isnull().all():
        data_minima = st.date_input("De:", value=df_pedidos['DATA'].min() or datetime.date.today())
        data_maxima = st.date_input("Até:", value=df_pedidos['DATA'].max() or datetime.date.today())
    else:
        data_minima = None
        data_maxima = None
        st.info("Nenhum dado com data disponível para filtrar.")

    st.subheader("Filtros de Dados")
    filtro_solicitante = 'Todos'
    if 'SOLICITANTE' in df_pedidos.columns and not df_pedidos.empty:
        solicitantes_disponiveis = sorted(df_pedidos['SOLICITANTE'].dropna().unique().tolist())
        filtro_solicitante = st.selectbox(
            "Filtrar por Solicitante:",
            options=['Todos'] + solicitantes_disponiveis
        )
    
    filtro_departamento = 'Todos'
    if 'DEPARTAMENTO' in df_pedidos.columns and not df_pedidos.empty:
        departamentos_disponiveis = sorted(df_pedidos['DEPARTAMENTO'].dropna().unique().tolist())
        filtro_departamento = st.selectbox(
            "Filtrar por Departamento:",
            options=['Todos'] + departamentos_disponiveis
        )

    filtro_status = []
    if 'STATUS_PEDIDO' in df_pedidos.columns and not df_pedidos.empty:
        status_disponiveis = df_pedidos['STATUS_PEDIDO'].dropna().unique().tolist()
        filtro_status = st.multiselect(
            "Filtrar por Status:",
            options=['Todos'] + sorted(status_disponiveis),
            default=['Todos']
        )


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

# --- Aplicação dos Filtros na Tabela Principal ---
df_filtrado = df_pedidos.copy()

if data_minima and data_maxima and 'DATA' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['DATA'].dt.date.between(data_minima, data_maxima)]

if filtro_solicitante != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['SOLICITANTE'] == filtro_solicitante]

if filtro_departamento != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['DEPARTAMENTO'] == filtro_departamento]

if filtro_status and 'Todos' not in filtro_status:
    df_filtrado = df_filtrado[df_filtrado['STATUS_PEDIDO'].isin(filtro_status)]

if df_filtrado.empty:
    st.warning("Nenhum pedido encontrado com os filtros aplicados.")
    st.stop()


# --- Análise e Métricas ---
st.subheader("Visão Geral do Período")
col1, col2, col3 = st.columns(3)
with col1:
    total_pedidos = len(df_filtrado)
    st.metric("Total de Pedidos", total_pedidos)
with col2:
    pedidos_pendentes = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'PENDENTE'])
    st.metric("Pedidos Pendentes", pedidos_pendentes)
with col3:
    pedidos_entregues = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'ENTREGUE'])
    st.metric("Pedidos Entregues", pedidos_entregues)

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

st.dataframe(
    df_tabela[[
        'DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'MATERIAL', 
        'QUANTIDADE', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'DATA ENTREGA'
    ]],
    use_container_width=True,
    hide_index=True,
    column_order=[
        'DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'MATERIAL', 
        'QUANTIDADE', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'DATA ENTREGA'
    ],
    column_config={
        "DATA REQUISIÇÃO": st.column_config.DateColumn("Data Requisição"),
        "REQUISICAO": "N° Requisição",
        "SOLICITANTE": "Solicitante",
        "DEPARTAMENTO": "Departamento",
        "MATERIAL": "Material",
        "QUANTIDADE": "Quantidade",
        "STATUS": "Status",
        "ORDEM_COMPRA": "N° Ordem de Compra",
        "FORNECEDOR": "Fornecedor",
        "DATA ENTREGA": "Data Entrega"
    }
)

# Botão de download para o CSV
csv_pedidos = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Exportar Tabela para CSV",
    data=csv_pedidos,
    file_name=f"pedidos_consulta_{datetime.date.today()}.csv",
    mime="text/csv",
    help="Clique para baixar os dados da tabela filtrada."
)
