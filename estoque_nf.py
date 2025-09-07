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
from google.oauth2.service_account import Credentials
import json

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Almoxarifado", layout="wide", page_icon="🏭")

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

# --- Funções de Carregamento e Salvamento de Dados ---
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

@st.cache_data(show_spinner=False)
def carregar_dados_almoxarifado():
    """Carrega dados do Google Sheets (aba de Almoxarifado)."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(2)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        colunas_essenciais = [
            "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "ORDEM_COMPRA"
        ]

        if df.empty:
            df = pd.DataFrame(columns=colunas_essenciais)
        else:
            for col in colunas_essenciais:
                if col not in df.columns:
                    df[col] = ''
            
        for col in ['DATA', 'VENCIMENTO']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        for col in ['V. TOTAL NF', 'VALOR FRETE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do almoxarifado: {e}")
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR_NF", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",
            "ORDEM_COMPRA"
        ])

def salvar_dados_almoxarifado(df):
    """Salva os dados do DataFrame no Google Sheets (aba de Almoxarifado)."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(2)

        df_copy = df.copy()
        for col in ['DATA', 'VENCIMENTO']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
        
        data_to_write = [df_copy.columns.values.tolist()] + df_copy.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados do almoxarifado: {e}")
        return False

@st.cache_data(show_spinner=False)
def carregar_dados_pedidos():
    """Carrega os dados de pedidos do Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # --- CORREÇÃO AQUI: Tratamento de valores numéricos com vírgula ---
        if 'VALOR_ITEM' in df.columns:
            # Converte para string para garantir a manipulação
            df['VALOR_ITEM'] = df['VALOR_ITEM'].astype(str)
            
            # Remove pontos de milhar
            df['VALOR_ITEM'] = df['VALOR_ITEM'].str.replace('.', '', regex=False)
            
            # Substitui a vírgula por ponto decimal
            df['VALOR_ITEM'] = df['VALOR_ITEM'].str.replace(',', '.', regex=False)
            
            # Converte para numérico
            df['VALOR_ITEM'] = pd.to_numeric(df['VALOR_ITEM'], errors='coerce').fillna(0)
        
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ''
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de pedidos: {e}")
        return pd.DataFrame(columns=["DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", "DOC NF"])

def salvar_dados_pedidos(df):
    """Salva os dados de pedidos no Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)

        df_copy = df.copy()
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
        
        data_to_write = [df_copy.columns.values.tolist()] + df_copy.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados de pedidos: {e}")
        return False

@st.cache_data(show_spinner=False)
def carregar_dados_solicitantes():
    """Carrega dados dos solicitantes do Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(1)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de solicitantes: {e}")
        return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])

# --- LÓGICA DE LOGIN ---
USERS = {
    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},
    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},
    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAURA SOARES"},
    "acsouza@essencis.com.br": {"password": "Essencis01", "name": "ANDRE CASTRO DE SOUZA"},
    "bcampos@essencis.com.br": {"password": "Essencis01", "name": "BARBARA DA SILVA CAMPOS"},
    "earaujo@essencis.com.br": {"password": "Essencis01", "name": "EMERSON ALMEIDA DE ARAUJO"}
}

def fazer_login(email, senha):
    """Lógica para autenticar o usuário."""
    if email in USERS and USERS[email]["password"] == senha:
        st.session_state['logado'] = True
        st.session_state['nome_colaborador'] = USERS[email]["name"]
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
        time.sleep(1)
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# --- INTERFACE PRINCIPAL ---
def render_login_page():
    """Exibe a página de login."""
    st.title("🏭 Login do Almoxarifado")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)

def render_main_app():
    """Exibe a interface principal da aplicação após o login."""
    # Carrega a logo e dados
    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)
    
    # Carregamento de dados com cache e tratamento de estado de sessão
    if 'df_pedidos' not in st.session_state:
        st.session_state.df_pedidos = carregar_dados_pedidos()
    if 'df_almoxarifado' not in st.session_state:
        st.session_state.df_almoxarifado = carregar_dados_almoxarifado()

    df_solicitantes = carregar_dados_solicitantes()

    # Sidebar
    if logo_img:
        st.sidebar.image(logo_img, use_container_width=True)
    
    st.sidebar.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")
    st.sidebar.title("Menu de Navegação")
    menu_option = st.sidebar.radio(
        "Selecione a opção:",
        ["📝 Registrar NF", "📊 Dashboard", "🔍 Consultar NFs", "⚙️ Configurações"],
        index=0
    )
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        st.session_state['logado'] = False
        st.session_state.pop('nome_colaborador', None)
        st.rerun()
    
    # Renderiza a página selecionada
    if menu_option == "📝 Registrar NF":
        render_registrar_nf_page()
    elif menu_option == "📊 Dashboard":
        render_dashboard_page()
    elif menu_option == "🔍 Consultar NFs":
        render_consultar_nfs_page()
    elif menu_option == "⚙️ Configurações":
        render_configuracoes_page()

def render_registrar_nf_page():
    """Página para registrar novas notas fiscais."""
    st.markdown("""
        <div class='header-container'>
            <h1>🏭 REGISTRAR NOTA FISCAL</h1>
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fornecedores_disponiveis = st.session_state.df_pedidos['FORNECEDOR'].dropna().unique().tolist()
        # O seletor de fornecedor está fora do formulário para habilitar o filtro dinâmico
        fornecedor_selecionado = st.selectbox("Fornecedor da NF*", options=[''] + sorted(fornecedores_disponiveis))
        nf_numero = st.text_input("Número da NF*")

    # Lógica para filtrar as Ordens de Compra com base no fornecedor selecionado
    ordens_disponiveis = ['']
    if fornecedor_selecionado:
        pedidos_filtrados = st.session_state.df_pedidos[
            (st.session_state.df_pedidos['FORNECEDOR'] == fornecedor_selecionado)
        ]
        ordens_disponiveis.extend(pedidos_filtrados['ORDEM_COMPRA'].dropna().unique().tolist())
    
    with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
        with st.form("formulario_nota", clear_on_submit=True):
            col1_form, col2_form, col3_form = st.columns(3)
            
            with col1_form:
                data_recebimento = st.date_input("Data do Recebimento*", datetime.date.today())
                
                # Exibe o fornecedor selecionado do widget fora do formulário
                st.write(f"**Fornecedor Selecionado:** `{fornecedor_selecionado}`")
                st.write(f"**Número da NF:** `{nf_numero}`")
                
            with col2_form:
                recebedor_options = [
                    "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                    "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                    "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                    "OUTROS"
                ]
                recebedor = st.selectbox("Recebedor*", sorted(recebedor_options))

                ordem_compra_nf = st.selectbox(
                    "N° Ordem de Compra*",
                    options=sorted(ordens_disponiveis),
                    help="Selecione o número da ordem de compra para vincular a nota."
                )
                
                volume_nf = st.number_input("Volume*", min_value=1, value=1)
                
            with col3_form:
                valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")
                condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"])
                valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00")
            
            doc_nf_link = st.text_input("Link da Nota Fiscal (URL)", placeholder="Cole o link de acesso aqui...")
            observacao = st.text_area("Observações", placeholder="Informações adicionais...")
            vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))
            
            enviar = st.form_submit_button("✅ Registrar Nota Fiscal")
            
            if enviar:
                campos_validos = all([
                    fornecedor_selecionado.strip(), nf_numero.strip(), ordem_compra_nf.strip(),
                    valor_total_nf.strip() not in ["", "0,00"]
                ])
                
                if not campos_validos:
                    st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                else:
                    try:
                        # O valor da NF digitado já é tratado aqui para aceitar vírgula e ponto
                        valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                        valor_frete_float = float(valor_frete_nf.replace(".", "").replace(",", "."))
                        
                        pedidos_relacionados = st.session_state.df_pedidos[
                            st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                        ]
                        
                        valor_oc_total = 0.0
                        if not pedidos_relacionados.empty:
                            try:
                                # O valor_oc_total já está numérico após a correção na função de carregamento
                                valor_oc_total = pedidos_relacionados['VALOR_ITEM'].sum()
                            except ValueError:
                                st.warning("Não foi possível calcular o valor da OC. Verifique o formato dos dados.")
                        
                        divergencia = valor_total_float - valor_oc_total
                        
                        st.session_state['novo_registro_nf'] = {
                            "DATA": pd.to_datetime(data_recebimento),
                            "RECEBEDOR": recebedor,
                            "FORNECEDOR_NF": fornecedor_selecionado, 
                            "NF": nf_numero,
                            "VOLUME": volume_nf,
                            "V. TOTAL NF": valor_total_float,
                            "CONDICAO FRETE": condicao_frete_nf,
                            "VALOR FRETE": valor_frete_float,
                            "OBSERVACAO": observacao,
                            "DOC NF": doc_nf_link,
                            "VENCIMENTO": pd.to_datetime(vencimento_nf),
                            "STATUS_FINANCEIRO": "EM ANDAMENTO",
                            "CONDICAO_PROBLEMA": "N/A",
                            "REGISTRO_ADICIONAL": "",
                            "ORDEM_COMPRA": ordem_compra_nf
                        }
                        st.session_state['divergencia_oc'] = divergencia
                        st.session_state['valor_oc_total'] = valor_oc_total
                        
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
        df_ultimas_nfs = st.session_state.df_almoxarifado[st.session_state.df_almoxarifado['NF'].astype(str) != ''].tail(10)
        st.dataframe(
            df_ultimas_nfs[[ 'DATA', 'FORNECEDOR_NF', 'NF', 'ORDEM_COMPRA', 'VOLUME', 'V. TOTAL NF', 'STATUS_FINANCEIRO', 'DOC NF']],
            use_container_width=True,
            column_config={
                "DOC NF": st.column_config.LinkColumn(
                    "DOC NF",
                    help="Clique para abrir a nota fiscal.",
                    display_text="📥 Abrir NF"
                )
            }
        )
    else:
        st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")

def salvar_nota_fiscal(novo_registro_nf):
    """Função para salvar a nota fiscal e atualizar os pedidos relacionados."""
    st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)
    
    pedidos_relacionados = st.session_state.df_pedidos[
        st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == novo_registro_nf['ORDEM_COMPRA'].strip().upper()
    ]
    indices_a_atualizar = pedidos_relacionados.index
    st.session_state.df_pedidos.loc[indices_a_atualizar, 'STATUS_PEDIDO'] = 'ENTREGUE'
    st.session_state.df_pedidos.loc[indices_a_atualizar, 'DATA_ENTREGA'] = pd.to_datetime(novo_registro_nf['DATA'])
    st.session_state.df_pedidos.loc[indices_a_atualizar, 'DOC NF'] = novo_registro_nf['DOC NF']
    
    salvar_dados_pedidos(st.session_state.df_pedidos)
    
    if salvar_dados_almoxarifado(st.session_state.df_almoxarifado):
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
        divergencia_formatada = f"R$ {st.session_state['divergencia_oc']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        st.warning(f"⚠️ **Atenção: Divergência de Valor!**")
        st.write(f"O **Valor da Ordem de Compra** é: **{valor_oc_formatado}**")
        st.write(f"O **Valor da Nota Fiscal** digitado é: **{valor_nf_formatado}**")
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
            
            fornecedores_unicos = sorted(df['FORNECEDOR_NF'].dropna().unique().tolist()) if 'FORNECEDOR_NF' in df.columns else []
            fornecedor_consulta = st.selectbox("Filtrar por Fornecedor", options=["Todos"] + fornecedores_unicos)
        
        with col2:
            status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]
            status_consulta = st.multiselect("Filtrar por Status", options=["Todos"] + status_financeiro_options, default=["Todos"])
            
            data_minima = df['DATA'].min().date() if pd.notna(df['DATA'].min()) else datetime.date.today()
            data_maxima = df['DATA'].max().date() if pd.notna(df['DATA'].max()) else datetime.date.today()
            
            data_inicio_consulta = st.date_input("Data Início", value=data_minima, min_value=data_minima, max_value=data_maxima)
            data_fim_consulta = st.date_input("Data Fim", value=data_maxima, min_value=data_minima, max_value=data_maxima)

        df_consulta = df.copy()
        
        if nf_consulta: df_consulta = df_consulta[df_consulta['NF'].astype(str).str.contains(nf_consulta, case=False)]
        if ordem_compra_consulta: df_consulta = df_consulta[df_consulta['ORDEM_COMPRA'].astype(str).str.contains(ordem_compra_consulta, case=False)]
        if fornecedor_consulta != "Todos": df_consulta = df_consulta[df_consulta['FORNECEDOR_NF'] == fornecedor_consulta]
        if "Todos" not in status_consulta: df_consulta = df_consulta[df_consulta['STATUS_FINANCEIRO'].isin(status_consulta)]
        
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
                    "CAPTURADO": "🟠",
                    "FINALIZADO": "🟢"
                }
                return f"{cores.get(status, '⚪')} {status}"
            
            df_exibir_consulta['STATUS_FINANCEIRO'] = df_exibir_consulta['STATUS_FINANCEIRO'].apply(colorir_status)
            df_exibir_consulta['DATA'] = df_exibir_consulta['DATA'].dt.strftime('%d/%m/%Y')
            
            def formatar_moeda(valor):
                return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            df_exibir_consulta['V. TOTAL NF'] = df_exibir_consulta['V. TOTAL NF'].apply(formatar_moeda)
            
            st.dataframe(
                df_exibir_consulta,
                use_container_width=True,
                height=400,
                column_config={
                    "DOC NF": st.column_config.LinkColumn(
                        "DOC NF",
                        help="Clique para abrir a nota fiscal.",
                        display_text="📥 Abrir NF"
                    ),
                    "FORNECEDOR_NF": "FORNECEDOR",
                }
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
        st.write(f"Última atualização: **{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}**")
        
        if st.button("🔄 Recarregar Dados"):
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

# --- Execução da Aplicação ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    render_login_page()
else:
    render_main_app()
