import streamlit as st
import pandas as pd
import datetime
import os
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from PIL import Image
from io import BytesIO
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import json
import re
import pytz
import numpy as np

st.set_page_config(page_title="Painel Financeiro - Almoxarifado", layout="wide", page_icon="💼")

st.markdown(
    """
    <style>
    /* SAP Fiori Color Palette */
    :root {
        --sap-blue: #0854a0;
        --sap-light-blue: #427cac;
        --sap-dark-blue: #1c4d86;
        --sap-accent: #00a4ef;
        --sap-success: #107e3e;
        --sap-warning: #e26100;
        --sap-error: #b00;
        --sap-neutral: #6a6d70;
        --sap-background: #fafafa;
        --sap-white: #ffffff;
        --sap-light-gray: #f2f2f2;
        --sap-border: #e5e5e5;
        --shadow-level-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        --shadow-level-2: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
        --shadow-level-3: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
    }

    /* Reset and base styling */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
        font-size: 1rem;
        line-height: 1.5;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sap-dark-blue) 0%, var(--sap-blue) 100%);
        border-right: 1px solid var(--sap-border);
        color: white;
    }
    
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
    .stDownloadButton button p { color: white !important; }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span { color: white !important; }

    [data-testid="stSidebar"] .stMultiSelect label p { color: white !important; }
    [data-testid="stSidebar"] .stMultiSelect div[role="listbox"] * { color: black !important; }
    [data-testid="stSidebar"] .stDateInput label p { color: white !important; }
    [data-testid="stSidebar"] .stDateInput input { color: black !important; }

    /* Modern Button Styling */ 
    .stButton button { 
        background: linear-gradient(135deg, var(--sap-blue) 0%, var(--sap-accent) 100%);
        color: var(--sap-white) !important; 
        border: none;
        border-radius: 6px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-level-1);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    } 

    .stButton button:hover {
        box-shadow: var(--shadow-level-2);
        transform: translateY(-2px);
    }

    .stButton button p { 
        color: var(--sap-white) !important; 
        margin: 0;
    } 
    
    .stDownloadButton button p { color: white !important; }

    [data-testid="stSidebar"] img {
        display: block; margin-left: auto; margin-right: auto;
        width: 80%; border-radius: 12px; padding: 1rem 0;
        box-shadow: var(--shadow-level-1);
    }

    /* Modern Header */
    .modern-header {
        background: linear-gradient(135deg, var(--sap-blue) 0%, var(--sap-dark-blue) 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-level-2);
        color: var(--sap-white);
    }

    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .header-title {
        font-size: 1.8rem;
        font-weight: 300;
        margin: 0;
        color: var(--sap-white);
    }

    .header-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0.25rem 0 0 0;
        font-weight: 300;
    }

    /* Breadcrumbs */
    .breadcrumbs {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
        color: var(--sap-neutral);
    }

    .breadcrumb-item {
        color: var(--sap-neutral);
        text-decoration: none;
        transition: color 0.2s ease;
    }

    .breadcrumb-item:hover {
        color: var(--sap-blue);
    }

    .breadcrumb-separator {
        color: var(--sap-border);
    }

    /* Modern Typography */ 
    h2, h3 { 
        color: var(--sap-dark-blue); 
        font-weight: 400; 
        line-height: 1.3;
    } 

    /* Modern Metrics Cards */ 
    [data-testid="stMetric"] > div { 
        background: var(--sap-white); 
        color: var(--sap-dark-blue); 
        padding: 1.5rem; 
        border-radius: 12px; 
        box-shadow: var(--shadow-level-1); 
        border: 1px solid var(--sap-border);
        transition: all 0.3s ease;
        text-align: center;
    }

    [data-testid="stMetric"] > div:hover {
        box-shadow: var(--shadow-level-2);
        transform: translateY(-2px);
    }

    [data-testid="stMetric"] .stMetricValue {
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    [data-testid="stMetric"] .stMetricLabel {
        font-size: 0.9rem;
        opacity: 0.8;
    }

    /* Modern Input Fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input {
        border: 2px solid var(--sap-border) !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease !important;
        background: var(--sap-white) !important;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within,
    .stDateInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--sap-accent) !important;
        box-shadow: 0 0 0 3px rgba(0, 164, 239, 0.1) !important;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .header-content {
            flex-direction: column;
            text-align: center;
        }
        
        .modern-header {
            padding: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Ordem padrão das colunas
COLUNA_ORDEM_PADRAO_FISCAL = [
    "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO",
    "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS",
    "VALOR_FRETE", "DOC_NF", "RECEBEDOR", "DIAS_VENCIMENTO",
    "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
]

@st.cache_data(show_spinner=False)
def load_logo(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

def render_modern_header(title, subtitle, show_back_button=True):
    """Render modern header with breadcrumbs"""
    # Breadcrumbs
    breadcrumb_html = """
        <div class="breadcrumbs">
            <a href="main_app.py" class="breadcrumb-item">🏠 Início</a>
            <span class="breadcrumb-separator">›</span>
            <span class="breadcrumb-item">Painel Fiscal</span>
        </div>
    """ if show_back_button else ""
    
    # Header
    header_html = f"""
        {breadcrumb_html}
        <div class="modern-header">
            <div class="header-content">
                <div>
                    <h1 class="header-title">{title}</h1>
                    <p class="header-subtitle">{subtitle}</p>
                </div>
            </div>
        </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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

def parse_date_input(date_value):
    """
    Converte valores de data de qualquer entrada para datetime,
    suportando formatos comuns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD).
    Retorna pd.NaT para valores inválidos.
    """
    if pd.isna(date_value) or date_value == '' or date_value is None:
        return pd.NaT
    
    if isinstance(date_value, (pd.Timestamp, datetime.datetime)):
        return date_value
    
    if isinstance(date_value, datetime.date):
        return datetime.datetime.combine(date_value, datetime.time())
    
    if isinstance(date_value, str):
        # Remove espaços em branco
        date_value = date_value.strip()
        
        # Primeiro tenta formatos específicos brasileiros
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_value, fmt)
            except ValueError:
                continue
        
        # Se não funcionar, tenta o parser do pandas
        try:
            dt = pd.to_datetime(date_value, dayfirst=True, errors='coerce')
            if pd.notna(dt):
                return dt
        except:
            pass
                
    return pd.NaT

def converter_para_float_brasileiro(valor_str):
    """
    Converte string no formato brasileiro (ex: "5,58") para float (5.58)
    """
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    if not isinstance(valor_str, str):
        return 0.0
    
    # Remove possíveis R$ e espaços
    valor_str = valor_str.replace('R$', '').strip()
    
    # Substitui vírgula por ponto and remove pontos de milhar
    if ',' in valor_str and '.' in valor_str:
        # Formato com milhar: 1.234,56 → 1234.56
        valor_str = valor_str.replace('.', '').replace(',', '.')
    elif ',' in valor_str:
        # Formato simples com vírgula decimal: 1234,56 → 1234.56
        valor_str = valor_str.replace(',', '.')
    
    try:
        return float(valor_str)
    except ValueError:
        return 0.0

def formatar_numero_brasileiro(valor, casas_decimais=2):
    """Formata número no padrão brasileiro (vírgula como separador decimal)"""
    if pd.isna(valor) or valor == 0:
        return ''
    return f"{valor:,.{casas_decimais}f}".replace('.', '|').replace(',', '.').replace('|', ',')

def _to_datetime(series):
    return pd.to_datetime(series, errors="coerce", dayfirst=True)

def carregar_dados() -> pd.DataFrame:
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df = pd.DataFrame(worksheet.get_all_records())

        colunas_obrigatorias = [
            "DATA", "FORNECEDOR_NF", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "OBSERVACAO", "VALOR_JUROS",
            "VALOR_FRETE", "DOC_NF", "RECEBEDOR", "CONDICAO_FRETE",
            "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
        ]

        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = None

        df = df.rename(columns={
            'STATUS_FINANCEIRO': 'STATUS',
            'OBSERVACAO': 'REGISTRO_ADICIONAL',
            'FORNECEDOR_NF': 'FORNECEDOR',
            'V. TOTAL NF': 'V_TOTAL_NF',
            'DOC NF': 'DOC_NF',
        }, errors='ignore')

        df = df.loc[:,~df.columns.duplicated()]

        df = df.dropna(how='all')
        if not df.empty:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        for c in ["V_TOTAL_NF", "VALOR_JUROS", "VALOR_FRETE"]:
            if c in df.columns:
                df[c] = df[c].apply(converter_para_float_brasileiro).fillna(0.0)
            else:
                df[c] = 0.0

        df["DATA"] = _to_datetime(df["DATA"])
        df["VENCIMENTO"] = _to_datetime(df["VENCIMENTO"])
        df["REGISTRO_ENVIO"] = _to_datetime(df["REGISTRO_ENVIO"])
        df["REGISTRO_LANCAMENTO"] = _to_datetime(df["REGISTRO_LANCAMENTO"])

        ref = pd.Timestamp.today().normalize()
        df["DIAS_VENCIMENTO"] = (df["VENCIMENTO"] - ref).dt.days.fillna(0).astype(int)

        # Garante que todas as colunas padrão existam
        for col in COLUNA_ORDEM_PADRAO_FISCAL:
            if col not in df.columns:
                df[col] = ''

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha. Verifique nome/aba/credenciais. Detalhe: {e}")
        return pd.DataFrame(columns=COLUNA_ORDEM_PADRAO_FISCAL)

def salvar_dados(df: pd.DataFrame) -> bool:
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df_to_save = df.copy()

        df_to_save["DATA"] = _to_datetime(df_to_save["DATA"])
        df_to_save["VENCIMENTO"] = _to_datetime(df_to_save["VENCIMENTO"])
        df_to_save["REGISTRO_ENVIO"] = _to_datetime(df_to_save["REGISTRO_ENVIO"])
        df_to_save["REGISTRO_LANCAMENTO"] = _to_datetime(df_to_save["REGISTRO_LANCAMENTO"])

        df_to_save = df_to_save.rename(columns={
            "STATUS": "STATUS_FINANCEIRO",
            "REGISTRO_ADICIONAL": "OBSERVACAO",
            "V_TOTAL_NF": "V. TOTAL NF",
            "DOC_NF": "DOC NF",
            "FORNECEDOR": "FORNECEDOR_NF"
        }, errors='ignore')

        if "DATA" in df_to_save.columns:
            df_to_save["DATA"] = df_to_save["DATA"].dt.strftime("%d/%m/%Y")
        if "VENCIMENTO" in df_to_save.columns:
            df_to_save["VENCIMENTO"] = df_to_save["VENCIMENTO"].dt.strftime("%d/%m/%Y")
        if "REGISTRO_ENVIO" in df_to_save.columns:
            df_to_save["REGISTRO_ENVIO"] = df_to_save["REGISTRO_ENVIO"].dt.strftime("%d/%m/%Y %H:%M:%S")
        if "REGISTRO_LANCAMENTO" in df_to_save.columns:
            df_to_save["REGISTRO_LANCAMENTO"] = df_to_save["REGISTRO_LANCAMENTO"].dt.strftime("%d/%m/%Y %H:%M:%S")

        df_to_save = df_to_save.drop(columns=["DIAS_VENCIMENTO"], errors="ignore")

        # Formata números no padrão brasileiro antes de salvar
        numeric_cols = ['V_TOTAL_NF', 'VALOR_JUROS', 'VALOR_FRETE']
        for col in numeric_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: formatar_numero_brasileiro(x) if pd.notna(x) and x != '' else '0,00'
                )

        set_with_dataframe(worksheet, df_to_save, include_index=False, resize=True)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados na planilha: {e}")
        return False

USERS = {
    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},
    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},
    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAULA SOARES"},
    "acsouza@essencis.com.br": {"password": "Essencis01", "name": "ANDRE CASTRO DE SOUZA"},
    "bcampos@essencis.com.br": {"password": "Essencis01", "name": "BARBARA DA SILVA CAMPOS"},
    "earaujo@essencis.com.br": {"password": "Essencis01", "name": "EMERSON ALMEIDA DE ARAUJO"},
    "wrezende@essencis.com.br": {"password": "Essencis01", "name": "WELLINGTON CASSIO DE REZENDE"}
}

def fazer_login(email, senha):
    if email in USERS and USERS[email]["password"] == senha:
        st.session_state['logado'] = True
        st.session_state['nome_colaborador'] = USERS[email]["name"]
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
        time.sleep(1)
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

if 'logado' not in st.session_state or not st.session_state.logado:
    st.title("Login - Painel de Notas Fiscais")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    if 'df' not in st.session_state:
        st.session_state.df = carregar_dados()

    if 'ultimo_salvamento' not in st.session_state:
        st.session_state.ultimo_salvamento = None
    if 'alteracoes_pendentes' not in st.session_state:
        st.session_state.alteracoes_pendentes = False

    df = st.session_state.df

    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)

        st.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")
        st.title("💼 Menu Financeiro")

        menu = st.radio(
            "📌 Navegação",
            ["📋 Lançamentos", "💰 Gestão de Juros", "📊 Dashboards", "⚙️ Configurações"]
        )
        st.divider()

        st.subheader("Filtros de Período")
        if 'DATA' in df.columns and not df['DATA'].isnull().all():
            min_date_value = df['DATA'].min() if not df['DATA'].isnull().all() else datetime.date.today()
            max_date_value = df['DATA'].max() if not df['DATA'].isnull().all() else datetime.date.today()
            data_minima = st.date_input("De:", value=min_date_value)
            data_maxima = st.date_input("Até:", value=max_date_value)
        else:
            data_minima = None
            data_maxima = None
            st.info("Nenhum dado com data disponível para filtrar.")

        st.subheader("Filtros de Dados")
        filtro_status = ['Todos']
        if 'STATUS' in df.columns and not df.empty:
            status_disponiveis = df['STATUS'].dropna().unique().tolist()
            filtro_status = st.multiselect(
                "Filtrar por Status:",
                options=['Todos'] + sorted(status_disponiveis),
                default=['Todos']
            )

        filtro_fornecedor = ['Todos']
        if 'FORNECEDOR' in df.columns and not df.empty:
            fornecedores_disponiveis = df['FORNECEDOR'].dropna().unique().tolist()
            filtro_fornecedor = st.multiselect(
                "Filtrar por Fornecedor:",
                options=['Todos'] + sorted(fornecedores_disponiveis),
                default=['Todos']
            )

        st.divider()
        if st.button("Logout"):
            st.session_state.logado = False
            st.rerun()

        st.caption("Sistema Financeiro Completo v1.0")

    headers = {
        "📋 Lançamentos": ("📋 VISUALIZAÇÃO DE NOTAS FISCAIS", "Gerenciamento e acompanhamento financeiro de NFs"),
        "💰 Gestão de Juros": ("💰 GESTÃO DE JUROS E MULTAS", "Calcule e gerencie juros para notas em atraso"),
        "📊 Dashboards": ("📊 DASHBOARDS FINANCEIROS COMPLETOS", "Análise estratégica de custos e eficiências"),
        "⚙️ Configurações": ("⚙️ CONFIGURAÇões DO SISTEMA", "Parâmetros e manutenção de dados"),
    }
    titulo, subtitulo = headers.get(menu)
    st.markdown(f"""
        <div class='header-container'>
            <h1>{titulo}</h1>
            <p>{subtitulo}</p>
        </div>
    """, unsafe_allow_html=True)

    if menu == "📋 Lançamentos":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("💾 Salvar Tudo", use_container_width=True):
                if salvar_dados(df):
                    st.session_state.ultimo_salvamento = datetime.datetime.now()
                    st.session_state.alteracoes_pendentes = False
                    st.success("Dados salvos com sucesso!")
                    time.sleep(1)
                    st.rerun()
        with col2:
            if st.button("🔄 Recarregar", use_container_width=True):
                st.session_state.df = carregar_dados()
                st.rerun()
        with col4:
            if st.session_state.ultimo_salvamento:
                st.info(f"Último save: {st.session_state.ultimo_salvamento.strftime('%H:%M:%S')}")
            elif st.session_state.alteracoes_pendentes:
                st.warning("Alterações não salvas")

        if not df.empty:
            df_filtrado = df.copy()

            if 'DATA' in df_filtrado.columns and data_minima and data_maxima:
                df_filtrado = df_filtrado[df_filtrado['DATA'].dt.date.between(data_minima, data_maxima)]

            if 'Todos' not in filtro_status:
                df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(filtro_status)]
            if 'Todos' not in filtro_fornecedor:
                df_filtrado = df_filtrado[df_filtrado['FORNECEDOR'].isin(filtro_fornecedor)]
            
            df_display = df_filtrado

            st.markdown("---")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            total_nfs = len(df_display)
            total_valor = df_display['V_TOTAL_NF'].sum()
            nfs_pendentes = len(df_display[df_display['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])])
            total_juros = df_display['VALOR_JUROS'].sum()
            total_frete = df_display['VALOR_FRETE'].sum()

            c1.metric("📊 Total de NFs", total_nfs)
            c2.metric("💰 Valor NFs", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c3.metric("⏳ Pendentes", nfs_pendentes)
            c4.metric("✅ Finalizadas", total_nfs - nfs_pendentes)
            c5.metric("💸 Juros", f"R$ {total_juros:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c6.metric("🚚 Fretes", f"R$ {total_frete:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            st.markdown("---")
            st.subheader("📋 Detalhes das Notas Fiscais")

            status_map = {
                'EM ANDAMENTO': '🟡 EM ANDAMENTO',
                'NF PROBLEMA': '🔴 NF PROBLEMA',
                'CAPTURADO': '🟣 CAPTURADO',
                'FINALIZADO': '🟢 FINALIZADO'
            }
            reverse_status_map = {v: k for k, v in status_map.items()}

            df_display['STATUS_VISUAL'] = df_display['STATUS'].map(status_map).fillna('⚪ DESCONHECIDO')
            
            def formatar_vencimento_visual(dias):
                if pd.isna(dias): return "N/A"
                if dias <= 7:
                    return f"🔴 {dias}"
                elif dias <= 10:
                    return f"🟡 {dias}"
                return str(dias)
            df_display['DIAS_VENCIMENTO_VISUAL'] = df_display['DIAS_VENCIMENTO'].apply(formatar_vencimento_visual)

            def formatar_problema_visual(row):
                if str(row.get('CONDICAO_PROBLEMA')) == 'CHAMADO':
                    data_problema = datetime.date(2025, 9, 29)
                    dias_passados = (datetime.date.today() - data_problema).days
                    if dias_passados > 5:
                        return f"🔴 {row['CONDICAO_PROBLEMA']}"
                return row['CONDICAO_PROBLEMA']
            
            df_display['PROBLEMA_VISUAL'] = df_display.apply(lambda row: formatar_problema_visual(row), axis=1)

            problema_options = ["N/A", "SEM PEDIDO", "VALOR INCORRETO", "OUTRO", "CHAMADO", "CARTA CORRECAO", "AJUSTE OC", "RECUSA"]

            df_display['REGISTRO_ENVIO'] = pd.to_datetime(df_display['REGISTRO_ENVIO'], errors='coerce')
            df_display['REGISTRO_LANCAMENTO'] = pd.to_datetime(df_display['REGISTRO_LANCAMENTO'], errors='coerce')

            df_display['REGISTRO_ENVIO_VISUAL'] = df_display['REGISTRO_ENVIO'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
            df_display['REGISTRO_LANCAMENTO_VISUAL'] = df_display['REGISTRO_LANCAMENTO'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')

            df_display['V_TOTAL_NF'] = df_display['V_TOTAL_NF'].astype(float)
            
            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                column_config={
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
                    "FORNECEDOR": "Fornecedor",
                    "NF": "N° NF",
                    "ORDEM_COMPRA": "N° Ordem de Compra",
                    "V_TOTAL_NF": st.column_config.NumberColumn("V. Total NF (R$)", format="%.2f"),
                    "VENCIMENTO": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                    "DIAS_VENCIMENTO_VISUAL": st.column_config.Column("Dias Vencimento", disabled=True),
                    "STATUS_VISUAL": st.column_config.SelectboxColumn("Status", options=list(status_map.values()), default="🟡 EM ANDAMENTO"),
                    "PROBLEMA_VISUAL": st.column_config.SelectboxColumn("Problema", options=problema_options),
                    "REGISTRO_ADICIONAL": "Obs.",
                    "VALOR_JUROS": st.column_config.NumberColumn("Juros (R$)", format="%.2f"),
                    "VALOR_FRETE": st.column_config.NumberColumn("Frete (R$)", format="%.2f"),
                    "DOC_NF": st.column_config.LinkColumn("DOC NF", display_text="📥"),
                    "RECEBEDOR": "Recebedor",
                    "REGISTRO_ENVIO_VISUAL": st.column_config.TextColumn("Reg. Envio (Almox.)", disabled=True),
                    "REGISTRO_LANCAMENTO_VISUAL": st.column_config.TextColumn("Reg. Lançamento (Fin.)"),
                },
                column_order=[
                    "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO", "DIAS_VENCIMENTO_VISUAL",
                    "STATUS_VISUAL", "PROBLEMA_VISUAL", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC_NF", "RECEBEDOR",
                    "REGISTRO_ENVIO_VISUAL", "REGISTRO_LANCAMENTO_VISUAL"
                ],
                hide_index=True
            )

            if not edited_df.equals(df_display):
                st.session_state.alteracoes_pendentes = True
                
                updated_df = df.copy()
                
                brasilia_tz = pytz.timezone('America/Sao_Paulo')
                
                for index, row in edited_df.iterrows():
                    novo_status_visual = row['STATUS_VISUAL']
                    novo_status_data = reverse_status_map.get(novo_status_visual)
                    
                    if novo_status_data:
                        status_original = updated_df.loc[index, 'STATUS']

                        if novo_status_data == 'FINALIZADO' and status_original != 'FINALIZADO':
                            updated_df.loc[index, 'REGISTRO_LANCAMENTO'] = datetime.datetime.now(brasilia_tz)
                        
                        if novo_status_data == 'CAPTURADO' and status_original != 'CAPTURADO':
                            updated_df.loc[index, 'REGISTRO_LANCAMENTO'] = datetime.datetime.now(brasilia_tz)
                        
                        if novo_status_data == 'CAPTURADO' and status_original != 'CAPTURADO':
                            updated_df.loc[index, 'REGISTRO_ENVIO'] = datetime.datetime.now(brasilia_tz)
                        
                        updated_df.loc[index, 'STATUS'] = novo_status_data
                        updated_df.loc[index, 'CONDICAO_PROBLEMA'] = str(row['PROBLEMA_VISUAL']).replace('🔴 ', '')
                        updated_df.loc[index, 'VALOR_JUROS'] = row['VALOR_JUROS']
                        updated_df.loc[index, 'VALOR_FRETE'] = row['VALOR_FRETE']
                        updated_df.loc[index, 'V_TOTAL_NF'] = row['V_TOTAL_NF']
                        
                st.session_state.df = updated_df

                if salvar_dados(st.session_state.df):
                    st.session_state.ultimo_salvamento = datetime.datetime.now()
                    st.session_state.alteracoes_pendentes = False
                    st.success("Alterações salvas com sucesso!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("📝 Nenhuma nota fiscal registrada no sistema. As notas cadastradas no Painel do Almoxarifado aparecerão aqui.")

    elif menu == "💰 Gestão de Juros":
        st.header("💰 Gestão de Juros e Multas")

        if not df.empty:
            nfs_com_problema = df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])]
            if not nfs_com_problema.empty:
                st.subheader("Notas com Possibilidade de Juros")

                for idx, row in nfs_com_problema.iterrows():
                    valor_nf_str = f"R$ {row['V_TOTAL_NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    title = f"NF {row['NF']} - {row['FORNECEDOR']} - {valor_nf_str}"
                    with st.expander(title):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            venc = row['VENCIMENTO'].strftime('%d/%m/%Y') if pd.notna(row['VENCIMENTO']) else 'N/A'
                            st.info(f"**Vencimento:** {venc}")
                            default_atraso = int(max(0, -int(row.get('DIAS_VENCIMENTO', 0))))
                            dias_atraso = st.number_input("Dias em Atraso", min_value=0, value=default_atraso, key=f"dias_{idx}")

                        with col2:
                            st.info(f"**Valor Original:** {valor_nf_str}")
                            taxa_juros = st.number_input("Taxa de Juros (%)", min_value=0.0, max_value=100.0, value=1.0, step=0.1, key=f"taxa_{idx}")

                        with col3:
                            valor_juros = (row['V_TOTAL_NF'] * (taxa_juros / 100.0)) * dias_atraso
                            st.metric("Valor de Juros", f"R$ {valor_juros:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            if st.button("Aplicar Juros", key=f"apply_{idx}"):
                                df.at[idx, 'VALOR_JUROS'] = float(valor_juros)
                                st.session_state.alteracoes_pendentes = True
                                st.success("Juros aplicados com sucesso!")
                                time.sleep(1)
                                st.rerun()

                st.subheader("📈 Resumo de Juros Aplicados")
                if "DATA" in df.columns:
                    base = df.copy()
                    base["DATA"] = _to_datetime(base["DATA"])
                    juros_por_mes = base.groupby(base['DATA'].dt.to_period('M'))['VALOR_JUROS'].sum().reset_index()
                    juros_por_mes['DATA'] = juros_por_mes['DATA'].dt.to_timestamp()

                    if not juros_por_mes.empty:
                        fig_juros = px.bar(
                            juros_por_mes, x='DATA', y='VALOR_JUROS',
                            title='Evolução dos Juros Mensais',
                            labels={'VALOR_JUROS': 'Valor de Juros (R$)', 'DATA': 'Mês'}
                        )
                        st.plotly_chart(fig_juros, use_container_width=True)

                juros_por_fornecedor = df.groupby('FORNECEDOR')['VALOR_JUROS'].sum().nlargest(10).reset_index()
                if not juros_por_fornecedor.empty:
                    fig_fornecedor = px.pie(
                        juros_por_fornecedor, values='VALOR_JUROS', names='FORNECEDOR',
                        title='Distribuição de Juros por Fornecedor (Top 10)'
                    )
                    st.plotly_chart(fig_fornecedor, use_container_width=True)
            else:
                st.info("Nenhuma nota fiscal para calcular juros.")
        else:
            st.info("Nenhum dado disponível.")

    elif menu == "📊 Dashboards":
        st.header("📊 Dashboards Financeiros Completos")

        if not df.empty:
            df["DATA"] = _to_datetime(df["DATA"])

            df['MES_ANO'] = df['DATA'].dt.to_period('M')
            df['ANO'] = df['DATA'].dt.year
            df['MES'] = df['DATA'].dt.month

            dados_mensais = df.groupby('MES_ANO').agg({
                'V_TOTAL_NF': 'sum',
                'VALOR_FRETE': 'sum',
                'VALOR_JUROS': 'sum',
                'NF': 'count'
            }).reset_index()
            dados_mensais['MES_ANO'] = dados_mensais['MES_ANO'].dt.to_timestamp()

            anos = sorted(df['ANO'].dropna().unique())
            if len(anos) >= 2:
                st.subheader("📅 Comparativo Anual")

                comparativo_anual = df.groupby('ANO').agg({
                    'V_TOTAL_NF': 'sum',
                    'VALOR_FRETE': 'sum',
                    'VALOR_JUROS': 'sum',
                    'NF': 'count'
                }).reset_index()

                fig_comparativo = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Valor Total', 'Custo com Fretes', 'Juros Pagos', 'Quantidade de NFs')
                )

                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['V_TOTAL_NF'], name='Valor Total'), row=1, col=1)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_FRETE'], name='Fretes'), row=1, col=2)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_JUROS'], name='Juros'), row=2, col=1)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['NF'], name='Qtd NFs'), row=2, col=2)

                fig_comparativo.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_comparativo, use_container_width=True)

            st.subheader("🚚 Análise de Fretes")
            col1, col2 = st.columns(2)

            with col1:
                if 'CONDICAO_FRETE' in df.columns:
                    frete_tipo = df.groupby('CONDICAO_FRETE')['VALOR_FRETE'].sum().reset_index()
                    if not frete_tipo.empty:
                        fig_frete_tipo = px.pie(
                            frete_tipo, values='VALOR_FRETE', names='CONDICAO_FRETE',
                            title='Distribuição por Tipo de Frete'
                        )
                        st.plotly_chart(fig_frete_tipo, use_container_width=True)

            with col2:
                if not dados_mensais.empty:
                    fig_frete_evolucao = px.line(
                        dados_mensais, x='MES_ANO', y='VALOR_FRETE',
                        title='Evolução Mensal dos Gastos com Frete',
                        labels={'VALOR_FRETE': 'Valor do Frete (R$)', 'MES_ANO': 'Mês'}
                    )
                    st.plotly_chart(fig_frete_evolucao, use_container_width=True)

            st.subheader("💸 Análise de Custos")
            custos_totais = pd.DataFrame({
                'Tipo': ['Valor NFs', 'Fretes', 'Juros'],
                'Valor': [df['V_TOTAL_NF'].sum(), df['VALOR_FRETE'].sum(), df['VALOR_JUROS'].sum()]
            })

            fig_custos = px.bar(custos_totais, x='Tipo', y='Valor', title='Distribuição Total de Custos', color='Tipo')
            st.plotly_chart(fig_custos, use_container_width=True)

            st.subheader("📈 Métricas de Eficiência")
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)

            with col_met1:
                custo_total = df['V_TOTAL_NF'].sum() + df['VALOR_FRETE'].sum() + df['VALOR_JUROS'].sum()
                st.metric("Custo Total", f"R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            with col_met2:
                vt = df['V_TOTAL_NF'].sum()
                perc_frete = (df['VALOR_FRETE'].sum() / vt * 100) if vt > 0 else 0
                st.metric("% Frete/NF", f"{perc_frete:.2f}%")

            with col_met3:
                vt = df['V_TOTAL_NF'].sum()
                perc_juros = (df['VALOR_JUROS'].sum() / vt * 100) if vt > 0 else 0
                st.metric("% Juros/NF", f"{perc_juros:.2f}%")

            with col_met4:
                nfs_com_juros = int((df['VALOR_JUROS'] > 0).sum())
                st.metric("Nfs com Juros", f"{nfs_com_juros}")
        else:
            st.info("Nenhum dado disponível.")

    elif menu == "⚙️ Configurações":
        st.header("⚙️ Configurações do Sistema")

        st.subheader("Manutenção de Dados")
        if st.button("🔄 Forçar Recarregamento de Dados"):
            st.session_state.df = carregar_dados()
            st.success("Cache limpo e dados recarregados com sucesso!")
            st.rerun()

        st.subheader("Exportação de Dados")
        if not df.empty:
            csv = df.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="dados_financeiros_completos.csv",
                mime="text/csv"
            )
        else:
            st.info("Não há dados para exportar.")

        st.subheader("Log de Atividades")
        if 'log_messages' in st.session_state:
            log_text = "\n".join(st.session_state['log_messages'])
            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)
        else:
            st.info("Nenhum log disponível.")
