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
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import json
import re
import pytz
import sys

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

def get_gspread_client():
    """Retorna o cliente gspread autorizado."""
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    return gspread.authorize(credentials)

def parse_brazil_number(value_str):
    """
    Converte uma string de número no formato brasileiro (1.234,56) para float (1234.56).
    """
    if not isinstance(value_str, str):
        return value_str

    cleaned_value = value_str.strip()
    
    # Remove 'R$' e espaços.
    cleaned_value = re.sub(r'R\$\s*', '', cleaned_value)
    
    # Assume que a vírgula é sempre o separador decimal.
    cleaned_value = cleaned_value.replace('.', '')
    cleaned_value = cleaned_value.replace(',', '.')

    try:
        return float(cleaned_value)
    except (ValueError, TypeError):
        return pd.NaT

def _to_datetime(series, dayfirst=True):
    """Converte uma Series para datetime, retornando NaT para erros."""
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)

@st.cache_data(show_spinner=False)
def carregar_dados_almoxarifado():
    """Carrega dados do Google Sheets (aba de Almoxarifado - segunda aba)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(1)  # Segunda aba (índice 1) é Almoxarifado
        
        data = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        if not data or len(data) <= 1:
            return pd.DataFrame(columns=[
                "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
                "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
                "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "ORDEM_COMPRA",
                "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
            ])
        
        headers = data[0]
        records = data[1:]
        df = pd.DataFrame(records, columns=headers)

        colunas_essenciais = [
            "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "ORDEM_COMPRA",
            "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
        ]
        
        for col in colunas_essenciais:
            if col not in df.columns:
                df[col] = ''
            
        for col in ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']:
            if col in df.columns:
                df[col] = df[col].replace('', np.nan).replace(0, np.nan).replace('0', np.nan)
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        
        for col in ['V. TOTAL NF', 'VALOR FRETE']:
            if col in df.columns:
                df[col] = df[col].apply(parse_brazil_number).fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do almoxarifado: {e}")
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",
            "ORDEM_COMPRA", "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
        ])
def salvar_dados_almoxarifado(df):
    """Salva os dados do DataFrame no Google Sheets (segunda aba - Almoxarifado)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(1)  # Segunda aba (índice 1) é Almoxarifado

        df_copy = df.copy()

        df_copy = df_copy.rename(columns={
            "REGISTRO_ADICIONAL": "OBSERVACAO",
            "V. TOTAL NF": "V. TOTAL NF",
            "DOC NF": "DOC NF",
            "CONDICAO FRETE": "CONDICAO FRETE",
            "VALOR FRETE": "VALOR FRETE",
            "FORNECEDOR_NF": "FORNECEDOR_NF",
            "REGISTRO_LANCAMENTO": "REGISTRO_LANCAMENTO",
            "REGISTRO_ENVIO": "REGISTRO_ENVIO",
            "STATUS_FINANCEIRO": "STATUS_FINANCEIRO",
        }, errors='ignore')
        
        for col in ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y %H:%M:%S') if pd.notna(x) else '')

        df_copy = df_copy.loc[:,~df_copy.columns.duplicated()]
        
        worksheet.clear()
        set_with_dataframe(worksheet, df_copy, include_index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados do almoxarifado: {e}")
        return False

@st.cache_data(show_spinner=False)
def carregar_dados_pedidos():
    """Carrega os dados de pedidos do Google Sheets (primeira aba)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(0)  # Primeira aba (índice 0) é dados_pedido
        
        data = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        if not data or len(data) <= 1:
            st.warning("A planilha está vazia ou não contém dados.")
            return pd.DataFrame()
            
        headers = data[0]
        records = data[1:]
        
        df = pd.DataFrame(records, columns=headers)
        
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df.columns:
                df[col] = _to_datetime(df[col], dayfirst=True)
        
        numeric_cols = ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'QUANTIDADE']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(parse_brazil_number).fillna(0)
        
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ''
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de pedidos: {e}")
        return pd.DataFrame(columns=["DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", "DOC NF"])


def salvar_dados_pedidos(df):
    """Salva os dados de pedidos no Google Sheets (primeira aba)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(0)  # Primeira aba (índice 0) é dados_pedido

        df_copy = df.copy()
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
        
        set_with_dataframe(worksheet, df_copy, include_index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados de pedidos: {e}")
        return False
        
@st.cache_data(show_spinner=False)
def carregar_dados_solicitantes():
    """Carrega dados dos solicitantes do Google Sheets."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(3)  # O índice correto para "Solicitantes" é 3
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de solicitantes: {e}")
        return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])

# Lógica de login e usuários foi removida por ser redundante neste contexto
# e para focar na lógica principal do almoxarifado.

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
# REMOVIDO: A função de login, a página de login e a verificação de sessão foram removidas
# para que o aplicativo seja acessível diretamente.
# As funções render_login_page e fazer_login também foram removidas.

def render_main_app():
    """Exibe a interface principal da aplicação sem login."""
    try:
        logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
        logo_img = load_logo(logo_url)
        
        # O carregamento de dados foi movido para o topo do script para garantir que estejam sempre disponíveis
        if 'df_pedidos' not in st.session_state:
            st.session_state.df_pedidos = carregar_dados_pedidos()
        if 'df_almoxarifado' not in st.session_state:
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado()

        # Sidebar
        with st.sidebar:
            if logo_img:
                st.image(logo_img, use_container_width=True)
            
            st.title("Menu de Navegação")
            menu_option = st.radio(
                "Selecione a opção:",
                ["📝 Registrar NF", "📊 Dashboard", "🔍 Consultar NFs", "⚙️ Configurações"],
                index=0
            )
            st.divider()
        
        # Renderiza a página selecionada
        if menu_option == "📝 Registrar NF":
            render_registrar_nf_page()
        elif menu_option == "📊 Dashboard":
            render_dashboard_page()
        elif menu_option == "🔍 Consultar NFs":
            render_consultar_nfs_page()
        elif menu_option == "⚙️ Configurações":
            render_configuracoes_page()
    except Exception as e:
        st.error(f"Erro ao renderizar a página principal: {e}")
        st.info("Por favor, verifique a integridade dos dados nas suas planilhas e tente novamente.")

def render_registrar_nf_page():
    """Página para registrar novas notas fiscais."""
    st.markdown("""
        <div class='header-container'>
            <h1>🏭 REGISTRAR NOTA FISCAL</h1>
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.df_pedidos.empty:
        st.warning("Nenhum pedido encontrado. Não é possível registrar notas fiscais. Verifique a planilha de pedidos.")
        st.stop()
    
    # Inicializa variáveis de estado
    if 'oc_items_for_nf' not in st.session_state:
        st.session_state.oc_items_for_nf = pd.DataFrame(columns=['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE', 'VALOR_ITEM'])
    
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        with st.form("formulario_nota", clear_on_submit=False):
            col1_form, col2_form, col3_form = st.columns(3)
            
            with col1_form:
                fornecedores_disponiveis = st.session_state.df_pedidos['FORNECEDOR'].dropna().unique().tolist()
                fornecedor_selecionado = st.selectbox("Fornecedor da NF*", options=[''] + sorted(fornecedores_disponiveis), key="fornecedor_nf_select")
                nf_numero = st.text_input("Número da NF*", key="nf_numero_input")

            with col2_form:
                recebedor_options = [
                    "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                    "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                    "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                    "OUTROS"
                ]
                recebedor = st.selectbox("Recebedor*", sorted(recebedor_options), key="recebedor_select")
                
                ordens_disponiveis = ['']
                if fornecedor_selecionado:
                    pedidos_filtrados = st.session_state.df_pedidos[st.session_state.df_pedidos['FORNECEDOR'].str.strip() == fornecedor_selecionado.strip()]
                    ordens_disponiveis.extend(pedidos_filtrados['ORDEM_COMPRA'].dropna().unique().tolist())
                
                ordem_compra_nf = st.selectbox(
                    "N° Ordem de Compra*",
                    options=sorted(ordens_disponiveis),
                    help="Selecione o número da ordem de compra para vincular a nota.",
                    key="oc_select"
                )
                
                if ordem_compra_nf and st.session_state.get('last_oc_selected') != ordem_compra_nf:
                    oc_items = st.session_state.df_pedidos[st.session_state.df_pedidos['ORDEM_COMPRA'].str.strip() == ordem_compra_nf.strip()].copy()
                    if not oc_items.empty:
                        if 'QUANTIDADE_ENTREGUE' not in oc_items.columns:
                            oc_items['QUANTIDADE_ENTREGUE'] = 0.0
                        oc_items['SALDO_PENDENTE'] = oc_items['QUANTIDADE'] - oc_items['QUANTIDADE_ENTREGUE']
                        st.session_state.oc_items_for_nf = oc_items
                    else:
                        st.session_state.oc_items_for_nf = pd.DataFrame(columns=['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE', 'VALOR_ITEM'])
                    
                    st.session_state.last_oc_selected = ordem_compra_nf
                    st.rerun()

            with col3_form:
                valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00", key="valor_total_nf_input")
                condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"], key="condicao_frete_select")
                valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00", key="valor_frete_input")
            
            doc_nf_links = st.text_area("Links das Notas Fiscais (um por linha)", placeholder="Cole os links de acesso aqui...", key="doc_nf_links_area")
            
            observacao = st.text_area("Observações", placeholder="Informações adicionais...", key="observacao_area")
            vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30), key="vencimento_nf_input")
            
            st.markdown("---")
            st.subheader("Itens do Pedido")

            if not st.session_state.oc_items_for_nf.empty:
                df_to_edit = st.session_state.oc_items_for_nf[['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE']].copy()
                
                edited_items = st.data_editor(
                    df_to_edit,
                    use_container_width=True,
                    hide_index=True,
                    num_rows='fixed',
                    column_config={
                        "CODIGO_MATERIAL": st.column_config.TextColumn("Código Material", disabled=True),
                        "MATERIAL": st.column_config.TextColumn("Descrição Material", disabled=True),
                        "UN": st.column_config.TextColumn("UN", disabled=True),
                        "QUANTIDADE": st.column_config.NumberColumn("Qtd. Pedida", disabled=True, format="%d"),
                        "QUANTIDADE_ENTREGUE": st.column_config.NumberColumn("Qtd. Recebida", min_value=0, format="%d"),
                        "SALDO_PENDENTE": st.column_config.NumberColumn("Saldo Pendente", disabled=True, format="%d")
                    },
                    key="itens_pedido_editor"
                )
            
            else:
                st.info("Selecione uma Ordem de Compra para visualizar os itens.")
                edited_items = pd.DataFrame()


            enviar = st.form_submit_button("✅ Registrar Nota Fiscal")

            if enviar:
                if not ordem_compra_nf:
                    st.error("Por favor, selecione uma Ordem de Compra.")
                    st.stop()
                
                campos_validos = all([
                    fornecedor_selecionado.strip(), nf_numero.strip(),
                    valor_total_nf.strip() not in ["", "0,00"], doc_nf_links
                ])
                
                if not campos_validos:
                    st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                elif edited_items.empty:
                    st.error("Adicione os itens do pedido antes de registrar a nota fiscal.")
                else:
                    try:
                        valor_total_float = parse_brazil_number(valor_total_nf)
                        valor_frete_float = parse_brazil_number(valor_frete_nf)
                        
                        pedidos_relacionados = st.session_state.df_pedidos[
                            st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                        ].copy()
                        
                        valor_oc_total = (pedidos_relacionados['VALOR_ITEM'] * pedidos_relacionados['QUANTIDADE']).sum()
                        divergencia = valor_total_float - valor_oc_total
                        
                        brasilia_tz = pytz.timezone('America/Sao_Paulo')
                        agora = datetime.datetime.now(brasilia_tz)
                        
                        doc_nf_string = doc_nf_links.replace('\n', ', ')

                        novo_registro_nf = {
                            "DATA": datetime.date.today(),
                            "RECEBEDOR": recebedor,
                            "FORNECEDOR_NF": fornecedor_selecionado,
                            "NF": nf_numero,
                            "VOLUME": edited_items['QUANTIDADE_ENTREGUE'].sum(),
                            "V. TOTAL NF": valor_total_float,
                            "CONDICAO FRETE": condicao_frete_nf,
                            "VALOR FRETE": valor_frete_float,
                            "OBSERVACAO": observacao,
                            "DOC NF": doc_nf_string,
                            "VENCIMENTO": vencimento_nf,
                            "STATUS_FINANCEIRO": "EM ANDAMENTO",
                            "CONDICAO_PROBLEMA": "N/A",
                            "ORDEM_COMPRA": ordem_compra_nf,
                            "REGISTRO_ENVIO": agora,
                            "REGISTRO_LANCAMENTO": agora
                        }

                        if abs(divergencia) > 0.01:
                            st.session_state['mostrar_popup_divergencia'] = True
                            st.session_state['novo_registro_nf'] = novo_registro_nf
                            st.session_state.edited_items = edited_items
                            st.rerun()
                        else:
                            salvar_nota_fiscal(novo_registro_nf, edited_items, pedidos_relacionados)

                    except ValueError:
                        st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")
    
    if st.session_state.get('mostrar_popup_divergencia'):
        handle_divergence_popup()
    
    st.markdown("---")
    st.subheader("Últimas Notas Registradas")
    if not st.session_state.df_almoxarifado.empty:
        df_ultimas_nfs = st.session_state.df_almoxarifado[st.session_state.df_almoxarifado['NF'].astype(str) != ''].tail(10).copy()
        
        for col in ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']:
            if col in df_ultimas_nfs.columns:
                df_ultimas_nfs[col] = pd.to_datetime(df_ultimas_nfs[col], errors='coerce', dayfirst=True)
        
        df_ultimas_nfs['DATA'] = df_ultimas_nfs['DATA'].dt.strftime('%d/%m/%Y').fillna('')
        df_ultimas_nfs['VENCIMENTO'] = df_ultimas_nfs['VENCIMENTO'].dt.strftime('%d/%m/%Y').fillna('')
        df_ultimas_nfs['REGISTRO_LANCAMENTO_VISUAL'] = df_ultimas_nfs['REGISTRO_LANCAMENTO'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')

        col_map = {
            'DATA': 'Data',
            'FORNECEDOR_NF': 'Fornecedor',
            'NF': 'Número NF',
            'ORDEM_COMPRA': 'Ordem de Compra',
            'VOLUME': 'Volume',
            'V. TOTAL NF': 'Valor Total NF',
            'STATUS_FINANCEIRO': 'Status Financeiro',
            'DOC NF': 'Anexo NF',
            'REGISTRO_LANCAMENTO_VISUAL': 'Registro de Lançamento'
        }
        
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
                "Anexo NF": st.column_config.TextColumn(
                    "Anexos NF",
                    help="Links para abrir as notas fiscais."
                ),
                "Registro de Lançamento": st.column_config.TextColumn("Registro de Lançamento")
            },
            hide_index=True
        )
    else:
        st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")

def salvar_nota_fiscal(novo_registro_nf, edited_items_df, original_items_df):
    """Função para salvar a nota fiscal e atualizar os pedidos relacionados."""
    
    st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)
    
    for index, row in edited_items_df.iterrows():
        original_oc_items = st.session_state.df_pedidos[
            (st.session_state.df_pedidos['ORDEM_COMPRA'].str.strip() == novo_registro_nf['ORDEM_COMPRA'].strip()) &
            (st.session_state.df_pedidos['CODIGO_MATERIAL'] == row['CODIGO_MATERIAL'])
        ]
        
        if not original_oc_items.empty:
            original_idx = original_oc_items.index[0]
            
            quantidade_entregue_anterior = st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE_ENTREGUE']
            nova_quantidade_entregue = quantidade_entregue_anterior + row['QUANTIDADE_ENTREGUE']
            
            st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE_ENTREGUE'] = nova_quantidade_entregue
            st.session_state.df_pedidos.loc[original_idx, 'DOC NF'] = novo_registro_nf['DOC NF']
            
            if nova_quantidade_entregue >= st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE']:
                st.session_state.df_pedidos.loc[original_idx, 'STATUS_PEDIDO'] = 'ENTREGUE'
                st.session_state.df_pedidos.loc[original_idx, 'DATA_ENTREGA'] = pd.to_datetime(novo_registro_nf['DATA'])
    
    salvar_dados_pedidos(st.session_state.df_pedidos)
    salvar_dados_almoxarifado(st.session_state.df_almoxarifado)

    st.success(f"🎉 Nota fiscal {novo_registro_nf['NF']} registrada com sucesso!")
    
    df_pedidos_pos_salvamento = st.session_state.df_pedidos[st.session_state.df_pedidos['ORDEM_COMPRA'].str.strip() == novo_registro_nf['ORDEM_COMPRA'].strip()].copy()
    for index, row in df_pedidos_pos_salvamento.iterrows():
        saldo_restante = row['QUANTIDADE'] - row.get('QUANTIDADE_ENTREGUE', 0)
        if saldo_restante > 0:
            st.warning(f"⚠️ **Atenção:** O item '{row['MATERIAL']}' ainda tem um saldo pendente de **{saldo_restante}** unidades.")
        else:
            st.info(f"✅ O item '{row['MATERIAL']}' foi totalmente recebido.")

    st.session_state['mostrar_popup_divergencia'] = False
    st.rerun()

def handle_divergence_popup():
    """Exibe e gerencia o pop-up de divergência de valores."""
    with st.form("popup_divergencia"):
        valor_oc_formatado = f"R$ {st.session_state['valor_oc_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        valor_nf_formatado = f"R$ {st.session_state['novo_registro_nf']['V. TOTAL NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        divergencia_formatada = f"R$ {st.session_state['divergencia_oc']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        st.warning(f"⚠️ **Atenção: Divergência de Valor!**")
        st.write(f"O **Valor da Ordem de Compra** é: **{valor_oc_formatado}**")
        st.write(f"O **Valor da Nota Fiscal** digitado é: **{valor_nf_formatado}**")
        st.write(f"A **diferença** é de: **{divergencia_formatada}**")
        
        st.write("Você está ciente e concorda em registrar a nota fiscal com essa divergência?")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("✅ Sim, Salvar Nota Fiscal"):
                salvar_nota_fiscal(st.session_state['novo_registro_nf'], st.session_state.edited_items, st.session_state.oc_items_for_nf)
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
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
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
            
            datas_validas = df['DATA'].dropna()
            
            if not datas_validas.empty:
                data_minima = datas_validas.min().date()
                data_maxima = datas_validas.max().date()
            else:
                data_minima = datetime.date.today()
                data_maxima = datetime.date.today()
            
            data_inicio_consulta = st.date_input("Data Início", value=data_minima, min_value=data_minima, max_value=data_maxima)
            data_fim_consulta = st.date_input("Data Fim", value=data_maxima, min_value=data_minima, max_value=data_maxima)

        df_consulta = df.copy()
        
        if nf_consulta:  
            df_consulta = df_consulta[df_consulta['NF'].astype(str).str.contains(nf_consulta, case=False)]
        if ordem_compra_consulta:  
            df_consulta = df_consulta[df_consulta['ORDEM_COMPRA'].astype(str).str.contains(ordem_compra_consulta, case=False)]
        if fornecedor_consulta != "Todos":  
            df_consulta = df_consulta[df_consulta['FORNECEDOR_NF'] == fornecedor_consulta]
        if "Todos" not in status_consulta:  
            df_consulta = df_consulta[df_consulta['STATUS_FINANCEIRO'].isin(status_consulta)]
        
        if not df_consulta.empty and 'DATA' in df_consulta.columns:
            df_consulta['DATA'] = pd.to_datetime(df_consulta['DATA'], errors='coerce')
            df_consulta = df_consulta[df_consulta['DATA'].notna()]
            if not df_consulta.empty:
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
            
            df_exibir_consulta['DATA'] = df_exibir_consulta['DATA'].dt.strftime('%d/%m/%Y').fillna('Data inválida')
            
            def colorir_status(status):
                cores = {
                    "EM ANDAMENTO": "🟡",
                    "NF PROBLEMA": "🔴",
                    "CAPTURADO": "🟣",
                    "FINALIZADO": "🟢"
                }
                return f"{cores.get(status, '⚪')} {status}"
            
            if 'STATUS_FINANCEIRO' in df_exibir_consulta.columns:
                df_exibir_consulta['STATUS_FINANCEIRO'] = df_exibir_consulta['STATUS_FINANCEIRO'].apply(colorir_status)
            
            st.dataframe(
                df_exibir_consulta,
                use_container_width=True,
                height=400,
                column_config={
                    "DATA": st.column_config.TextColumn("Data"),
                    "Valor Total NF": st.column_config.NumberColumn("Valor Total NF", format="R$ %.2f"),
                    "Anexo NF": st.column_config.TextColumn(
                        "Anexos NF",
                        help="Links para abrir as notas fiscais."
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
            st.session_state.df_pedidos = carregar_dados_pedidos()
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado()
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
render_main_app()
