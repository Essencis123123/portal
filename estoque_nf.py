import streamlit as st
import pandas as pd
import datetime
import os
import time
import plotly.express as px
from pandas.errors import EmptyDataError
import numpy as np
import requests
from PIL import Image
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials
import json
import re
import pytz

# ==============================================================================
# CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO CSS
# ==============================================================================
# Configuração da página com layout wide e ícone
st.set_page_config(page_title="Painel Almoxarifado", layout="wide", page_icon="🏭")

# CSS personalizado para o tema Essencis
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
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j p,
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j,
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

# ==============================================================================
# FUNÇÕES DE UTILIDADE E CONEXÃO
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_logo(url):
    """Carrega a imagem do logo a partir de uma URL e a armazena em cache."""
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        st.error(f"Erro ao carregar o logo: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Retorna o cliente gspread autorizado."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None

@st.cache_data(ttl=300, show_spinner="Carregando dados do Google Sheets...")
def carregar_dados_google_sheets(_client, sheet_name):
    """Carrega dados de uma planilha específica do Google Sheets."""
    try:
        # ID da planilha do Google Sheets (substitua pelo seu ID real)
        SPREADSHEET_ID = st.secrets["spreadsheet_id"]
        
        # Abre a planilha
        spreadsheet = _client.open_by_key(SPREADSHEET_ID)
        
        # Seleciona a aba específica
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Obtém todos os registros como DataFrame
        df = get_as_dataframe(worksheet, evaluate_formulas=True)
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

def salvar_dados_google_sheets(_client, df, sheet_name):
    """Salva dados em uma planilha específica do Google Sheets."""
    try:
        # ID da planilha do Google Sheets
        SPREADSHEET_ID = st.secrets["spreadsheet_id"]
        
        # Abre a planilha
        spreadsheet = _client.open_by_key(SPREADSHEET_ID)
        
        # Seleciona a aba específica
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Limpa a planilha existente
        worksheet.clear()
        
        # Atualiza com os novos dados
        set_with_dataframe(worksheet, df)
        
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")
        return False

def parse_brazil_number(value_str):
    """
    Converte uma string de número no formato brasileiro (1.234,56) para float (1234.56).
    """
    if pd.isna(value_str) or value_str == '' or value_str is None:
        return 0.0
        
    if isinstance(value_str, (int, float)):
        return float(value_str)
        
    if not isinstance(value_str, str):
        try:
            return float(value_str)
        except:
            return 0.0

    cleaned_value = str(value_str).strip()
    
    # Remove 'R$' e espaços.
    cleaned_value = re.sub(r'R\$\s*', '', cleaned_value)
    
    # Assume que a vírgula é sempre o separador decimal.
    cleaned_value = cleaned_value.replace('.', '')
    cleaned_value = cleaned_value.replace(',', '.')

    try:
        return float(cleaned_value)
    except (ValueError, TypeError):
        return 0.0

def _to_datetime(series, dayfirst=True):
    """Converte uma Series para datetime, retornando NaT para erros."""
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)

def carregar_dados_almoxarifado(_client):
    """Carrega dados da aba de Almoxarifado do Google Sheets."""
    df = carregar_dados_google_sheets(_client, "Almoxarifado")
    
    if df.empty:
        return pd.DataFrame()
    
    # Garante que todas as colunas esperadas existam
    colunas_esperadas = [
        "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
        "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
        "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "ORDEM_COMPRA", "REGISTRO_ENVIO", 
        "REGISTRO_LANCAMENTO", "VALOR_JUROS", "VALOR_FRETE", "CONDICAO_FRETE", 
        "MES_ANO", "ANO", "MES"
    ]
    
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = ''
    
    # Converter colunas de data
    date_columns = ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Converter colunas numéricas
    numeric_cols = ['V. TOTAL NF', 'VALOR FRETE', 'VALOR_JUROS', 'VOLUME']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Garantir que colunas críticas sejam strings
    string_cols = ['NF', 'ORDEM_COMPRA', 'FORNECEDOR_NF', 'STATUS_FINANCEIRO']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna('')
    
    return df

def carregar_dados_pedidos(_client):
    """Carrega os dados de pedidos do Google Sheets."""
    df = carregar_dados_google_sheets(_client, "Pedidos")
    
    if df.empty:
        return pd.DataFrame()
    
    # Converter colunas de data
    date_columns = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Converter colunas numéricas
    numeric_cols = ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'QUANTIDADE']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'DOC NF' not in df.columns:
        df['DOC NF'] = ''
            
    return df

def carregar_dados_solicitantes(_client):
    """Carrega dados dos solicitantes do Google Sheets."""
    df = carregar_dados_google_sheets(_client, "Solicitantes")
    return df

def salvar_dados_almoxarifado(_client, df):
    """Salva os dados do DataFrame no Google Sheets."""
    return salvar_dados_google_sheets(_client, df, "Almoxarifado")

def salvar_dados_pedidos(_client, df):
    """Salva os dados de pedidos no Google Sheets."""
    return salvar_dados_google_sheets(_client, df, "Pedidos")

def atualizar_status_pedido(ordem_compra, quantidade_entregue, valor_total_nf):
    """Atualiza o status do pedido com base na quantidade entregue e valor."""
    if 'df_pedidos' not in st.session_state:
        return
    
    # Encontra o pedido correspondente
    mask = st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra.strip().upper()
    
    if mask.any():
        # Atualiza a quantidade entregue e valor
        st.session_state.df_pedidos.loc[mask, 'QUANTIDADE_ENTREGUE'] = quantidade_entregue
        st.session_state.df_pedidos.loc[mask, 'VALOR_ENTREGUE'] = valor_total_nf
        
        # Calcula totais para a ordem de compra
        quantidade_total = st.session_state.df_pedidos.loc[mask, 'QUANTIDADE'].sum()
        valor_total_oc = st.session_state.df_pedidos.loc[mask, 'VALOR_ITEM'].sum()
        
        # Verifica quantas notas já foram registradas para esta OC
        nfs_registradas = st.session_state.df_almoxarifado[
            st.session_state.df_almoxarifado['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra.strip().upper()
        ]
        
        quantidade_total_entregue = nfs_registradas['VOLUME'].sum()
        valor_total_entregue = nfs_registradas['V. TOTAL NF'].sum()
        
        # Atualiza o status com base nas quantidades
        if quantidade_total_entregue >= quantidade_total and abs(valor_total_entregue - valor_total_oc) <= 0.01:
            st.session_state.df_pedidos.loc[mask, 'STATUS_PEDIDO'] = 'ENTREGUE'
        elif quantidade_total_entregue > 0:
            st.session_state.df_pedidos.loc[mask, 'STATUS_PEDIDO'] = 'PARCIALMENTE ENTREGUE'

# ==============================================================================
# FUNÇÕES DE PÁGINA
# ==============================================================================
def render_login_page():
    """Página de login."""
    st.markdown(
        """
        <div style='text-align: center; padding: 50px 0;'>
            <h1 style='color: #1C4D86;'>Sistema de Controle de Almoxarifado</h1>
            <p style='color: #555;'>Faça login para acessar o sistema</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            if st.form_submit_button("Entrar"):
                # Verificação simples de login (substitua por sua lógica de autenticação)
                if username == "admin" and password == "admin":
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = username
                    
                    # Inicializa o cliente do Google Sheets
                    st.session_state.gs_client = get_gspread_client()
                    
                    # Carrega os dados
                    if st.session_state.gs_client:
                        st.session_state.df_pedidos = carregar_dados_pedidos(st.session_state.gs_client)
                        st.session_state.df_almoxarifado = carregar_dados_almoxarifado(st.session_state.gs_client)
                        st.session_state.df_solicitantes = carregar_dados_solicitantes(st.session_state.gs_client)
                    
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")

def render_main_app():
    """Aplicação principal após login."""
    # Sidebar com navegação
    with st.sidebar:
        # Logo da empresa
        logo_url = "https://example.com/logo.png"  # Substitua pela URL real do logo
        logo = load_logo(logo_url)
        if logo:
            st.image(logo)
        
        st.title("🏭 Almoxarifado")
        st.write(f"Usuário: {st.session_state.get('usuario', 'N/A')}")
        
        # Menu de navegação
        pagina = st.radio(
            "Navegação",
            ["📋 Registrar NF", "📊 Dashboard", "🔍 Consultar NFs", "⚙️ Configurações"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()
    
    # Conteúdo principal baseado na página selecionada
    if pagina == "📋 Registrar NF":
        render_registrar_nf_page()
    elif pagina == "📊 Dashboard":
        render_dashboard_page()
    elif pagina == "🔍 Consultar NFs":
        render_consultar_nfs_page()
    elif pagina == "⚙️ Configurações":
        render_configuracoes_page()

def render_registrar_nf_page():
    """Página para registrar novas notas fiscais."""
    st.markdown("""
        <div class='header-container'>
            <h1>📋 REGISTRAR NOTA FISCAL</h1>
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Verifica se os dados foram carregados
    if 'df_pedidos' not in st.session_state or st.session_state.df_pedidos.empty:
        st.error("Dados de pedidos não disponíveis. Verifique a conexão com o Google Sheets.")
        return
    
    if 'df_almoxarifado' not in st.session_state:
        st.session_state.df_almoxarifado = pd.DataFrame()
    
    # Inicializa estado para popup de divergência se não existir
    if 'mostrar_popup_divergencia' not in st.session_state:
        st.session_state['mostrar_popup_divergencia'] = False
    
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        with st.form("formulario_nota", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Data de recebimento
                data_recebimento = st.date_input(
                    "Data de Recebimento*",
                    value=datetime.date.today(),
                    help="Data em que a mercadoria foi recebida"
                )
                
                # Recebedor
                recebedor = st.text_input(
                    "Recebedor*",
                    value="ARLEY GONCALVES DOS SANTOS",
                    help="Nome de quem recebeu a mercadoria"
                )
                
                # Fornecedor
                fornecedores_disponiveis = st.session_state.df_pedidos['FORNECEDOR'].dropna().unique().tolist()
                fornecedor_selecionado = st.selectbox(
                    "Fornecedor*",
                    options=[''] + sorted(fornecedores_disponiveis),
                    help="Selecione o fornecedor da nota fiscal"
                )
                
                # Número da NF
                nf_numero = st.text_input(
                    "Número da NF*",
                    placeholder="Ex: 123456",
                    help="Número da nota fiscal"
                )
                
                # Volume
                volume_nf = st.number_input(
                    "Volume*",
                    min_value=1,
                    value=1,
                    help="Quantidade de volumes recebidos"
                )
            
            with col2:
                # Ordem de Compra
                ordens_disponiveis = ['']
                if fornecedor_selecionado:
                    pedidos_filtrados = st.session_state.df_pedidos[
                        (st.session_state.df_pedidos['FORNECEDOR'] == fornecedor_selecionado)
                    ]
                    ordens_disponiveis.extend(pedidos_filtrados['ORDEM_COMPRA'].dropna().unique().tolist())
                
                ordem_compra_nf = st.selectbox(
                    "Ordem de Compra*",
                    options=sorted(ordens_disponiveis),
                    help="Selecione a ordem de compra relacionada"
                )
                
                # Valor Total NF
                valor_total_nf = st.text_input(
                    "Valor Total NF (R$)*",
                    placeholder="Ex: 1.234,56",
                    help="Valor total da nota fiscal"
                )
                
                # Condição de Frete
                condicao_frete_nf = st.selectbox(
                    "Condição de Frete*",
                    options=["CIF", "FOB"],
                    index=0,
                    help="Condição de frete (CIF: frete pago pelo fornecedor, FOB: frete pago pelo destinatário)"
                )
                
                # Valor do Frete
                valor_frete_nf = st.text_input(
                    "Valor do Frete (R$)",
                    placeholder="Ex: 100,00",
                    value="0,00",
                    help="Valor do frete (se houver)"
                )
                
                # Quantidade Entregue
                quantidade_entregue_nf = st.number_input(
                    "Quantidade Entregue*",
                    min_value=1,
                    value=1,
                    help="Quantidade de itens entregues nesta nota"
                )
            
            # Observação e Link do Documento
            observacao = st.text_area(
                "Observações",
                placeholder="Observações adicionais sobre a nota fiscal...",
                height=80
            )
            
            doc_nf_link = st.text_input(
                "Link do Documento NF",
                placeholder="URL do documento da NF (SharePoint, Drive, etc.)",
                help="Link para a nota fiscal digitalizada"
            )
            
            # Data de Vencimento
            vencimento_nf = st.date_input(
                "Data de Vencimento*",
                value=datetime.date.today() + datetime.timedelta(days=30),
                help="Data de vencimento para pagamento"
            )
            
            # Botão de envio
            enviar = st.form_submit_button("📤 Registrar Nota Fiscal")
            
            if enviar:
                campos_validos = all([
                    fornecedor_selecionado.strip(), 
                    nf_numero.strip(), 
                    ordem_compra_nf.strip(),
                    valor_total_nf.strip() not in ["", "0,00"], 
                    quantidade_entregue_nf > 0
                ])
                
                if not campos_validos:
                    st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                else:
                    try:
                        valor_total_float = parse_brazil_number(valor_total_nf)
                        valor_frete_float = parse_brazil_number(valor_frete_nf)
                        
                        # Buscar pedidos relacionados
                        pedidos_relacionados = st.session_state.df_pedidos[
                            st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                        ]
                        
                        valor_oc_total = 0.0
                        if not pedidos_relacionados.empty:
                            # Soma todos os valores dos itens relacionados à mesma OC
                            valor_oc_total = pedidos_relacionados['VALOR_ITEM'].sum()
                        
                        # Verifica se já existem notas para esta OC
                        nfs_existentes = st.session_state.df_almoxarifado[
                            st.session_state.df_almoxarifado['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                        ]
                        
                        valor_total_existente = nfs_existentes['V. TOTAL NF'].sum() if not nfs_existentes.empty else 0
                        divergencia = (valor_total_existente + valor_total_float) - valor_oc_total
                        
                        # Remover timezone para compatibilidade
                        agora = datetime.datetime.now()
                        
                        st.session_state['novo_registro_nf'] = {
                            "DATA": data_recebimento,
                            "RECEBEDOR": recebedor,
                            "FORNECEDOR_NF": fornecedor_selecionado,   
                            "NF": nf_numero,
                            "VOLUME": volume_nf,
                            "V. TOTAL NF": valor_total_float,
                            "CONDICAO FRETE": condicao_frete_nf,
                            "VALOR FRETE": valor_frete_float,
                            "OBSERVACAO": observacao,
                            "DOC NF": doc_nf_link,
                            "VENCIMENTO": vencimento_nf,
                            "STATUS_FINANCEIRO": "EM ANDAMENTO",
                            "CONDICAO_PROBLEMA": "N/A",
                            "ORDEM_COMPRA": ordem_compra_nf,
                            "REGISTRO_ENVIO": agora,
                            "REGISTRO_LANCAMENTO": agora,
                            "VALOR_JUROS": 0,
                            "VALOR_FRETE": valor_frete_float,
                            "CONDICAO_FRETE": condicao_frete_nf,
                            "MES_ANO": data_recebimento.strftime('%Y-%m'),
                            "ANO": data_recebimento.year,
                            "MES": data_recebimento.month
                        }
                        
                        st.session_state['divergencia_oc'] = divergencia
                        st.session_state['valor_oc_total'] = valor_oc_total
                        st.session_state['quantidade_entregue'] = quantidade_entregue_nf
                        st.session_state['valor_total_existente'] = valor_total_existente
                        
                        if abs(divergencia) > 0.01:
                            st.session_state['mostrar_popup_divergencia'] = True
                            st.rerun()
                        else:
                            salvar_nota_fiscal(st.session_state['novo_registro_nf'])
                    
                    except ValueError:
                        st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")
    
    # Lógica do Pop-up de Validação
    if st.session_state.get('mostrar_popup_divergencia'):
        handle_divergence_popup()
    
    st.markdown("---")
    st.subheader("Últimas Notas Registradas")
    if not st.session_state.df_almoxarifado.empty:
        # Filtrar notas fiscais válidas
        df_ultimas_nfs = st.session_state.df_almoxarifado.copy()
        
        # Remover linhas com NF vazia
        df_ultimas_nfs = df_ultimas_nfs[df_ultimas_nfs['NF'].astype(str).str.strip() != '']
        
        if not df_ultimas_nfs.empty:
            # Ordenar por data de registro (mais recente primeiro)
            if 'REGISTRO_LANCAMENTO' in df_ultimas_nfs.columns:
                df_ultimas_nfs = df_ultimas_nfs.sort_values('REGISTRO_LANCAMENTO', ascending=False)
            
            # Pegar as últimas 10 notas
            df_ultimas_nfs = df_ultimas_nfs.head(10)
            
            # Formatar datas para exibição
            for col in ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']:
                if col in df_ultimas_nfs.columns:
                    df_ultimas_nfs[col] = df_ultimas_nfs[col].apply(
                        lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
                    )
            
            col_map = {
                'DATA': 'Data',
                'FORNECEDOR_NF': 'Fornecedor',
                'NF': 'Número NF',
                'ORDEM_COMPRA': 'Ordem de Compra',
                'VOLUME': 'Volume',
                'V. TOTAL NF': 'Valor Total NF',
                'STATUS_FINANCEIRO': 'Status Financeiro',
                'DOC NF': 'Anexo NF'
            }
            
            # Filtra apenas as colunas que existem no DataFrame
            available_cols = [col for col in col_map.keys() if col in df_ultimas_nfs.columns]
            col_map_filtered = {k: v for k, v in col_map.items() if k in available_cols}
            
            df_ultimas_nfs_display = df_ultimas_nfs[available_cols].rename(columns=col_map_filtered)
            
            def colorir_status_display(status):
                cores = {
                    "EM ANDAMENTO": "🟡",
                    "NF PROBLEMA": "🔴",
                    "CAPTURADO": "🟣",
                    "FINALIZADO": "🟢"
                }
                return f"{cores.get(status, '⚪')} {status}"
            
            if 'Status Financeiro' in df_ultimas_nfs_display.columns:
                df_ultimas_nfs_display['Status Financeiro'] = df_ultimas_nfs_display['Status Financeiro'].apply(colorir_status_display)
            
            st.dataframe(
                df_ultimas_nfs_display,
                use_container_width=True,
                column_config={
                    "Data": st.column_config.TextColumn("Data"),
                    "Valor Total NF": st.column_config.NumberColumn("Valor Total NF", format="R$ %.2f"),
                    "Anexo NF": st.column_config.LinkColumn(
                        "Anexo NF",
                        help="Clique para abrir a nota fiscal.",
                        display_text="📥 Abrir NF"
                    )
                },
                hide_index=True
            )
        else:
            st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")
    else:
        st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")

def salvar_nota_fiscal(novo_registro_nf):
    """Função para salvar a nota fiscal e atualizar os pedidos relacionados."""
    
    # Adiciona o registro à planilha do almoxarifado
    st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)
    
    # Atualiza o status do pedido com base na quantidade entregue
    atualizar_status_pedido(
        novo_registro_nf['ORDEM_COMPRA'], 
        st.session_state.get('quantidade_entregue', 0),
        novo_registro_nf['V. TOTAL NF']
    )
    
    # Salva as alterações em ambas as planilhas
    if salvar_dados_pedidos(st.session_state.gs_client, st.session_state.df_pedidos) and \
       salvar_dados_almoxarifado(st.session_state.gs_client, st.session_state.df_almoxarifado):
        st.success(f"🎉 Nota fiscal {novo_registro_nf['NF']} registrada com sucesso!")
    else:
        st.error("Erro ao salvar os dados da nota fiscal.")
    
    st.session_state['mostrar_popup_divergencia'] = False
    st.rerun()

def handle_divergence_popup():
    """Exibe e gerencia o pop-up de divergência de valores."""
    with st.form("popup_divergencia"):
        valor_oc_formatado = f"R$ {st.session_state['valor_oc_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        valor_nf_formatado = f"R$ {st.session_state['novo_registro_nf']['V. TOTAL NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        valor_existente_formatado = f"R$ {st.session_state['valor_total_existente']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        divergencia_formatada = f"R$ {st.session_state['divergencia_oc']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        st.warning(f"⚠️ **Atenção: Divergência de Valor!**")
        st.write(f"O **Valor da Ordem de Compra** é: **{valor_oc_formatado}**")
        st.write(f"O **Valor das Notas Existentes** é: **{valor_existente_formatado}**")
        st.write(f"O **Valor da Nova Nota Fiscal** é: **{valor_nf_formatado}**")
        st.write(f"O **Total com a nova nota** será: **R$ {st.session_state['valor_total_existente'] + st.session_state['novo_registro_nf']['V. TOTAL NF']:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        st.write(f"A **diferença** é de: **{divergencia_formatada}**")
        
        st.write("Você está ciente e concorda em registrar a nota fiscal com essa divergência?")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("✅ Sim, Salvar Nota Fiscal"):
                salvar_nota_fiscal(st.session_state['novo_registro_nf'])
        with col_btn2:
            if st.form_submit_button("❌ Não, Corrigir Valores"):
                st.session_state['mostrar_popup_divergencia'] = False
                st.info("Valores não salvos. Por favor, corrija as informações.")
                st.rerun()

def render_dashboard_page():
    """Página do dashboard com visualizações de dados."""
    st.markdown("""
        <div class='header-container'>
            <h1>📊 DASHBOARD ALMOXARIFADO</h1>
            <p>Análise estratégica dos custos por departamento</p>
        </div>
    """, unsafe_allow_html=True)
    
    df = st.session_state.df_almoxarifado
    if not df.empty:
        df_almoxarifado_filtrado = df[df['NF'].astype(str) != '']
        
        col1, col2, col3, col4 = st.columns(4)
        total_nfs = len(df_almoxarifado_filtrado)
        em_andamento = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'EM ANDAMENTO'])
        com_problema = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'NF PROBLEMA'])
        finalizadas = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'FINALIZADO'])
        
        with col1: st.metric("📦 Total de NFs", total_nfs)
        with col2: st.metric("🔄 Em Andamento", em_andamento)
        with col3: st.metric("⚠️ Com Problema", com_problema)
        with col4: st.metric("✅ Finalizadas", finalizadas)
        
        st.subheader("📈 Análise do Status Financeiro")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            status_count = df_almoxarifado_filtrado['STATUS_FINANCEIRO'].value_counts().reset_index()
            status_count.columns = ['Status', 'Quantidade']
            if not status_count.empty:
                fig_pizza = px.pie(status_count, values='Quantidade', names='Status', title='Distribuição dos Status Financeiros')
                st.plotly_chart(fig_pizza, use_container_width=True)
        
        with col_g2:
            problemas_df = df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'NF PROBLEMA']
            if not problemas_df.empty:
                top_problemas = problemas_df['FORNECEDOR_NF'].value_counts().head(10).reset_index()
                top_problemas.columns = ['Fornecedor', 'Notas com Problema']
                fig_barras = px.bar(top_problemas, x='Notas com Problema', y='Fornecedor', orientation='h', title='Top 10 Fornecedores com Problemas')
                st.plotly_chart(fig_barras, use_container_width=True)
            else:
                st.info("✅ Nenhuma nota com problemas no momento")
    else:
        st.write("Nenhum dado disponível.")

def render_consultar_nfs_page():
    """Página para consultar e filtrar notas fiscais."""
    st.markdown("""
        <div class='header-container'>
            <h1>🔍 CONSULTAR NOTAS FISCAIS</h1>
            <p>Sistema de Controle de Notas Fiscals e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    df = st.session_state.df_almoxarifado.copy()
    
    if not df.empty:
        st.subheader("🔎 Consulta Avançada")
        col1, col2 = st.columns(2)
        
        with col1:
            nf_consulta = st.text_input("Buscar por Número da NF", placeholder="Digite o número da NF...")
            ordem_compra_consulta = st.text_input("Buscar por N° Ordem de Compra", placeholder="Digite o número da OC...")
            
            df['FORNECEDOR_NF'] = df['FORNECEDOR_NF'].astype(str)
            fornecedores_unicos = sorted(df['FORNECEDOR_NF'].dropna().unique().tolist()) if 'FORNECEDOR_NF' in df.columns else []
            fornecedor_consulta = st.selectbox("Filtrar por Fornecedor", options=["Todos"] + fornecedores_unicos)
        
        with col2:
            status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]
            status_consulta = st.multiselect("Filtrar por Status", options=["Todos"] + status_financeiro_options, default=["Todos"])
            
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
            
            data_minima = df['DATA'].min().date() if pd.notna(df['DATA'].min()) else datetime.date.today()
            data_maxima = df['DATA'].max().date() if pd.notna(df['DATA'].max()) else datetime.date.today()
            
            data_inicio_consulta = st.date_input("Data Início", value=data_minima, min_value=data_minima, max_value=data_maxima)
            data_fim_consulta = st.date_input("Data Fim", value=data_maxima, min_value=data_minima, max_value=data_maxima)

        df_consulta = df.copy()
        
        if nf_consulta: df_consulta = df_consulta[df_consulta['NF'].astype(str).str.contains(nf_consulta, case=False)]
        if ordem_compra_consulta: df_consulta = df_consulta[df_consulta['ORDEM_COMPRA'].astype(str).str.contains(ordem_compra_consulta, case=False)]
        if fornecedor_consulta != "Todos": df_consulta = df_consulta[df_consulta['FORNECEDOR_NF'] == fornecedor_consulta]
        if "Todos" not in status_consulta: df_consulta = df_consulta[df_consulta['STATUS_FINANCEIRO'].isin(status_consulta)]
        
        if not df_consulta.empty and pd.api.types.is_datetime64_any_dtype(df_consulta['DATA']):
            df_consulta = df_consulta[
                (df_consulta['DATA'].dt.date >= data_inicio_consulta) &
                (df_consulta['DATA'].dt.date <= data_fim_consulta)
            ]
        
        st.subheader(f"📋 Resultados da Consulta ({len(df_consulta)} notas encontradas)")
        
        if not df_consulta.empty:
            df_exibir_consulta = df_consulta[[
                'DATA', 'FORNECEDOR_NF', 'NF', 'ORDEM_COMPRA', 'VOLUME', 'V. TOTAL NF',
                'STATUS_FINANCEIRO', 'DOC NF'
            ]].copy()
            
            def colorir_status(status):
                cores = {
                    "EM ANDAMENTO": "🟡",
                    "NF PROBLEMA": "🔴",
                    "CAPTURADO": "🟣",
                    "FINALIZADO": "🟢"
                }
                return f"{cores.get(status, '⚪')} {status}"
            
            df_exibir_consulta['STATUS_FINANCEIRO'] = df_exibir_consulta['STATUS_FINANCEIRO'].apply(colorir_status)
            
            st.dataframe(
                df_exibir_consulta,
                use_container_width=True,
                height=400,
                column_config={
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "FORNECEDOR_NF": "Fornecedor",
                    "NF": "N° NF",
                    "ORDEM_COMPRA": "N° Ordem de Compra",
                    "VOLUME": "Volume",
                    "V. TOTAL NF": st.column_config.NumberColumn("Valor Total NF", format="R$ %.2f"),
                    "STATUS_FINANCEIRO": "Status Financeiro",
                    "DOC NF": st.column_config.LinkColumn(
                        "Anexo NF",
                        help="Clique para abrir a nota fiscal.",
                        display_text="📥 Abrir NF"
                    )
                },
                hide_index=True
            )
            
            csv_consulta = df_exibir_consulta.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 Download Resultados",
                data=csv_consulta,
                file_name="consulta_nfs.csv",
                mime="text/csv",
                help="Clique para baixar os dados da tabela filtrada."
            )
        else:
            st.warning("⚠️ Nenhuma nota fiscal encontrada com os filtros aplicados.")
    else:
        st.info("📝 Nenhum dado disponível para consulta.")

def render_configuracoes_page():
    """Página de configurações do sistema."""
    st.markdown("""
        <div class='header-container'>
            <h1>⚙️ CONFIGURAÇÕES DO SISTEMA</h1>
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    df = st.session_state.df_almoxarifado
    
    st.subheader("⚙️ Configurações Gerais")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Informações do Sistema**")
        st.write(f"Total de notas cadastradas: **{len(df)}**")
        
        brasilia_tz = pytz.timezone('America/Sao_Paulo')
        agora_brasilia = datetime.datetime.now(brasilia_tz).strftime('%d/%m/%Y %H:%M')
        st.write(f"Última atualização: **{agora_brasilia}**")
        
        if st.button("🔄 Recarregar Dados"):
            st.cache_data.clear()
            st.session_state.df_pedidos = carregar_dados_pedidos(st.session_state.gs_client)
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado(st.session_state.gs_client)
            st.session_state.df_solicitantes = carregar_dados_solicitantes(st.session_state.gs_client)
            st.success("Dados recarregados com sucesso!")
            st.rerun()
    
    with col2:
        st.info("**Manutenção**")
        st.write("Versão: 1.0")
        
        csv_backup = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="💾 Fazer Backup",
            data=csv_backup,
            file_name=f"backup_almoxarifado_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Clique para baixar uma cópia de segurança dos dados."
        )

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if 'logado' not in st.session_state or not st.session_state['logado']:
    render_login_page()
else:
    render_main_app()
