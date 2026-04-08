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
import numpy as np 
import gspread 
from gspread_dataframe import set_with_dataframe 
from google.oauth2.service_account import Credentials 
import json 
import re 
import pytz 
import sys 

# ============================================================================== 
# CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO CSS 
# ============================================================================== 
# Configuração da página com layout wide and ícone 
st.set_page_config(page_title="Painel do Comprador", layout="wide", page_icon="👨‍💼") 

# --- CSS Personalizado para o Tema Essencis --- 
st.markdown( 
    """ 
    <style> 
    /* Aumenta o tamanho da fonte de todo o corpo do aplicativo */ 
    html, body, [data-testid="stAppViewContainer"] { 
        font-size: 1.1rem; 
    } 
     
    /* Cor do menu lateral e texto */ 
    [data-testid="stSidebar"] { 
        background-color: #1C4D86; 
        color: white; 
    } 
     
    /* Regras para garantir que TODO o texto no sidebar seja branco */ 
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] p, 
    [data.testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j p, 
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j, 
    .stDownloadButton button p { 
        color: white !important; 
    } 

    /* ESTILOS ESPECÍFICOS PARA O MENU DE NAVEGAÇÃO */ 
    /* Container principal do radio button */ 
    [data-testid="stSidebar"] .stRadio { 
        background-color: #1C4D86; 
    } 
     
    /* Container dos itens do menu */ 
    [data-testid="stSidebar"] .stRadio > div { 
        background-color: #1C4D86; 
        border: none; 
    } 
     
    /* Labels dos itens do menu */ 
    [data-testid="stSidebar"] .stRadio label { 
        color: white !important; 
        font-weight: 500; 
        padding: 8px 12px; 
        border-radius: 4px; 
        margin: 2px 0; 
    } 
     
    /* Texto dentro das labels */ 
    [data-testid="stSidebar"] .stRadio label span { 
        color: white !important; 
        font-size: 16px; 
    } 
     
    /* Hover dos itens do menu */ 
    [data-testid="stSidebar"] .stRadio label:hover { 
        color: white !important; 
        background-color: #2a5f9e; 
    } 
     
    /* Item selecionado */ 
    [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) { 
        background-color: #0055a5; 
        color: white !important; 
    } 
     
    /* Foca nos itens */ 
    [data-testid="stSidebar"] .stRadio label:focus { 
        color: white !important; 
        outline: none; 
    } 
     
    /* Garantir que os ícones também fiquem brancos */ 
    [data-testid="stSidebar"] .stRadio div label span { 
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

# Carregar a imagem do logo a partir da URL 
def load_logo(url): 
    """Carrega la imagen de un URL.""" 
    try: 
        response = requests.get(url, timeout=10) 
        response.raise_for_status() 
        img = Image.open(BytesIO(response.content)) 
        return img 
    except Exception: 
        return None 

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png" 
logo_img = load_logo(logo_url) 

# Ordem padrão das colunas 
COLUNA_ORDEM_PADRAO = [ 
    "DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE", 
    "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", 
    "DATA_APROVACAO", "PREVISAO_ENTREGA", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", 
    "DIAS_ATRASO", "DIAS_EMISSAO", "DOC NF", "QUANTIDADE_ENTREGUE" 
] 

# --- Funções de Conexão e Carregamento de Dados (Versão Aprimorada) --- 
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                 'https://www.googleapis.com/auth/drive']
        
        # Pega as credenciais do secrets
        sa_info = st.secrets["gcp_service_account"]
        
        # Prepara o dicionário de credenciais
        credentials_info = {
            "type": sa_info["type"],
            "project_id": sa_info["project_id"],
            "private_key_id": sa_info["private_key_id"],
            "private_key": sa_info["private_key"].strip(),  # Remove espaços em branco extras
            "client_email": sa_info["client_email"],
            "client_id": sa_info["client_id"],
            "auth_uri": sa_info["auth_uri"],
            "token_uri": sa_info["token_uri"],
            "auth_provider_x509_cert_url": sa_info["auth_provider_x509_cert_url"],
            "client_x509_cert_url": sa_info["client_x509_cert_url"]
        }
        
        # Cria as credenciais
        creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(creds)
        
        return client

    except Exception as e: 
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        import traceback
        st.error(f"Detalhes do erro: {traceback.format_exc()}")
        return None

def parse_date_input(date_value): 
    """ 
    Converte valores de data de qualquer entrada (editor, string) para datetime, 
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
        date_value = date_value.strip() 
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y'] 
        for fmt in formats: 
            try: 
                return datetime.datetime.strptime(date_value, fmt) 
            except ValueError: 
                continue 
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
     
    valor_str = valor_str.replace('R$', '').strip() 
     
    if ',' in valor_str and '.' in valor_str: 
        valor_str = valor_str.replace('.', '').replace(',', '.') 
    elif ',' in valor_str: 
        valor_str = valor_str.replace(',', '.') 
     
    try: 
        return float(valor_str) 
    except ValueError: 
        return 0.0 

@st.cache_data(ttl=300) 
def carregar_dados_pedidos(): 
    """Carrega o DataFrame de pedidos do Google Sheets usando get_all_records.""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return criar_dataframe_pedidos_vazio() 
         
        sheet = gc.open("dados_pedido") 
        data = sheet.get_worksheet(0).get_all_records(value_render_option='UNFORMATTED_VALUE') 
         
        if not data: 
            return criar_dataframe_pedidos_vazio() 

        df = pd.DataFrame(data) 

        for col in COLUNA_ORDEM_PADRAO: 
            if col not in df.columns: 
                df[col] = '' 
         
        date_cols = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA'] 
        for col in date_cols: 
            if col in df.columns: 
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True) 
         
        # Fix pandas FutureWarning: Convert to numeric first, then fillna
        numeric_cols = ['QUANTIDADE', "VALOR_ITEM", "VALOR_RENEGOCIADO", "DIAS_ATRASO", "DIAS_EMISSAO", "QUANTIDADE_ENTREGUE"]
        for col in numeric_cols:
            if col in df.columns:
                # Convert to numeric first, then fillna to avoid FutureWarning
                df[col] = pd.to_numeric(df[col].apply(converter_para_float_brasileiro), errors='coerce').fillna(0) 
          
        df = df.reindex(columns=COLUNA_ORDEM_PADRAO, fill_value='') 

        df['STATUS_PEDIDO'] = df['DATA_ENTREGA'].apply( 
            lambda x: 'ENTREGUE' if pd.notna(x) else 'PENDENTE' 
        ) 

        return df 
    except Exception as e: 
        st.error(f"Erro ao carregar dados do Google Sheets: {e}") 
        return criar_dataframe_pedidos_vazio() 

def criar_dataframe_pedidos_vazio(): 
    """Cria um DataFrame vazio with a estrutura de pedidos.""" 
    return pd.DataFrame(columns=COLUNA_ORDEM_PADRAO) 

def salvar_dados_pedidos(df): 
    """Salva o DataFrame de pedidos no Google Sheets, garantindo formato DD/MM/YYYY para datas.""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return 
         
        sheet = gc.open("dados_pedido") 
        worksheet = sheet.get_worksheet(0) 

        df_to_save = df.copy() 
        df_to_save['VALOR_ITEM'] = df_to_save['VALOR_ITEM'].apply(
            lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) and x != '' else '0,00'
        )

        date_cols = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA'] 
        for col in date_cols: 
            if col in df_to_save.columns: 
                df_to_save[col] = df_to_save[col].apply( 
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '' 
                ) 

        # Fix pandas FutureWarning: Convert to numeric first, then fillna
        numeric_cols_to_save = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO', 'QUANTIDADE_ENTREGUE']
        for col in numeric_cols_to_save:
            if col in df_to_save.columns:
                df_to_save[col] = pd.to_numeric(df_to_save[col], errors='coerce').fillna(0)
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) and x != '' else '0,00'
                ) 
         
        if 'VALOR_TOTAL' in df_to_save.columns: 
            df_to_save.drop(columns='VALOR_TOTAL', inplace=True, errors='ignore') 

        df_to_save = df_to_save.fillna('') 
         
        df_to_save = df_to_save.reindex(columns=COLUNA_ORDEM_PADRAO, fill_value='') 

        worksheet.clear() 
        set_with_dataframe(worksheet, df_to_save, resize=True, include_column_header=True) 
         
        st.success("Dados salvos with sucesso!") 
         
    except Exception as e: 
        st.error(f"Erro ao salvar dados no Google Sheets: {e}") 

def criar_dataframe_solicitantes_vazio(): 
    """Cria um DataFrame de solicitantes vazio.""" 
    return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"]) 

@st.cache_data(show_spinner=False, ttl=300) 
def carregar_dados_solicitantes(): 
    """Carrega dados dos solicitantes do Google Sheets (quarta aba).""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            st.warning("Não foi possível conectar ao Google Sheets")
            return criar_dataframe_solicitantes_vazio()
            
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(3)  # 4ª aba (índice 3)
        data = worksheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        
        if not data:
            st.info("Planilha de solicitantes está vazia")
            return criar_dataframe_solicitantes_vazio()
            
        df = pd.DataFrame(data)
        
        # Verifica se as colunas necessárias existem
        colunas_necessarias = ["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"]
        colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
        
        if colunas_faltantes:
            st.warning(f"Colunas faltantes na planilha de solicitantes: {colunas_faltantes}")
            # Adiciona colunas faltantes
            for col in colunas_faltantes:
                df[col] = ""
                
        return df
        
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba de solicitantes não encontrada. Será criada uma nova quando necessário.")
        return criar_dataframe_solicitantes_vazio()
    except Exception as e:
        st.error(f"Erro ao carregar dados de solicitantes: {e}")
        return criar_dataframe_solicitantes_vazio()

def salvar_dados_solicitantes(df): 
    """Salva o DataFrame de solicitantes no Google Sheets.""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return 
         
        sheet = gc.open("dados_pedido") 
        worksheet = sheet.get_worksheet(3) 
        df_copy = df.copy() 
        set_with_dataframe(worksheet, df_copy, include_index=False) 
         
        st.success("Solicitante cadastrado with sucesso!") 
    except Exception as e: 
        st.error(f"Erro ao salvar dados de solicitantes no Google Sheets: {e}") 

@st.cache_data(ttl=300) 
def carregar_dados_almoxarifado(): 
    """Carrega dados do almoxarifado para preencher a nota fiscal.""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return pd.DataFrame(columns=['ORDEM_COMPRA', 'DOC NF']) 
             
        sheet = gc.open("dados_pedido") 
        worksheet = sheet.get_worksheet(1) 
        data = worksheet.get_all_records(value_render_option='UNFORMATTED_VALUE') 
        df = pd.DataFrame(data) 

        ordem_colunas = ['ORDEM_COMPRA', 'DOC NF'] 
        df = df.reindex(columns=ordem_colunas, fill_value="") 
         
        return df 
    except Exception as e: 
        st.warning(f"Aviso: Não foi possível carregar dados do Almoxarifado para preencher a nota fiscal. Verifique a aba 'Almoxarifado' da planilha. {e}") 
        return pd.DataFrame(columns=['ORDEM_COMPRA', 'DOC NF']) 

@st.cache_data(show_spinner=False, ttl=300) 
def carregar_dados_materiais(): 
    """Carrega dados dos materiais do Google Sheets (terceira aba).""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return pd.DataFrame(columns=["CODIGO", "DESCRICAO"]) 
             
        sheet = gc.open("dados_pedido") 
        worksheet = sheet.get_worksheet(2) 
        data = worksheet.get_all_records(value_render_option='UNFORMATTED_VALUE') 
        df = pd.DataFrame(data) 
        if not all(col in df.columns for col in ["CODIGO", "DESCRICAO"]): 
            st.error("A planilha de Materiais não tem as colunas esperadas: CODIGO, DESCRICAO.") 
            return pd.DataFrame(columns=["CODIGO", "DESCRICAO"]) 
        return df 
    except Exception as e: 
        st.error(f"Erro ao carregar dados de materiais: {e}") 
        return pd.DataFrame(columns=["CODIGO", "DESCRICAO"]) 

def salvar_dados_materiais(df): 
    """Salva os dados de materiais no Google Sheets (terceira aba - MATERIAIS).""" 
    try: 
        gc = get_gspread_client() 
        if gc is None: 
            return 
             
        sheet = gc.open("dados_pedido") 
        worksheet = sheet.get_worksheet(2) 
        df_copy = df.copy() 
        set_with_dataframe(worksheet, df_copy, include_index=False) 
        return True 
    except Exception as e: 
        st.error(f"Erro ao salvar dados de materiais: {e}") 
        return False 

# --- LÓGICA DE LOGIN (SEM INTEGRAÇÃO COM SMTP) --- 
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
    """Valida as credenciais do usuário""" 
    import re 
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email): 
        st.error("Formato de e-mail inválido") 
        return 
          
    if email in USERS and USERS[email]["password"] == senha: 
        st.session_state['logado'] = True 
        st.session_state['nome_colaborador'] = USERS[email]["name"] 
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.") 
        st.rerun() 
    else: 
        st.error("E-mail ou senha incorretos.") 

# --- INTERFACE PRINCIPAL --- 
def render_login_page(): 
    """Exibe a página de login.""" 
    st.markdown("<h1 style='text-align: center; color: #1C4D86;'>Login - Painel do Comprador</h1>", unsafe_allow_html=True) 
    col_left, col_center, col_right = st.columns([1, 2, 1]) 
    with col_center: 
        st.image("http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png", use_container_width=True) 
        st.write("") 
        with st.form("login_form"): 
            email = st.text_input("E-mail", placeholder="seu.email@essencis.com.br") 
            senha = st.text_input("Senha", type="password") 
            st.write("") 
            if st.form_submit_button("Entrar"): 
                fazer_login(email, senha) 

def verificar_ou_criar_abas():
    """Verifica se todas as abas necessárias existem, cria se necessário."""
    try:
        gc = get_gspread_client()
        if gc is None:
            return False
            
        sheet = gc.open("dados_pedido")
        abas_existentes = [ws.title for ws in sheet.worksheets()]
        
        abas_necessarias = ["Pedidos", "Almoxarifado", "Materiais", "Solicitantes"]
        
        for aba in abas_necessarias:
            if aba not in abas_existentes:
                sheet.add_worksheet(title=aba, rows=100, cols=20)
                st.info(f"Aba '{aba}' criada automaticamente")
                
        return True
        
    except Exception as e:
        st.error(f"Erro ao verificar/criar abas: {e}")
        return False

def render_main_app(): 
    """Exibe a interface principal da aplicação após o login.""" 
    # Verificar/criar abas necessárias primeiro
    verificar_ou_criar_abas()
    
    logo_img = load_logo(logo_url) 

    if 'df_pedidos' not in st.session_state: 
        st.session_state.df_pedidos = carregar_dados_pedidos() 
    if 'df_solicitantes' not in st.session_state: 
        st.session_state.df_solicitantes = carregar_dados_solicitantes() 
    if 'itens_requisicao_temp' not in st.session_state: 
        st.session_state.itens_requisicao_temp = pd.DataFrame(columns=["CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE"]) 
    if 'df_almoxarifado' not in st.session_state: 
        st.session_state.df_almoxarifado = carregar_dados_almoxarifado() 
    if 'df_materiais' not in st.session_state: 
        st.session_state.df_materiais = carregar_dados_materiais() 
      
    if 'solicitante_selecionado' not in st.session_state: 
        st.session_state.solicitante_selecionado = "" 
    if 'requisicao_numero' not in st.session_state: 
        st.session_state.requisicao_numero = "" 
    if 'data_requisicao' not in st.session_state: 
        st.session_state.data_requisicao = datetime.date.today() 
    if 'tipo_pedido' not in st.session_state: 
        st.session_state.tipo_pedido = "LOCAL" 
    if 'item_codigo' not in st.session_state: 
        st.session_state.item_codigo = "" 
    if 'item_material' not in st.session_state: 
        st.session_state.item_material = "" 
    if 'unidade_medida' not in st.session_state: 
        st.session_state.unidade_medida = "UN" 
    if 'item_quantidade' not in st.session_state: 
        st.session_state.item_quantidade = 1 

    with st.sidebar: 
        if logo_img: 
            st.image(logo_img, use_container_width=True) 
          
        st.write(f"Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!") 
        st.title("👨‍💼 Comprador") 
        st.divider() 
        menu = st.radio( 
            "📌 Navegação", 
            ["📝 Requisição", "✍️ Pedidos (OC)", "📜 Histórico ", "👤 Cadastro", "📊 Dashboards ", "📊 Performance "] 
        ) 
        
        # Botão de teste de conexão
        if st.button("🧪 Testar Conexão Google Sheets"):
            st.header("Teste de Conexão")
            
            gc = get_gspread_client()
            if gc:
                try:
                    # Tenta abrir a planilha pelo sheet_id
                    sheet = gc.open_by_key(st.secrets["gcp_service_account"]["sheet_id"])
                    st.success("✅ Conexão bem-sucedida com Google Sheets!")
                    
                    # Lista as abas disponíveis
                    worksheets = sheet.worksheets()
                    st.write(f"📋 Abas encontradas ({len(worksheets)}):")
                    for i, ws in enumerate(worksheets):
                        st.write(f"{i+1}. {ws.title} - {ws.row_count} linhas")
                        
                    # Verifica se as abas necessárias existem
                    abas_necessarias = ["Pedidos", "Almoxarifado", "Materiais", "Solicitantes"]
                    abas_existentes = [ws.title for ws in worksheets]
                    
                    st.write("---")
                    st.subheader("Verificação de Abas")
                    for aba in abas_necessarias:
                        if aba in abas_existentes:
                            st.success(f"✅ {aba}")
                        else:
                            st.error(f"❌ {aba} (não encontrada)")
                            
                except gspread.exceptions.SpreadsheetNotFound:
                    st.error("❌ Planilha não encontrada. Verifique o sheet_id.")
                except gspread.exceptions.APIError as e:
                    st.error(f"❌ Erro da API Google: {e}")
                except Exception as e:
                    st.error(f"❌ Erro inesperado: {e}")
            else:
                st.error("❌ Falha ao obter cliente do Google Sheets")
        
        st.divider() 
        if st.sidebar.button("Atualizar Dados"): 
            st.cache_data.clear() 
            st.session_state.df_pedidos = carregar_dados_pedidos() 
            st.session_state.df_solicitantes = carregar_dados_solicitantes() 
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado() 
            st.session_state.df_materiais = carregar_dados_materiais() 
            st.success("Dados atualizados with sucesso!") 
            st.rerun() 
        if st.sidebar.button("Logout"): 
            st.session_state['logado'] = False 
            st.session_state.pop('nome_colaborador', None) 
            st.rerun() 

    if menu == "📝 Requisição": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>📝 REGISTRAR REQUISIÇÃO DE COMPRA</h1> 
                <p>Sistema de Controle and Análise de Pedidos</p> 
            </div> 
        """, unsafe_allow_html=True) 
          
        st.header("📝 Registrar Nova Requisição de Compra") 
          
        if st.session_state.df_solicitantes is not None and not st.session_state.df_solicitantes.empty: 
            solicitantes_nomes = [""] + st.session_state.df_solicitantes['NOME'].unique().tolist() 
            with st.container(): 
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1]) 
                with col1: 
                    solicitante_selecionado = st.selectbox( 
                        "Solicitante",  
                        solicitantes_nomes, 
                        key="select_solicitante", 
                        index=solicitantes_nomes.index(st.session_state.solicitante_selecionado) if st.session_state.solicitante_selecionado in solicitantes_nomes else 0 
                    ) 
                if solicitante_selecionado: 
                    solicitante_info = st.session_state.df_solicitantes[st.session_state.df_solicitantes['NOME'] == solicitante_selecionado].iloc[0] 
                    departamento_selecionado = solicitante_info['DEPARTAMENTO'] 
                    filial_selecionada = solicitante_info['FILIAL'] 
                else: 
                    departamento_selecionado = "" 
                    filial_selecionada = "" 
                with col2: 
                    st.text_input("Departamento", value=departamento_selecionado, disabled=True) 
                with col3: 
                    st.text_input("Filial", value=filial_selecionada, disabled=True) 
                with col4: 
                    requisicao = st.text_input("N° Requisição", key="input_requisicao", value=st.session_state.requisicao_numero) 
        else: 
            st.warning("Nenhum solicitante encontrado. Por favor, cadastre um na aba 'Cadastro'.") 
            solicitante_selecionado = "" 
            departamento_selecionado = "" 
            filial_selecionada = "" 
            requisicao = st.text_input("N° Requisição", key="input_requisicao_disabled", disabled=True) 

        col5, col6 = st.columns(2) 
        with col5: 
            data_requisicao = st.date_input("Data da Requisição", st.session_state.data_requisicao, key="input_data") 
        with col6: 
            tipo_pedido = st.selectbox( 
                "Tipo de Pedido",  
                ["LOCAL", "EMERGENCIAL", "PROGRAMADO"], 
                key="select_tipo_pedido", 
                index=["LOCAL", "EMERGENCIAL", "PROGRAMADO"].index(st.session_state.tipo_pedido) 
            ) 
          
        st.markdown("---") 
        st.subheader("Itens da Requisição") 
          
        if not st.session_state.itens_requisicao_temp.empty: 
            st.session_state.itens_requisicao_temp = st.data_editor( 
                st.session_state.itens_requisicao_temp, 
                use_container_width=True, 
                num_rows='dynamic', 
                column_config={ 
                    "CODIGO_MATERIAL": "Código Material", 
                    "MATERIAL": "Descrição Material", 
                    "UN": "Unidade de Medida", 
                    "QUANTIDADE": st.column_config.NumberColumn("Quantidade", min_value=1) 
                }, 
                key="editor_itens" 
            ) 

        col_item1, col_item2, col_item3, col_item4 = st.columns([1, 2, 1, 1]) 
          
        if st.session_state.df_materiais is not None and not st.session_state.df_materiais.empty: 
            with col_item1: 
                item_codigo = st.text_input("Código do Material", key="input_codigo_material", value=st.session_state.item_codigo) 

            with col_item2: 
                descricao_material = "" 
                if item_codigo: 
                    material_info = st.session_state.df_materiais[st.session_state.df_materiais['CODIGO'] == item_codigo] 
                    if not material_info.empty: 
                        descricao_material = material_info.iloc[0]['DESCRICAO'] 
                  
                item_material = st.text_input("Descrição do Material", value=descricao_material, disabled=True, key="display_material") 
              
            with col_item3: 
                unidade_medida = st.selectbox( 
                    "Unidade de Medida", 
                    [ 
                        "UN", "TB", "PÇ", "KIT", "CX", "FR", "GL", "KG", "G", "MG",  
                        "L", "ML", "M", "CM", "MM", "M2", "M3", "PCT", "RL", "BD",  
                        "AMP", "SC", "T", "DZ", "CJ", "JG", "PAR", "CXA", "FAR",  
                        "BL", "CR", "PL", "TON", "LT", "S", "CAP", 
                    ], 
                    key="select_unidade_medida", 
                ) 

            with col_item4: 
                item_quantidade = st.number_input("Quantidade", min_value=1, value=1, key="input_quantidade") 
                  
                if st.button("➕ Adicionar Item", key="btn_adicionar_item"): 
                    if item_codigo and item_material and item_quantidade > 0: 
                        novo_item = pd.DataFrame([{ 
                            "CODIGO_MATERIAL": item_codigo,  
                            "MATERIAL": item_material,  
                            "UN": unidade_medida,  
                            "QUANTIDADE": item_quantidade 
                        }]) 
                        st.session_state.itens_requisicao_temp = pd.concat([st.session_state.itens_requisicao_temp, novo_item], ignore_index=True) 
                        st.success("Item adicionado! Você pode editar ou excluir na tabela acima.") 
                          
                        st.session_state.item_codigo = "" 
                        st.session_state.item_material = "" 
                        st.session_state.unidade_medida = "UN" 
                        st.session_state.item_quantidade = 1 
                        st.rerun() 
                    else: 
                        st.error("Por favor, preencha todos os campos obrigatórios (Código, Descrição, Unidade e Quantidade).") 
        else: 
            st.warning("Nenhum material encontrado. Por favor, cadastre um na aba 'Cadastro'.") 
            st.text_input("Código do Material", disabled=True, value="") 
            st.text_input("Descrição do Material", disabled=True, value="") 
            st.selectbox("Unidade de Medida", ["UN"], disabled=True) 
            st.number_input("Quantidade", min_value=1, value=1, disabled=True) 
            st.button("➕ Adicionar Item", key="btn_adicionar_item", disabled=True) 

          
        st.write("---") 
          
        if st.button("Finalizar e Registrar Requisição", key="btn_finalizar_requisicao"): 
            if requisicao and not st.session_state.itens_requisicao_temp.empty: 
                linhas_a_adicionar = [] 
                for _, item_row in st.session_state.itens_requisicao_temp.iterrows(): 
                    nova_linha = { 
                        "DATA": data_requisicao, 
                        "SOLICITANTE": solicitante_selecionado, 
                        "DEPARTAMENTO": departamento_selecionado, 
                        "FILIAL": filial_selecionada, 
                        "CODIGO_MATERIAL": item_row["CODIGO_MATERIAL"], 
                        "MATERIAL": item_row["MATERIAL"], 
                        "UN": item_row["UN"], 
                        "QUANTIDADE": item_row["QUANTIDADE"], 
                        "TIPO_PEDIDO": tipo_pedido, 
                        "REQUISICAO": requisicao, 
                        "FORNECEDOR": "", 
                        "ORDEM_COMPRA": "", 
                        "VALOR_ITEM": 0.0, 
                        "VALOR_RENEGOCIADO": 0.0, 
                        "DATA_APROVACAO": pd.NaT, 
                        "PREVISAO_ENTREGA": pd.NaT, 
                        "CONDICAO_FRETE": "", 
                        "STATUS_PEDIDO": "PENDENTE", 
                        "DATA_ENTREGA": pd.NaT, 
                        "DIAS_ATRASO": 0, 
                        "DIAS_EMISSAO": 0, 
                        "DOC NF": "", 
                        "QUANTIDADE_ENTREGUE": 0 # Adicionado 
                    } 
                    linhas_a_adicionar.append(nova_linha) 
                  
                df_a_adicionar = pd.DataFrame(linhas_a_adicionar) 
                  
                st.session_state.df_pedidos = pd.concat([st.session_state.df_pedidos, df_a_adicionar], ignore_index=True) 
                  
                salvar_dados_pedidos(st.session_state.df_pedidos) 
                  
                st.session_state.itens_requisicao_temp = pd.DataFrame(columns=["CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE"]) 
                st.session_state.solicitante_selecionado = "" 
                st.session_state.requisicao_numero = "" 
                st.session_state.data_requisicao = datetime.date.today() 
                st.session_state.tipo_pedido = "LOCAL" 
                st.session_state.item_codigo = "" 
                st.session_state.item_material = "" 
                st.session_state.unidade_medida = "UN" 
                st.session_state.item_quantidade = 1 
                  
                st.success("Requisição registrada com sucesso! Vá para 'Atualizar Pedidos' para completar as informações.") 
                st.balloons() 
                st.rerun() 
            else: 
                st.error("O campo 'Número da Requisição' e pelo menos um item são obrigatórios.") 

    elif menu == "✍️ Pedidos (OC)": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>✍️ PEDIDOS PENDENTES</h1> 
                <p>Gerencie Requisições Pendentes com Seleção em Lote</p> 
            </div> 
        """, unsafe_allow_html=True) 
      
        st.header("✍️ Pedidos Pendentes - Seleção e Atualização em Lote") 
        st.info("Selecione um solicitante à esquerda, marque itens desejados e aplique dados em lote.") 
        
        # Calculate date threshold for highlighting (3 days ago)
        date_threshold = datetime.date.today() - datetime.timedelta(days=3)
          
        # Get pending orders (without purchase order)
        pedidos_pendentes_oc = st.session_state.df_pedidos[ 
            ((st.session_state.df_pedidos['ORDEM_COMPRA'].isnull()) |  
            (st.session_state.df_pedidos['ORDEM_COMPRA'] == "")) &
            (st.session_state.df_pedidos['STATUS_PEDIDO'] == "PENDENTE")
        ].copy() 
          
        if pedidos_pendentes_oc.empty: 
            st.success("🎉 Todas as requisições pendentes já foram atualizadas!") 
            st.stop()
        
        # Process dates for highlighting calculation
        for col in ['DATA']:
            if col in pedidos_pendentes_oc.columns:
                pedidos_pendentes_oc[col] = pedidos_pendentes_oc[col].apply(parse_date_input)
        
        # Two-column layout: Requesters on left, Items on right
        col_requesters, col_items = st.columns([1, 3])
        
        with col_requesters:
            st.subheader("Solicitantes")
            
            # Get unique requesters and check if they have overdue items
            solicitantes_info = []
            for solicitante in pedidos_pendentes_oc['SOLICITANTE'].unique():
                solicitante_items = pedidos_pendentes_oc[pedidos_pendentes_oc['SOLICITANTE'] == solicitante]
                
                # Check if any item is overdue (>3 days)
                overdue = False
                for _, item in solicitante_items.iterrows():
                    if pd.notna(item['DATA']):
                        item_date = item['DATA'].date() if hasattr(item['DATA'], 'date') else item['DATA']
                        if item_date < date_threshold:
                            overdue = True
                            break
                
                solicitantes_info.append({
                    'nome': solicitante,
                    'overdue': overdue,
                    'count': len(solicitante_items)
                })
            
            # Display requesters with red highlighting for overdue
            selected_solicitante = st.session_state.get('selected_solicitante_pedidos', None)
            
            for info in solicitantes_info:
                # Create color styling based on overdue status
                color = "🔴" if info['overdue'] else "⚪"
                label = f"{color} {info['nome']} ({info['count']} itens)"
                
                if st.button(label, key=f"btn_sol_{info['nome']}", use_container_width=True):
                    st.session_state.selected_solicitante_pedidos = info['nome']
                    st.rerun()
        
        with col_items:
            st.subheader("Itens Pendentes")
            
            if selected_solicitante:
                # Filter items for selected requester
                items_solicitante = pedidos_pendentes_oc[
                    pedidos_pendentes_oc['SOLICITANTE'] == selected_solicitante
                ].copy()
                
                if not items_solicitante.empty:
                    # Add selection column
                    if 'Selecionar' not in items_solicitante.columns:
                        items_solicitante.insert(0, 'Selecionar', False)
                    
                    # Process dates and check for overdue items
                    items_display = items_solicitante.copy()
                    for col in ['DATA', 'DATA_APROVACAO', 'PREVISAO_ENTREGA']:
                        if col in items_display.columns:
                            items_display[col] = items_display[col].apply(parse_date_input)
                            items_display[col] = items_display[col].apply(
                                lambda x: x.date() if pd.notna(x) and hasattr(x, 'date') else x
                            )
                    
                    # Convert numeric columns
                    numeric_cols = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO']
                    for col in numeric_cols:
                        if col in items_display.columns:
                            items_display[col] = pd.to_numeric(items_display[col], errors='coerce').fillna(0)
                    
                    # Create styled data editor
                    cols_to_show = ['Selecionar', 'DATA', 'REQUISICAO', 'CODIGO_MATERIAL', 'MATERIAL', 
                                   'QUANTIDADE', 'FORNECEDOR', 'ORDEM_COMPRA', 'VALOR_ITEM', 
                                   'VALOR_RENEGOCIADO', 'DATA_APROVACAO', 'PREVISAO_ENTREGA']
                    cols_available = [col for col in cols_to_show if col in items_display.columns]
                    
                    # Use data_editor for item selection and editing
                    edited_items = st.data_editor(
                        items_display[cols_available],
                        use_container_width=True,
                        hide_index=True,
                        key=f"items_editor_{selected_solicitante}",
                        column_config={
                            "Selecionar": st.column_config.CheckboxColumn("✓", default=False),
                            "DATA": st.column_config.DateColumn("Data Req.", format="DD/MM/YYYY"),
                            "REQUISICAO": "N° Req.",
                            "CODIGO_MATERIAL": "Cód. Material",
                            "MATERIAL": "Material",
                            "QUANTIDADE": st.column_config.NumberColumn("Qtd.", format="%d"),
                            "FORNECEDOR": "Fornecedor",
                            "ORDEM_COMPRA": "OC",
                            "VALOR_ITEM": st.column_config.NumberColumn("Valor Unit.", format="R$ %.2f"),
                            "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Reneg.", format="R$ %.2f"),
                            "DATA_APROVACAO": st.column_config.DateColumn("Data Aprov.", format="DD/MM/YYYY"),
                            "PREVISAO_ENTREGA": st.column_config.DateColumn("Prev. Entrega", format="DD/MM/YYYY")
                        }
                    )
                    
                    # Action buttons for bulk operations
                    st.markdown("---")
                    col_actions1, col_actions2, col_actions3 = st.columns(3)
                    
                    with col_actions1:
                        if st.button("Selecionar Todos", use_container_width=True):
                            edited_items['Selecionar'] = True
                            st.rerun()
                    
                    with col_actions2:
                        if st.button("Limpar Seleção", use_container_width=True):
                            edited_items['Selecionar'] = False
                            st.rerun()
                    
                    with col_actions3:
                        selected_count = edited_items['Selecionar'].sum() if 'Selecionar' in edited_items.columns else 0
                        st.info(f"{selected_count} itens selecionados")
                    
                    # Form for bulk data application
                    if selected_count > 0:
                        with st.expander("🔄 Aplicar Dados aos Itens Selecionados", expanded=True):
                            st.info(f"Os dados abaixo serão aplicados aos {selected_count} itens selecionados. Valores unitários não serão alterados.")
                            
                            with st.form("bulk_update_form"):
                                col_form1, col_form2 = st.columns(2)
                                
                                with col_form1:
                                    bulk_fornecedor = st.text_input("Fornecedor", key="bulk_fornecedor")
                                    bulk_oc = st.text_input("Ordem de Compra", key="bulk_oc")
                                    bulk_status = st.selectbox("Status do Pedido", 
                                                             options=["", "PENDENTE", "EM ANDAMENTO", "APROVADO"],
                                                             key="bulk_status")
                                
                                with col_form2:
                                    # Fix date defaults - use current date instead of 01/01/2000
                                    today = datetime.date.today()
                                    bulk_data_aprovacao = st.date_input("Data de Aprovação", 
                                                                       value=today, key="bulk_data_aprovacao")
                                    bulk_previsao_entrega = st.date_input("Previsão de Entrega", 
                                                                         value=today, key="bulk_previsao_entrega")
                                
                                if st.form_submit_button("Aplicar Dados aos Itens Selecionados", type="primary"):
                                    # Apply bulk updates to selected items
                                    selected_indices = edited_items[edited_items['Selecionar'] == True].index
                                    updates_made = 0
                                    
                                    for idx in selected_indices:
                                        original_idx = items_solicitante.iloc[idx].name
                                        
                                        # Apply updates (but not to value fields)
                                        if bulk_fornecedor:
                                            st.session_state.df_pedidos.loc[original_idx, 'FORNECEDOR'] = bulk_fornecedor
                                            updates_made += 1
                                        if bulk_oc:
                                            st.session_state.df_pedidos.loc[original_idx, 'ORDEM_COMPRA'] = bulk_oc
                                            updates_made += 1
                                        if bulk_status:
                                            st.session_state.df_pedidos.loc[original_idx, 'STATUS_PEDIDO'] = bulk_status
                                            updates_made += 1
                                        if bulk_data_aprovacao:
                                            st.session_state.df_pedidos.loc[original_idx, 'DATA_APROVACAO'] = bulk_data_aprovacao
                                            updates_made += 1
                                        if bulk_previsao_entrega:
                                            st.session_state.df_pedidos.loc[original_idx, 'PREVISAO_ENTREGA'] = bulk_previsao_entrega
                                            updates_made += 1
                                    
                                    if updates_made > 0:
                                        # Save changes
                                        salvar_dados_pedidos(st.session_state.df_pedidos)
                                        st.success(f"✅ Dados aplicados com sucesso a {len(selected_indices)} itens!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.warning("Nenhum dado foi preenchido para aplicação.")
                
                else:
                    st.info("Nenhum item pendente encontrado para este solicitante.")
            else:
                st.info("Selecione um solicitante à esquerda para visualizar os itens pendentes.")

    elif menu == "📜 Histórico ": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>📜 HISTÓRICO E EDIÇÃO DE PEDIDOS</h1> 
                <p>Gerencie e Edite os Registros Anteriores</p> 
            </div> 
        """, unsafe_allow_html=True) 
          
        st.header("📜 Histórico Completo - Filtros e Anexos Funcionais") 
        st.info("Visualize, filtre e baixe anexos de NF dos pedidos registrados.") 

        df_history = st.session_state.df_pedidos.copy() 
          
        # Process dates
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']: 
            df_history[col] = df_history[col].apply(parse_date_input) 
          
        # Fix pandas FutureWarning: Convert to numeric first, then fillna
        for col in ['QUANTIDADE', 'VALOR_ITEM', 'QUANTIDADE_ENTREGUE']:
            df_history[col] = pd.to_numeric(df_history[col], errors='coerce').fillna(0) 

        df_history['VALOR_TOTAL'] = df_history['QUANTIDADE'] * df_history['VALOR_ITEM'] 
        df_history['VALOR_TOTAL'] = df_history['VALOR_TOTAL'].round(2) 
          
        # Enhanced filtering interface
        st.subheader("🔍 Filtros")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            # Date range filter using delivery dates
            today = datetime.date.today()
            data_inicio_hist = st.date_input("Data Início (Entrega)", 
                                           value=today - datetime.timedelta(days=30),
                                           key="hist_data_inicio")
            data_fim_hist = st.date_input("Data Fim (Entrega)", 
                                        value=today,
                                        key="hist_data_fim")
        
        with col_f2:
            # Status filter
            status_options = ['Todos'] + sorted([s for s in df_history['STATUS_PEDIDO'].unique() if pd.notna(s)])
            status_selecionado_h = st.selectbox("Status", status_options, key="hist_status")
        
        with col_f3:
            # Solicitante filter
            solicitantes_disponiveis = ['Todos'] + sorted([s for s in df_history['SOLICITANTE'].unique() if pd.notna(s)])
            solicitante_selecionado_h = st.selectbox("Solicitante", solicitantes_disponiveis, key="hist_solicitante")
        
        with col_f4:
            # Text search filter
            texto_busca = st.text_input("Busca Geral (Material, Req, OC)", key="hist_busca")
        
        # Apply filters
        df_filtered = df_history.copy()
        
        # Filter by delivery date range (only if column has datetime data)
        if 'PREVISAO_ENTREGA' in df_filtered.columns:
            # Only apply date filter if the column has datetime values
            date_mask = df_filtered['PREVISAO_ENTREGA'].isna()
            if df_filtered['PREVISAO_ENTREGA'].dtype.name.startswith('datetime'):
                date_mask = date_mask | (
                    (df_filtered['PREVISAO_ENTREGA'].dt.date >= data_inicio_hist) & 
                    (df_filtered['PREVISAO_ENTREGA'].dt.date <= data_fim_hist)
                )
            df_filtered = df_filtered[date_mask]
        
        # Filter by status
        if status_selecionado_h != 'Todos':
            df_filtered = df_filtered[df_filtered['STATUS_PEDIDO'] == status_selecionado_h]
        
        # Filter by solicitante
        if solicitante_selecionado_h != 'Todos':
            df_filtered = df_filtered[df_filtered['SOLICITANTE'] == solicitante_selecionado_h]
        
        # Text search filter - using .astype(str).str.contains to avoid Series errors
        if texto_busca:
            mask = (
                df_filtered['MATERIAL'].astype(str).str.contains(texto_busca, case=False, na=False) |
                df_filtered['REQUISICAO'].astype(str).str.contains(texto_busca, case=False, na=False) |
                df_filtered['ORDEM_COMPRA'].astype(str).str.contains(texto_busca, case=False, na=False)
            )
            df_filtered = df_filtered[mask]
        
        # Display results
        if df_filtered.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            return
        
        st.subheader(f"📋 Resultados: {len(df_filtered)} registros encontrados")
        
        # Enhanced attachment handling function
        def format_nf_column(doc_nf):
            """Format the NF document column with download capability"""
            if pd.isna(doc_nf) or doc_nf == '' or doc_nf == 'nan':
                return "—"  # Em dash for empty values
            
            # Check if it's a URL, file path, or base64 data
            doc_str = str(doc_nf)
            if any(doc_str.startswith(prefix) for prefix in ['http://', 'https://', 'file://', 'data:']):
                return f"[📥 Baixar NF]({doc_str})"
            else:
                return f"📄 {doc_str}"
        
        # Prepare display dataframe
        df_display = df_filtered.copy()
        
        # Format status for display
        def formatar_status_display(status):
            if status == 'ENTREGUE':
                return '🟢 ENTREGUE'
            elif status == 'PENDENTE':
                return '🟡 PENDENTE'
            else:
                return str(status) if pd.notna(status) else ''
        
        df_display['STATUS_PEDIDO'] = df_display['STATUS_PEDIDO'].apply(formatar_status_display)
        
        # Format monetary values
        for col in ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'VALOR_TOTAL']:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: f"R$ {float(x):.2f}".replace('.', ',') if pd.notna(x) and x != '' else ''
                )
        
        # Format attachment column
        if 'DOC NF' in df_display.columns:
            df_display['Anexo NF'] = df_display['DOC NF'].apply(format_nf_column)
        else:
            df_display['Anexo NF'] = "—"
        
        # Select columns for display
        display_cols = [
            'DATA', 'REQUISICAO', 'SOLICITANTE', 'MATERIAL', 'QUANTIDADE', 
            'VALOR_TOTAL', 'STATUS_PEDIDO', 'ORDEM_COMPRA', 'FORNECEDOR', 
            'PREVISAO_ENTREGA', 'Anexo NF'
        ]
        available_cols = [col for col in display_cols if col in df_display.columns]
        
        # Display the data with attachment functionality
        st.dataframe(
            df_display[available_cols],
            use_container_width=True,
            column_config={
                "DATA": st.column_config.DateColumn("Data Req.", format="DD/MM/YYYY"),
                "REQUISICAO": "N° Req.",
                "SOLICITANTE": "Solicitante",
                "MATERIAL": "Material",
                "QUANTIDADE": st.column_config.NumberColumn("Qtd.", format="%d"),
                "VALOR_TOTAL": "Valor Total",
                "STATUS_PEDIDO": "Status",
                "ORDEM_COMPRA": "OC",
                "FORNECEDOR": "Fornecedor",
                "PREVISAO_ENTREGA": st.column_config.DateColumn("Prev. Entrega", format="DD/MM/YYYY"),
                "Anexo NF": st.column_config.LinkColumn("Anexo NF", display_text="📥 Download")
            }
        )
        
        # Summary metrics
        st.markdown("---")
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        
        with col_sum1:
            total_value = df_filtered['VALOR_TOTAL'].sum()
            st.metric("💰 Valor Total", f"R$ {total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        with col_sum2:
            delivered_count = len(df_filtered[df_filtered['STATUS_PEDIDO'].str.contains('ENTREGUE', na=False)])
            st.metric("✅ Entregues", f"{delivered_count} de {len(df_filtered)}")
        
        with col_sum3:
            pending_count = len(df_filtered[df_filtered['STATUS_PEDIDO'].str.contains('PENDENTE', na=False)])
            st.metric("⏳ Pendentes", f"{pending_count} de {len(df_filtered)}")
        
        # Export functionality
        if st.button("📥 Exportar Resultados (CSV)", use_container_width=True):
            csv_data = df_filtered[available_cols].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="Baixar CSV",
                data=csv_data,
                file_name=f"historico_pedidos_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    elif menu == "👤 Cadastro": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>👤 CADASTRO DE SOLICITANTES E MATERIAIS</h1> 
                <p>Gerencie os Cadastros do Sistema</p> 
            </div> 
        """, unsafe_allow_html=True) 
          
        tab1, tab2, tab3 = st.tabs(["👤 Cadastro de Solicitantes", "📦 Cadastro de Materiais", "🏢 Cadastro de Fornecedores"]) 
          
        with tab1: 
            st.header("👤 Cadastro de Solicitantes") 
            
            # Individual registration
            with st.form("form_cadastro_solicitante"): 
                col1, col2 = st.columns(2) 
                with col1: 
                    nome_solicitante = st.text_input("Nome Completo") 
                    email_solicitante = st.text_input("E-mail") 
                with col2: 
                    departamento_solicitante = st.text_input("Departamento") 
                    filial_solicitante = st.text_input("Filial") 
                  
                if st.form_submit_button("Cadastrar Solicitante"): 
                    if nome_solicitante and departamento_solicitante and email_solicitante and filial_solicitante: 
                        novo_solicitante = pd.DataFrame([{ 
                            "NOME": nome_solicitante, 
                            "DEPARTAMENTO": departamento_solicitante, 
                            "EMAIL": email_solicitante, 
                            "FILIAL": filial_solicitante 
                        }]) 
                          
                        st.session_state.df_solicitantes = pd.concat([st.session_state.df_solicitantes, novo_solicitante], ignore_index=True) 
                        if salvar_dados_solicitantes(st.session_state.df_solicitantes):
                            st.success("✅ Solicitante cadastrado com sucesso!") 
                            st.rerun() 
                        else:
                            st.error("❌ Erro ao salvar solicitante.")
                    else: 
                        st.error("Por favor, preencha todos os campos.") 
            
            # Bulk upload for solicitantes
            st.markdown("---")
            st.subheader("📤 Upload em Massa")
            st.info("Faça upload de um arquivo CSV com colunas: NOME, DEPARTAMENTO, EMAIL, FILIAL")
            
            uploaded_file = st.file_uploader("Escolha um arquivo CSV", type=['csv'], key="upload_solicitantes")
            
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_csv(uploaded_file)
                    
                    # Validate required columns
                    required_cols = ['NOME', 'DEPARTAMENTO', 'EMAIL', 'FILIAL']
                    if all(col in df_upload.columns for col in required_cols):
                        st.dataframe(df_upload, use_container_width=True)
                        
                        if st.button("Confirmar Upload de Solicitantes"):
                            st.session_state.df_solicitantes = pd.concat([st.session_state.df_solicitantes, df_upload], ignore_index=True)
                            if salvar_dados_solicitantes(st.session_state.df_solicitantes):
                                st.success(f"✅ {len(df_upload)} solicitantes importados com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar dados.")
                    else:
                        st.error(f"❌ Arquivo deve conter as colunas: {', '.join(required_cols)}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo: {e}")
              
            st.subheader("Solicitantes Cadastrados") 
            if not st.session_state.df_solicitantes.empty: 
                st.dataframe(st.session_state.df_solicitantes, use_container_width=True) 
            else: 
                st.info("Nenhum solicitante cadastrado ainda.")
          
        with tab2: 
            st.header("📦 Cadastro de Materiais") 
            
            # Individual registration
            with st.form("form_cadastro_material"): 
                col1, col2 = st.columns(2) 
                with col1: 
                    codigo_material = st.text_input("Código do Material") 
                with col2: 
                    descricao_material = st.text_input("Descrição do Material") 
                  
                if st.form_submit_button("Cadastrar Material"): 
                    if codigo_material and descricao_material: 
                        novo_material = pd.DataFrame([{ 
                            "CODIGO": codigo_material, 
                            "DESCRICAO": descricao_material 
                        }]) 
                          
                        st.session_state.df_materiais = pd.concat([st.session_state.df_materiais, novo_material], ignore_index=True) 
                        if salvar_dados_materiais(st.session_state.df_materiais):
                            st.success("✅ Material cadastrado com sucesso!") 
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar material.")
                    else: 
                        st.error("Por favor, preencha todos os campos.") 
            
            # Bulk upload for materials
            st.markdown("---")
            st.subheader("📤 Upload em Massa")
            st.info("Faça upload de um arquivo CSV com colunas: CODIGO, DESCRICAO")
            
            uploaded_materials = st.file_uploader("Escolha um arquivo CSV", type=['csv'], key="upload_materials")
            
            if uploaded_materials is not None:
                try:
                    df_materials_upload = pd.read_csv(uploaded_materials)
                    
                    # Validate required columns
                    required_cols_mat = ['CODIGO', 'DESCRICAO']
                    if all(col in df_materials_upload.columns for col in required_cols_mat):
                        st.dataframe(df_materials_upload, use_container_width=True)
                        
                        if st.button("Confirmar Upload de Materiais"):
                            st.session_state.df_materiais = pd.concat([st.session_state.df_materiais, df_materials_upload], ignore_index=True)
                            if salvar_dados_materiais(st.session_state.df_materiais):
                                st.success(f"✅ {len(df_materials_upload)} materiais importados com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar dados.")
                    else:
                        st.error(f"❌ Arquivo deve conter as colunas: {', '.join(required_cols_mat)}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo: {e}")
            
            st.subheader("Materiais Cadastrados") 
            if not st.session_state.df_materiais.empty: 
                st.dataframe(st.session_state.df_materiais, use_container_width=True) 
            else: 
                st.info("Nenhum material cadastrado ainda.")
        
        with tab3:
            st.header("🏢 Cadastro de Fornecedores")
            
            # Individual registration
            with st.form("form_cadastro_fornecedor"):
                col1, col2 = st.columns(2)
                with col1:
                    nome_fornecedor = st.text_input("Nome/Razão Social do Fornecedor")
                    cnpj_fornecedor = st.text_input("CNPJ")
                with col2:
                    email_fornecedor = st.text_input("E-mail")
                    telefone_fornecedor = st.text_input("Telefone")
                
                if st.form_submit_button("Cadastrar Fornecedor"):
                    if nome_fornecedor and cnpj_fornecedor:
                        # Initialize fornecedores dataframe if it doesn't exist
                        if 'df_fornecedores' not in st.session_state:
                            st.session_state.df_fornecedores = pd.DataFrame(columns=["NOME", "CNPJ", "EMAIL", "TELEFONE"])
                        
                        novo_fornecedor = pd.DataFrame([{
                            "NOME": nome_fornecedor,
                            "CNPJ": cnpj_fornecedor,
                            "EMAIL": email_fornecedor,
                            "TELEFONE": telefone_fornecedor
                        }])
                        
                        st.session_state.df_fornecedores = pd.concat([st.session_state.df_fornecedores, novo_fornecedor], ignore_index=True)
                        # Note: You may want to implement salvar_dados_fornecedores function
                        st.success("✅ Fornecedor cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Por favor, preencha pelo menos o nome e CNPJ.")
            
            # Bulk upload for suppliers
            st.markdown("---")
            st.subheader("📤 Upload em Massa")
            st.info("Faça upload de um arquivo CSV com colunas: NOME, CNPJ, EMAIL, TELEFONE")
            
            uploaded_suppliers = st.file_uploader("Escolha um arquivo CSV", type=['csv'], key="upload_suppliers")
            
            if uploaded_suppliers is not None:
                try:
                    df_suppliers_upload = pd.read_csv(uploaded_suppliers)
                    
                    # Validate required columns
                    required_cols_sup = ['NOME', 'CNPJ']
                    if all(col in df_suppliers_upload.columns for col in required_cols_sup):
                        st.dataframe(df_suppliers_upload, use_container_width=True)
                        
                        if st.button("Confirmar Upload de Fornecedores"):
                            if 'df_fornecedores' not in st.session_state:
                                st.session_state.df_fornecedores = pd.DataFrame(columns=["NOME", "CNPJ", "EMAIL", "TELEFONE"])
                            
                            st.session_state.df_fornecedores = pd.concat([st.session_state.df_fornecedores, df_suppliers_upload], ignore_index=True)
                            st.success(f"✅ {len(df_suppliers_upload)} fornecedores importados com sucesso!")
                            st.rerun()
                    else:
                        st.error(f"❌ Arquivo deve conter pelo menos as colunas: {', '.join(required_cols_sup)}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo: {e}")
            
            st.subheader("Fornecedores Cadastrados")
            if 'df_fornecedores' in st.session_state and not st.session_state.df_fornecedores.empty:
                st.dataframe(st.session_state.df_fornecedores, use_container_width=True)
            else:
                st.info("Nenhum fornecedor cadastrado ainda.")

    elif menu == "📊 Dashboards ": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>📊 DASHBOARDS E INDICADORES</h1> 
                <p>Análise de Desempenho do Departamento de Compras</p> 
            </div> 
        """, unsafe_allow_html=True) 
          
        st.header("📊 Dashboards e Indicadores de Compras") 
          
        df_dash = st.session_state.df_pedidos.copy() 
          
        df_dash['DATA'] = pd.to_datetime(df_dash['DATA'], errors='coerce') 
        # Fix pandas FutureWarning: Convert to numeric first, then fillna
        df_dash['VALOR_ITEM'] = pd.to_numeric(df_dash['VALOR_ITEM'], errors='coerce').fillna(0)
        df_dash['QUANTIDADE'] = pd.to_numeric(df_dash['QUANTIDADE'], errors='coerce').fillna(0)
        df_dash['VALOR_TOTAL'] = df_dash['VALOR_ITEM'] * df_dash['QUANTIDADE'] 
          
        st.subheader("Filtros") 
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3) 
          
        with col_filtro1: 
            if not df_dash.empty and 'DATA' in df_dash.columns and not df_dash['DATA'].isna().all(): 
                datas_validas = df_dash[df_dash['DATA'].notna()] 
                if not datas_validas.empty: 
                    min_date = datas_validas['DATA'].min().date() 
                    max_date = datas_validas['DATA'].max().date() 
                    data_inicio = st.date_input("Data Início", min_date, min_value=min_date, max_value=max_date) 
                    data_fim = st.date_input("Data Fim", max_date, min_value=min_date, max_value=max_date) 
                else: 
                    st.info("Nenhuma data válida para filtrar") 
                    data_inicio = datetime.date.today() 
                    data_fim = datetime.date.today() 
            else: 
                st.info("Nenhuma data disponível para filtrar") 
                data_inicio = datetime.date.today() 
                data_fim = datetime.date.today() 
          
        with col_filtro2: 
            departamentos = ['Todos'] + df_dash['DEPARTAMENTO'].unique().tolist() if 'DEPARTAMENTO' in df_dash.columns else ['Todos'] 
            departamento_selecionado = st.selectbox("Departamento", departamentos) 
          
        with col_filtro3: 
            status_options = ['Todos'] + df_dash['STATUS_PEDIDO'].unique().tolist() if 'STATUS_PEDIDO' in df_dash.columns else ['Todos'] 
            status_selecionado = st.selectbox("Status", status_options) 
          
        if not df_dash.empty and 'DATA' in df_dash.columns: 
            df_dash = df_dash[(df_dash['DATA'].dt.date >= data_inicio) & (df_dash['DATA'].dt.date <= data_fim)] 
          
        if departamento_selecionado != 'Todos': 
            df_dash = df_dash[df_dash['DEPARTAMENTO'] == departamento_selecionado] 
          
        if status_selecionado != 'Todos': 
            df_dash = df_dash[df_dash['STATUS_Pedido'] == status_selecionado] 
          
        if df_dash.empty: 
            st.warning("Nenhum dado disponível para os filtros selecionados.") 
            st.stop() 
          
        st.subheader("Métricas Principais") 
        col1, col2, col3, col4 = st.columns(4) 
          
        with col1: 
            total_pedidos = len(df_dash) 
            st.metric("Total de Pedidos", total_pedidos) 
          
        with col2: 
            total_valor = df_dash['VALOR_TOTAL'].sum() 
            st.metric("Valor Total (R$)", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) 
          
        with col3: 
            pedidos_entregues = len(df_dash[df_dash['STATUS_PEDIDO'] == 'ENTREGUE']) if 'STATUS_PEDIDO' in df_dash.columns else 0 
            taxa_entrega = (pedidos_entregues / total_pedidos * 100) if total_pedidos > 0 else 0 
            st.metric("Taxa de Entrega", f"{taxa_entrega:.1f}%") 
          
        with col4: 
            valor_medio = total_valor / total_pedidos if total_pedidos > 0 else 0 
            st.metric("Valor Médio por Pedido", f"R$ {valor_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) 
          
        st.markdown("---") 
          
        st.subheader("Custo por Departamento") 
        if 'DEPARTAMENTO' in df_dash.columns: 
            custo_por_departamento = df_dash.groupby('DEPARTAMENTO')['VALOR_TOTAL'].sum().reset_index() 
            custo_por_departamento = custo_por_departamento.sort_values('VALOR_TOTAL', ascending=False) 
              
            fig1 = px.bar( 
                custo_por_departamento, 
                x='DEPARTAMENTO', 
                y='VALOR_TOTAL', 
                title="Custo Total por Departamento", 
                labels={'DEPARTAMENTO': 'Departamento', 'VALOR_TOTAL': 'Custo Total (R$)'} 
            ) 
            fig1.update_layout(xaxis_tickangle=-45) 
            st.plotly_chart(fig1, use_container_width=True) 
        else: 
            st.info("Dados de departamento não disponíveis para análise.") 
          
        st.markdown("---") 
          
        st.subheader("Solicitações Realizadas vs. Atendidas") 
        if 'STATUS_PEDIDO' in df_dash.columns: 
            status_counts = df_dash['STATUS_PEDIDO'].value_counts().reset_index() 
            status_counts.columns = ['Status', 'Quantidade'] 
              
            fig2 = px.pie( 
                status_counts, 
                values='Quantidade', 
                names='Status', 
                title="Distribuição de Status dos Pedidos" 
            ) 
            st.plotly_chart(fig2, use_container_width=True) 
        else: 
            st.info("Dados de status não disponíveis para análise.") 
          
        st.markdown("---") 
          
        st.subheader("Evolução Temporal de Pedidos") 
        if 'DATA' in df_dash.columns: 
            df_dash['MES_ANO'] = df_dash['DATA'].dt.to_period('M').astype(str) 
            evolucao_temporal = df_dash.groupby('MES_ANO').agg({ 
                'REQUISICAO': 'count', 
                'VALOR_TOTAL': 'sum' 
            }).reset_index() 
            evolucao_temporal.columns = ['Mês', 'Quantidade de Pedidos', 'Valor Total'] 
              
            fig3 = make_subplots(specs=[[{"secondary_y": True}]]) 
              
            fig3.add_trace( 
                go.Bar( 
                    x=evolucao_temporal['Mês'], 
                    y=evolucao_temporal['Quantidade de Pedidos'], 
                    name="Quantidade de Pedidos", 
                    marker_color='#1C4D86' 
                ), 
                secondary_y=False 
            ) 
              
            fig3.add_trace( 
                go.Scatter( 
                    x=evolucao_temporal['Mês'], 
                    y=evolucao_temporal['Valor Total'], 
                    name="Valor Total (R$)", 
                    mode='lines+markers', 
                    line=dict(color='#FF7F0E') 
                ), 
                secondary_y=True 
            ) 
              
            fig3.update_layout( 
                title_text="Evolução Temporal de Pedidos and Valor", 
                xaxis_tickangle=-45 
            ) 
              
            fig3.update_yaxes(title_text="Quantidade de Pedidos", secondary_y=False) 
            fig3.update_yaxes(title_text="Valor Total (R$)", secondary_y=True) 
            
              
            st.plotly_chart(fig3, use_container_width=True) 
        else: 
            st.info("Dados de data não disponíveis para análise.") 
          
        st.markdown("---") 
          
        st.subheader("Top 10 Materiais Mais Solicitados") 
        if 'MATERIAL' in df_dash.columns: 
            materiais_mais_solicitados = df_dash['MATERIAL'].value_counts().head(10).reset_index() 
            materiais_mais_solicitados.columns = ['Material', 'Quantidade'] 
              
            fig4 = px.bar( 
                materiais_mais_solicitados, 
                x='Quantidade', 
                y='Material', 
                orientation='h', 
                title="Top 10 Materiais Mais Solicitados", 
                labels={'Quantidade': 'Quantidade de Solicitações', 'Material': 'Material'} 
            ) 
            st.plotly_chart(fig4, use_container_width=True) 
        else: 
            st.info("Dados de materiais não disponíveis para análise.") 
          
        st.markdown("---") 
          
        st.subheader("Top 10 Fornecedores por Volume de Compras") 
        if 'FORNECEDOR' in df_dash.columns and 'VALOR_TOTAL' in df_dash.columns: 
            fornecedores_por_volume = df_dash.groupby('FORNECEDOR')['VALOR_TOTAL'].sum().reset_index() 
            fornecedores_por_volume = fornecedores_por_volume.sort_values('VALOR_TOTAL', ascending=False).head(10) 
              
            fig5 = px.bar( 
                fornecedores_por_volume, 
                x='VALOR_TOTAL', 
                y='FORNECEDOR', 
                orientation='h', 
                title="Top 10 Fornecedores por Volume de Compras", 
                labels={'VALOR_TOTAL': 'Valor Total (R$)', 'FORNECEDOR': 'Fornecedor'} 
            ) 
            st.plotly_chart(fig5, use_container_width=True) 
        else: 
            st.info("Dados de fornecedores não disponíveis para análise.") 
          
        st.markdown("---") 
          
        st.subheader("Detalhes dos Pedidos") 
        st.dataframe(df_dash[['DATA', 'SOLICITANTE', 'DEPARTAMENTO', 'MATERIAL', 'QUANTIDADE', 'VALOR_ITEM', 'VALOR_TOTAL', 'STATUS_PEDIDO']], use_container_width=True) 

    elif menu == "📊 Performance ": 
        st.markdown(""" 
            <div class='header-container'> 
                <h1>📊 PERFORMANCE DE NEGOCIAÇÃO</h1> 
                <p>Análise de Economia em Pedidos</p> 
            </div> 
        """, unsafe_allow_html=True) 
        st.header("📊 Análise de Performance de Negociações") 

        df_performance = st.session_state.df_pedidos.copy() 
        df_performance['DATA'] = pd.to_datetime(df_performance['DATA'], errors='coerce', dayfirst=True) 
          
        st.markdown("---") 
        st.subheader("Filtros de Período") 
        col_filtro_p1, col_filtro_p2 = st.columns(2) 
          
        mes_selecionado_p = [] 
        ano_selecionado_p = None 
          
        df_valid_dates_p = df_performance.dropna(subset=['DATA']) 
          
        if not df_valid_dates_p.empty: 
            meses_disponiveis_p = df_valid_dates_p['DATA'].dt.month.unique() 
            anos_disponiveis_p = df_valid_dates_p['DATA'].dt.year.unique() 
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"} 
            with col_filtro_p1: 
                mes_selecionado_p = st.multiselect("Selecione o Mês", sorted(meses_disponiveis_p), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis_p) if sorted(meses_disponiveis_p) else []) 
            with col_filtro_p2: 
                ano_selecionado_p = st.selectbox("Selecione o Ano", sorted(anos_disponiveis_p, reverse=True)) 
        else: 
            st.info("Nenhum pedido com data válida para análise.") 
            st.stop() 
          
        if not mes_selecionado_p or ano_selecionado_p is None: 
              st.warning("Selecione pelo menos um mês e um ano para visualizar os dados.") 
              st.stop() 

        if mes_selecionado_p and ano_selecionado_p: 
            df_performance_filtrado = df_performance[(df_performance['DATA'].dt.month.isin(mes_selecionado_p)) & (df_performance['DATA'].dt.year == ano_selecionado_p)] 
        else: 
            df_performance_filtrado = pd.DataFrame() 
          
        if df_performance_filtrado.empty: 
            st.warning("Nenhum dado disponível para o período selecionado.") 
            st.stop() 
          
        # Fix pandas FutureWarning: Convert to numeric first, then fillna
        df_performance_filtrado['VALOR_RENEGOCIADO'] = pd.to_numeric(df_performance_filtrado['VALOR_RENEGOCIADO'], errors='coerce').fillna(0)
        df_performance_filtrado['VALOR_ITEM'] = pd.to_numeric(df_performance_filtrado['VALOR_ITEM'], errors='coerce').fillna(0)
        df_performance_filtrado['QUANTIDADE'] = pd.to_numeric(df_performance_filtrado['QUANTIDADE'], errors='coerce').fillna(0) 

        df_negociados = df_performance_filtrado.copy() 
        df_negociados = df_negociados[ 
            (df_negociados['VALOR_RENEGOCIADO'] > 0) &  
            (df_negociados['VALOR_ITEM'] > 0) & 
            (df_negociados['VALOR_ITEM'] != df_negociados['VALOR_RENEGOCIADO']) 
        ].copy() 
          
        if df_negociados.empty: 
            st.info("Nenhum pedido com negociação registrada no período para as análises abaixo.") 
            st.stop() 
              
        df_negociados['ECONOMIA'] = (df_negociados['QUANTIDADE'] * df_negociados['VALOR_ITEM']) - (df_negociados['QUANTIDADE'] * df_negociados['VALOR_RENEGOCIADO']) 
        df_negociados['PERC_ECONOMIA'] = np.where((df_negociados['QUANTIDADE'] * df_negociados['VALOR_ITEM']) > 0,  
                                                  ((df_negociados['QUANTIDADE'] * df_negociados['VALOR_ITEM']) - (df_negociados['QUANTIDADE'] * df_negociados['VALOR_RENEGOCIADO'])) / (df_negociados['QUANTIDADE'] * df_negociados['VALOR_ITEM']) * 100,  
                                                  0) 
          
        df_performance_local = df_performance_filtrado[df_performance_filtrado['TIPO_PEDIDO'] == 'LOCAL'].copy() 
          
        st.subheader("Visão Geral da Performance") 
        col1, col2, col3 = st.columns(3) 
        with col1: 
            total_pedidos_local = len(df_performance_local) 
            st.metric("Total de Pedidos Locals", total_pedidos_local) 
        with col2: 
            media_economia = df_negociados['PERC_ECONOMIA'].mean() if 'PERC_ECONOMIA' in df_negociados.columns and not df_negociados.empty else 0 
            st.metric("Média de Economia (%)", f"{media_economia:.2f}%") 
        with col3: 
            total_economizado = df_negociados['ECONOMIA'].sum() if 'ECONOMIA' in df_negociados.columns and not df_negociados.empty else 0 
            st.metric("Total Economizado", f"R$ {total_economizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) 
              
        st.markdown("---") 

        st.subheader("Curva de Desempenho da Negociação (Média Mensal)") 
        df_negociados['MES_APROVACAO'] = df_negociados['DATA_APROVACAO'].dt.to_period('M').astype(str) 
          
        curva_mensal = df_negociados.groupby('MES_APROVACAO')['PERC_ECONOMIA'].mean().reset_index() 
          
        if not curva_mensal.empty: 
            fig_curva = px.line( 
                curva_mensal, 
                x='MES_APROVACAO', 
                y='PERC_ECONOMIA', 
                markers=True, 
                title="Média de Economia Percentual Mensal", 
                labels={'PERC_ECONOMIA': 'Média de Economia (%)', 'MES_APROVACAO': 'Mês de Aprovação'} 
            ) 
            st.plotly_chart(fig_curva, use_container_width=True) 
        else: 
            st.info("Dados de negociação insuficientes para gerar a curva de desempenho.") 
          
        st.markdown("---") 

        st.subheader("Principais Solicitantes de Pedidos com Negociação") 
        ranking_solicitantes = df_negociados['SOLICITANTE'].value_counts().reset_index() 
        ranking_solicitantes.columns = ['Solicitante', 'Total de Pedidos com Negociação'] 
          
        if not ranking_solicitantes.empty: 
            fig_ranking = px.bar( 
                ranking_solicitantes.nlargest(10, 'Total de Pedidos com Negociação'), 
                x='Total de Pedidos com Negociação', 
                y='Solicitante', 
                orientation='h', 
                title='Top 10 Solicitantes de Pedidos com Negociação', 
                labels={'Total de Pedidos com Negociação': 'Número de Pedidos', 'Solicitante': 'Solicitante'} 
            ) 
            st.plotly_chart(fig_ranking, use_container_width=True) 
        else: 
            st.info("Dados de solicitantes com negociação insuficientes para gerar o ranking.") 

# Lógica de execução principal 
if 'logado' not in st.session_state or not st.session_state.logado: 
    render_login_page() 
else: 
    render_main_app()
