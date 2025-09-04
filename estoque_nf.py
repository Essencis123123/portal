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

# Carregar a imagem do logo a partir da URL
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

# --- Funções de conexão e carregamento de dados para Google Sheets ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
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

@st.cache_data
def carregar_dados_almoxarifado():
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(2)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        for col in ['DATA', 'VENCIMENTO']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        for col in ['V. TOTAL NF', 'VALOR FRETE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'CONDICAO_PROBLEMA' not in df.columns:
            df['CONDICAO_PROBLEMA'] = ''
        if 'REGISTRO_ADICIONAL' not in df.columns:
            df['REGISTRO_ADICIONAL'] = ''
        if 'ORDEM_COMPRA' not in df.columns:
            df['ORDEM_COMPRA'] = ''
        if 'STATUS_FINANCEIRO' not in df.columns:
            df['STATUS_FINANCEIRO'] = ''
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ''
        if 'NF' not in df.columns:
             df['NF'] = ''

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do almoxarifado: {e}")
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",
            "ORDEM_COMPRA"
        ])

def salvar_dados_almoxarifado(df):
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

@st.cache_data
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
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de pedidos: {e}")
        return pd.DataFrame(columns=["DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA"])

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

def carregar_dados_solicitantes():
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

# Funções de E-mail
status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]

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
    if email in USERS and USERS[email]["password"] == senha:
        st.session_state['logado'] = True
        st.session_state['nome_colaborador'] = USERS[email]["name"]
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# --- INTERFACE PRINCIPAL ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.title("🏭 Login do Almoxarifado")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)
    
    df_pedidos = carregar_dados_pedidos()
    df_almoxarifado = carregar_dados_almoxarifado()

    if 'df_pedidos' not in st.session_state:
        st.session_state.df_pedidos = df_pedidos
    if 'df_almoxarifado' not in st.session_state:
        st.session_state.df_almoxarifado = df_almoxarifado
    
    df_solicitantes = carregar_dados_solicitantes()

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
    
    if menu_option == "📝 Registrar NF":
        st.markdown("""
            <div class='header-container'>
                <h1>🏭 REGISTRAR NOTA FISCAL</h1>
                <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
            with st.form("formulario_nota", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    data_recebimento = st.date_input("Data do Recebimento*", datetime.date.today())
                    
                    ordem_compra_nf = st.text_input("N° Ordem de Compra*", help="Número da ordem de compra para vincular a nota")

                    fornecedor_selecionado = ""
                    
                    # 1. Cria uma cópia da coluna para limpeza
                    fornecedores_limpos = df_pedidos['FORNECEDOR'].astype(str).str.strip().str.replace('"', '').str.replace('\n', '')

                    # 2. Procura a OC na planilha de pedidos
                    if ordem_compra_nf:
                        ordem_compra_existe = df_pedidos[
                            df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                        ]
                        if not ordem_compra_existe.empty:
                            fornecedor_selecionado = fornecedores_limpos.loc[ordem_compra_existe.index].iloc[0]
                    
                    # 3. Exibe o fornecedor com base na OC, ou permite seleção manual
                    if fornecedor_selecionado:
                        st.text_input("Fornecedor da NF*", value=fornecedor_selecionado, disabled=True, key='fornecedor_oc')
                    else:
                        fornecedores_disponiveis = fornecedores_limpos.dropna().unique().tolist()
                        fornecedor_selecionado = st.selectbox("Fornecedor da NF*", options=[''] + sorted(fornecedores_disponiveis))
                    
                    nf_numero = st.text_input("Número da NF*")
                    
                with col2:
                    recebedor_options = [
                        "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                        "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                        "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                        "OUTROS"
                    ]
                    recebedor = st.selectbox("Recebedor*", sorted(recebedor_options))
                    volume_nf = st.number_input("Volume*", min_value=1, value=1)
                    
                with col3:
                    valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")
                    condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"])
                    valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00")
                
                doc_nf_link = st.text_input("Link da Nota Fiscal (URL)", placeholder="Cole o link de acesso aqui...")
                
                observacao = st.text_area("Observações", placeholder="Informações adicionais...")
                vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))
                
                enviar = st.form_submit_button("✅ Registrar Nota Fiscal")
                
                if enviar:
                    nome_final_fornecedor = fornecedor_selecionado if fornecedor_selecionado else st.session_state.get('fornecedor_oc')
                    campos_validos = all([
                        nome_final_fornecedor, nf_numero.strip(), ordem_compra_nf.strip(),
                        valor_total_nf.strip() not in ["", "0,00"]
                    ])
                    
                    if not campos_validos:
                        st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                    else:
                        try:
                            valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                            valor_frete_float = float(valor_frete_nf.replace(".", "").replace(",", "."))
                            
                            if 'ORDEM_COMPRA' in st.session_state.df_pedidos.columns:
                                pedidos_relacionados = st.session_state.df_pedidos[
                                    st.session_state.df_pedidos['ORDEM_COMPRA'].astype(str).str.strip().str.upper() == ordem_compra_nf.strip().upper()
                                ]
                                
                                if not pedidos_relacionados.empty:
                                    indices_a_atualizar = pedidos_relacionados.index
                                    st.session_state.df_pedidos.loc[indices_a_atualizar, 'STATUS_PEDIDO'] = 'ENTREGUE'
                                    st.session_state.df_pedidos.loc[indices_a_atualizar, 'DATA_ENTREGA'] = pd.to_datetime(data_recebimento)

                                    salvar_dados_pedidos(st.session_state.df_pedidos)
                                else:
                                    st.warning(f"ℹ️ A Ordem de Compra '{ordem_compra_nf}' não foi encontrada na planilha de pedidos. O status não foi atualizado.")
                            
                            novo_registro_nf = {
                                "DATA": pd.to_datetime(data_recebimento),
                                "RECEBEDOR": recebedor,
                                "FORNECEDOR": nome_final_fornecedor,
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
                            st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)
                            
                            if salvar_dados_almoxarifado(st.session_state.df_almoxarifado):
                                st.success(f"🎉 Nota fiscal {nf_numero} registrada com sucesso!")
                            else:
                                st.error("Erro ao salvar os dados da nota fiscal.")
                        
                            st.balloons()
                            st.rerun()
                        except ValueError:
                            st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")
        
        st.markdown("---")
        st.subheader("Últimas Notas Registradas")
        if not st.session_state.df_almoxarifado.empty:
            df_ultimas_nfs = st.session_state.df_almoxarifado[st.session_state.df_almoxarifado['NF'].astype(str) != ''].tail(10)
            
            st.dataframe(
                df_ultimas_nfs,
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


    elif menu_option == "📊 Dashboard":
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
                    top_problemas = problemas_df['FORNECEDOR'].value_counts().head(10).reset_index()
                    top_problemas.columns = ['Fornecedor', 'Notas com Problema']
                    fig_barras = px.bar(top_problemas, x='Notas com Problema', y='Fornecedor', orientation='h', title='Top 10 Fornecedores com Problemas')
                    st.plotly_chart(fig_barras, use_container_width=True)
                else:
                    st.info("✅ Nenhuma nota com problemas no momento")
            
        else:
            st.write("Nenhum dado disponível.")

    elif menu_option == "🔍 Consultar NFs":
        st.markdown("""
            <div class='header-container'>
                <h1>🔍 CONSULTAR NOTAS FISCAIS E PEDIDOS</h1>
                <p>Veja as Notas Fiscais e os Pedidos de Compra correspondentes</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Carregar os DataFrames de forma segura
        if 'df_pedidos' not in st.session_state:
            st.session_state.df_pedidos = carregar_dados_pedidos()
        if 'df_almoxarifado' not in st.session_state:
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado()

        df_pedidos_oc = st.session_state.df_pedidos.copy()
        df_almox = st.session_state.df_almoxarifado.copy()
        
        # Juntar os dois DataFrames pela Ordem de Compra
        # Os sufixos garantem que colunas com o mesmo nome sejam diferenciadas
        df_combinado = pd.merge(
            df_pedidos_oc, 
            df_almox, 
            on='ORDEM_COMPRA', 
            how='outer',
            suffixes=('_pedido', '_nf')
        )
        
        # A nova lógica de renomear as colunas é mais robusta
        # Renomeia FORNECEDOR_pedido para FORNECEDOR, mas verifica antes para não dar KeyError
        if 'FORNECEDOR_pedido' in df_combinado.columns:
            df_combinado.rename(columns={'FORNECEDOR_pedido': 'FORNECEDOR'}, inplace=True)
        
        # Renomeia DATA_pedido para DATA, mas verifica antes para não dar KeyError
        if 'DATA_pedido' in df_combinado.columns:
            df_combinado.rename(columns={'DATA_pedido': 'DATA'}, inplace=True)
        
        # Renomeia V. TOTAL NF_nf para V. TOTAL NF, mas verifica antes para não dar KeyError
        if 'V. TOTAL NF_nf' in df_combinado.columns:
            df_combinado.rename(columns={'V. TOTAL NF_nf': 'V. TOTAL NF'}, inplace=True)

        # Tratar valores nulos de 'NF' para facilitar a consulta
        # Adiciona a coluna 'NF' se ela não existir
        if 'NF' not in df_combinado.columns:
            df_combinado['NF'] = 'NÃO RECEBIDA'
        else:
            df_combinado['NF'].fillna('NÃO RECEBIDA', inplace=True)

        if not df_combinado.empty:
            st.subheader("🔎 Consulta Avançada")
            col1, col2 = st.columns(2)
            
            with col1:
                nf_consulta = st.text_input("Buscar por Número da NF", placeholder="Digite o número da NF...")
                ordem_compra_consulta = st.text_input("Buscar por N° Ordem de Compra", placeholder="Digite o número da OC...")
                fornecedor_consulta = st.selectbox("Filtrar por Fornecedor (Pedido)", options=["Todos"] + sorted(df_combinado['FORNECEDOR'].dropna().unique().tolist()))
            
            with col2:
                status_consulta = st.multiselect("Filtrar por Status (Pedido)", options=["Todos", "ENTREGUE", "PENDENTE"], default=["Todos"])
                
                if 'DATA' in df_combinado.columns and not df_combinado['DATA'].isnull().all():
                    data_minima = df_combinado['DATA'].min().date() if pd.notna(df_combinado['DATA'].min()) else datetime.date.today()
                    data_maxima = df_combinado['DATA'].max().date() if pd.notna(df_combinado['DATA'].max()) else datetime.date.today()
                else:
                    data_minima = datetime.date.today()
                    data_maxima = datetime.date.today()

                data_inicio_consulta = st.date_input("Data Início (Pedido)", value=data_minima, min_value=data_minima, max_value=data_maxima)
                data_fim_consulta = st.date_input("Data Fim (Pedido)", value=data_maxima, min_value=data_minima, max_value=data_maxima)

            df_consulta = df_combinado.copy()
            
            # Aplicar filtros
            if nf_consulta: df_consulta = df_consulta[df_consulta['NF'].astype(str).str.contains(nf_consulta, case=False)]
            if ordem_compra_consulta: df_consulta = df_consulta[df_consulta['ORDEM_COMPRA'].astype(str).str.contains(ordem_compra_consulta, case=False)]
            if fornecedor_consulta != "Todos": df_consulta = df_consulta[df_consulta['FORNECEDOR'] == fornecedor_consulta]
            if "Todos" not in status_consulta: df_consulta = df_consulta[df_consulta['STATUS_PEDIDO'].isin(status_consulta)]
            
            # Checa se 'DATA' existe antes de aplicar o filtro de data
            if 'DATA' in df_consulta.columns:
                 df_consulta = df_consulta[
                    (df_consulta['DATA'].dt.date >= data_inicio_consulta) &
                    (df_consulta['DATA'].dt.date <= data_fim_consulta)
                ]
            else:
                st.warning("⚠️ A coluna 'DATA' não foi encontrada para aplicar o filtro de data.")


            st.subheader(f"📋 Resultados da Consulta ({len(df_consulta)} itens encontrados)")
            
            if not df_consulta.empty:
                df_exibir_consulta = df_consulta[[
                    'REQUISICAO', 'DATA', 'SOLICITANTE', 'MATERIAL', 'QUANTIDADE', 
                    'FORNECEDOR', 'ORDEM_COMPRA', 'STATUS_PEDIDO', 
                    'NF', 'V. TOTAL NF', 'VENCIMENTO', 'DOC NF', 'STATUS_FINANCEIRO'
                ]].copy()
                
                df_exibir_consulta.columns = [
                    'Nº Requisição', 'Data Pedido', 'Solicitante', 'Material', 'Quantidade',
                    'Fornecedor', 'Nº Ordem de Compra', 'Status do Pedido',
                    'Nº NF', 'Valor Total NF', 'Vencimento NF', 'Link NF', 'Status Financeiro'
                ]
                
                # Checa se 'DATA' e 'VENCIMENTO' existem antes de formatar
                if 'DATA' in df_exibir_consulta.columns:
                    df_exibir_consulta['Data Pedido'] = df_exibir_consulta['DATA'].dt.strftime('%d/%m/%Y')
                
                if 'VENCIMENTO' in df_exibir_consulta.columns:
                    df_exibir_consulta['Vencimento NF'] = df_exibir_consulta['VENCIMENTO'].dt.strftime('%d/%m/%Y')
                
                if 'V. TOTAL NF' in df_exibir_consulta.columns:
                    df_exibir_consulta['Valor Total NF'] = df_exibir_consulta['V. TOTAL NF'].apply(
                        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else 'R$ 0,00'
                    )
                
                st.dataframe(
                    df_exibir_consulta,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "Link NF": st.column_config.LinkColumn(
                            "Link NF",
                            help="Clique para abrir a nota fiscal.",
                            display_text="📥 Abrir NF"
                        )
                    }
                )
                
                csv_consulta = df_exibir_consulta.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Download Resultados",
                    data=csv_consulta,
                    file_name="consulta_nfs_e_pedidos.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ Nenhum registro encontrado com os filtros aplicados.")
        else:
            st.info("📝 Nenhum dado disponível para consulta.")

    elif menu_option == "⚙️ Configurações":
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

        st.subheader("📋 Log de Atividades")
        if 'log_messages' in st.session_state:
            log_text = "\n".join(st.session_state['log_messages'])
            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)
        else:
            st.info("Nenhum log disponível.")
