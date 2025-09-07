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
from pandas.errors import EmptyDataError

# Configuração da página com layout wide e ícone
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

# --- Funções de Conexão, Carregamento e Utilitários ---
@st.cache_data(show_spinner=False)
def load_logo(url):
    """Carrega a imagem de um URL e armazena em cache."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
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

def formatar_numero_brasileiro(valor, casas_decimais=2):
    """Formata número no padrão brasileiro (vírgula como separador decimal)"""
    if pd.isna(valor) or valor == 0:
        return ''
    return f"{valor:,.{casas_decimais}f}".replace('.', '|').replace(',', '.').replace('|', ',')

def criar_dataframe_pedidos_vazio():
    """Cria um DataFrame de pedidos vazio com a estrutura correta."""
    return pd.DataFrame(columns=[
        "DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "UN", "QUANTIDADE", "TIPO_PEDIDO",
        "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO",
        "DATA_APROVACAO", "PREVISAO_ENTREGA", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", "DIAS_ATRASO", "DIAS_EMISSAO", "DOC NF", "VALOR_TOTAL", "CODIGO_MATERIAL"
    ])

def criar_dataframe_solicitantes_vazio():
    """Cria um DataFrame de solicitantes vazio."""
    return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])

@st.cache_data(show_spinner="Carregando dados de pedidos...")
def carregar_dados_pedidos():
    """Carrega o DataFrame de pedidos do Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        
        # Use UNFORMATTED_VALUE para obter números como floats
        data = spreadsheet.get_worksheet(0).get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        headers = data[0]
        records = data[1:]

        if not records:
            st.warning("A planilha de pedidos está vazia ou não contém dados.")
            return criar_dataframe_pedidos_vazio()
        
        df = pd.DataFrame(records, columns=headers)

        # Trata colunas de data
        date_cols = ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                
        # Converte colunas numéricas - tratamento correto para formato brasileiro
        numeric_cols = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']
        for col in numeric_cols:
            if col in df.columns:
                # Se for string, converte do formato brasileiro para float
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)
        
        if 'QUANTIDADE' in df.columns and 'VALOR_ITEM' in df.columns:
            df['VALOR_TOTAL'] = df['QUANTIDADE'] * df['VALOR_ITEM']
            df['VALOR_TOTAL'] = df['VALOR_TOTAL'].round(2)
        
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ""
        
        if 'PREVISAO_ENTREGA' not in df.columns:
            df['PREVISAO_ENTREGA'] = pd.NaT

        df['STATUS_PEDIDO'] = df['DATA_ENTREGA'].apply(
            lambda x: 'ENTREGUE' if pd.notna(x) else 'PENDENTE'
        )
        
        if 'UN' not in df.columns:
            df['UN'] = ''
        if 'CODIGO_MATERIAL' not in df.columns:
            df['CODIGO_MATERIAL'] = ''

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        st.info("Criando um DataFrame vazio. Verifique suas credenciais e a planilha.")
        return criar_dataframe_pedidos_vazio()

def salvar_dados_pedidos(df):
    """Salva o DataFrame de pedidos no Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)

        df_to_save = df.copy()
        
        # Converte as colunas de data para o formato string
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
                )
        
        # Converte valores numéricos para formato brasileiro com 2 casas decimais
        numeric_cols_to_save = ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']
        for col in numeric_cols_to_save:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: formatar_numero_brasileiro(x, 2) if pd.notna(x) else ''
                )
        
        if 'VALOR_TOTAL' in df_to_save.columns:
            df_to_save.drop(columns='VALOR_TOTAL', inplace=True, errors='ignore')

        df_to_save = df_to_save.fillna('')
        
        set_with_dataframe(worksheet, df_to_save, resize=True, include_column_header=True)
        
        st.success("Dados salvos na planilha com sucesso!")
        st.cache_data.clear()
        st.rerun() # Adicionado para recarregar a página após o salvamento
        
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")

@st.cache_data(show_spinner="Carregando dados de solicitantes...")
def carregar_dados_solicitantes():
    """Carrega o DataFrame de solicitantes do Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(1)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de solicitantes do Google Sheets: {e}")
        return criar_dataframe_solicitantes_vazio()

def salvar_dados_solicitantes(df):
    """Salva o DataFrame de solicitantes no Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(1)

        data_to_write = [df.columns.values.tolist()] + df.values.tolist()
        
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        
        st.success("Solicitante cadastrado na planilha com sucesso!")
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"Erro ao salvar dados de solicitantes no Google Sheets: {e}")

@st.cache_data(show_spinner=False)
def carregar_dados_almoxarifado():
    """Carrega dados do almoxarifado para preencher a nota fiscal."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(2)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        ordem_colunas = ['ORDEM_COMPRA', 'DOC NF']
        df = df.reindex(columns=ordem_colunas, fill_value="")
        
        return df
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar dados do Almoxarifado para preencher a nota fiscal. Verifique a aba 'Almoxarifado' da planilha. {e}")
        return pd.DataFrame(columns=['ORDEM_COMPRA', 'DOC NF'])

@st.cache_data(show_spinner=False)
def carregar_dados_materiais():
    """Carrega o DataFrame de materiais do Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(3)
        data = worksheet.get_all_records()
        
        if not data:
            df = pd.DataFrame(columns=['CODIGO', 'DESCRICAO'])
        else:
            df = pd.DataFrame(data)
            df.columns = [col.upper() for col in df.columns]
        
        return df
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar dados de materiais. Verifique a aba 'MATERIAIS' da planilha. {e}")
        return pd.DataFrame(columns=['CODIGO', 'DESCRICAO'])

def salvar_dados_materiais(df):
    """Salva o DataFrame de materiais no Google Sheets."""
    try:
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(3)
        
        df_to_save = df.copy()
        df_to_save = df_to_save.fillna('')

        data_to_write = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        st.success("Material cadastrado na planilha com sucesso!")
        
    except Exception as e:
        st.error(f"Erro ao salvar dados de materiais no Google Sheets: {e}")

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
    if email in USERS and USERS[email]["password"] == senha:
        st.session_state['logado'] = True
        st.session_state['nome_colaborador'] = USERS[email]["name"]
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# --- INTERFACE PRINCIPAL ---
logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

if 'logado' not in st.session_state or not st.session_state.logado:
    st.title("Login - Painel do Comprador")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
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

    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        
        st.write(f"Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!")
        st.title("👨‍💼 Comprador")
        st.divider()
        menu = st.radio(
            "📌 Navegação",
            ["📝 Requisição", "✍️ Pedidos (OC)", "📜 Histórico ", "👤 Cadastro ", "📊 Dashboards ", "📊 Performance "]
        )
        st.divider()
        if st.sidebar.button("Logout"):
            st.session_state['logado'] = False
            st.session_state.pop('nome_colaborador', None)
            st.rerun()

    if menu == "📝 Requisição":
        st.markdown("""
            <div class='header-container'>
                <h1>📝 REGISTRAR REQUISIÇÃO DE COMPRA</h1>
                <p>Sistema de Controle e Análise de Pedidos</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.header("📝 Registrar Nova Requisição de Compra")
        
        solicitantes_nomes = [""] + st.session_state.df_solicitantes['NOME'].unique().tolist()
        
        departamento_selecionado = ""
        filial_selecionada = ""

        # Usando colunas para compactar a primeira linha
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            solicitante_selecionado = st.selectbox("Solicitante", solicitantes_nomes)
            if solicitante_selecionado:
                solicitante_info = st.session_state.df_solicitantes[st.session_state.df_solicitantes['NOME'] == solicitante_selecionado].iloc[0]
                departamento_selecionado = solicitante_info['DEPARTAMENTO']
                filial_selecionada = solicitante_info['FILIAL']
        
        with col2:
            st.text_input("Departamento", value=departamento_selecionado, disabled=True)
        
        with col3:
            st.text_input("Filial", value=filial_selecionada, disabled=True)
            
        with col4:
            requisicao = st.text_input("N° Requisição")

        # Segunda linha para os outros campos
        col5, col6 = st.columns(2)
        with col5:
            data_requisicao = st.date_input("Data da Requisição", datetime.date.today())
        with col6:
            tipo_pedido = st.selectbox("Tipo de Pedido", ["LOCAL", "EMERGENCIAL", "PROGRAMADO"])
        
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
                }
            )

        col_item1, col_item2, col_item3, col_item4 = st.columns([1, 2, 1, 1])
        with col_item1:
            item_codigo = st.text_input("Código do Material", key="codigo_material_input")
        with col_item2:
            descricao_material = ""
            if item_codigo and not st.session_state.df_materiais.empty:
                material_info = st.session_state.df_materiais[st.session_state.df_materiais['CODIGO'] == item_codigo.upper()]
                if not material_info.empty:
                    descricao_material = material_info.iloc[0]['DESCRICAO']
            item_material = st.text_input("Descrição do Material", value=descricao_material, disabled=True, key="material_input")
        with col_item3:
            unidade_medida = st.selectbox("Unidade de Medida", ["UN", "KG", "L", "M", "M2", "M3", "PÇ"], key="unidade_medida_input")
        with col_item4:
            item_quantidade = st.number_input("Quantidade", min_value=1, value=1, key="quantidade_input")
        if st.button("➕ Adicionar Item"):
            if item_codigo and item_material and item_quantidade > 0 and unidade_medida:
                novo_item = pd.DataFrame([{"CODIGO_MATERIAL": item_codigo.upper(), "MATERIAL": item_material.upper(), "UN": unidade_medida, "QUANTIDADE": item_quantidade}])
                st.session_state.itens_requisicao_temp = pd.concat([st.session_state.itens_requisicao_temp, novo_item], ignore_index=True)
                st.success("Item adicionado! Você pode editar ou excluir na tabela acima.")
                st.rerun()
            else:
                st.error("Por favor, preencha todos os campos obrigatórios (Código, Descrição, Unidade e Quantidade).")
        
        st.write("---")
        
        if st.button("Finalizar e Registrar Requisição"):
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
                        "FORNECEDOR": "", "ORDEM_COMPRA": "", "VALOR_ITEM": 0.0, "VALOR_RENEGOCIADO": 0.0,
                        "DATA_APROVACAO": pd.NaT, "PREVISAO_ENTREGA": pd.NaT, "CONDICAO_FRETE": "",
                        "STATUS_PEDIDO": "PENDENTE", "DATA_ENTREGA": pd.NaT,
                        "DIAS_ATRASO": 0, "DIAS_EMISSAO": 0, "DOC NF": ""
                    }
                    linhas_a_adicionar.append(nova_linha)
                
                st.session_state.df_pedidos = pd.concat([st.session_state.df_pedidos, pd.DataFrame(linhas_a_adicionar)], ignore_index=True)
                salvar_dados_pedidos(st.session_state.df_pedidos)
                st.session_state.itens_requisicao_temp = pd.DataFrame(columns=["CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE"])
                st.success("Requisição registrada com sucesso! Vá para 'Atualizar Pedidos' para completar as informações.")
                st.balloons()
            else:
                st.error("O campo 'Número da Requisição' e pelo menos um item são obrigatórios.")

    elif menu == "✍️ Pedidos (OC)":
        st.markdown("""
            <div class='header-container'>
                <h1>✍️ ATUALIZAR PEDIDOS COM OC</h1>
                <p>Vincule as Ordens de Compra às Requisições Pendentes</p>
            </div>
        """, unsafe_allow_html=True)

        st.header("✍️ Atualizar Requisições com Dados de Ordem de Compra")
        st.info("Edite os campos diretamente na tabela abaixo para adicionar os dados de Ordem de Compra. Eles serão salvos ao clicar no botão abaixo.")
        
        pedidos_pendentes_oc = st.session_state.df_pedidos[
            (st.session_state.df_pedidos['ORDEM_COMPRA'].isnull()) | (st.session_state.df_pedidos['ORDEM_COMPRA'] == "")
        ].copy()
        
        pedidos_pendentes_oc['DATA'] = pd.to_datetime(pedidos_pendentes_oc['DATA'], errors='coerce', dayfirst=True)
        
        if pedidos_pendentes_oc.empty:
            st.success("🎉 Todas as requisições pendentes já foram atualizadas com uma Ordem de Compra!")
            st.stop()
        
        df_almox = st.session_state.df_almoxarifado.copy()
        if not df_almox.empty:
            df_almox_oc = df_almox[['ORDEM_COMPRA', 'DOC NF']].copy()
            pedidos_pendentes_oc = pedidos_pendentes_oc.merge(df_almox_oc, on='ORDEM_COMPRA', how='left', suffixes=('', '_almox'))
            pedidos_pendentes_oc['DOC NF'] = pedidos_pendentes_oc['DOC NF_almox'].fillna(pedidos_pendentes_oc['DOC NF'])
            pedidos_pendentes_oc.drop(columns=['DOC NF_almox'], inplace=True, errors='ignore')

        data_cols_to_convert = ['DATA', 'DATA_APROVACAO', 'PREVISAO_ENTREGA']
        for col in data_cols_to_convert:
            if col in pedidos_pendentes_oc.columns:
                pedidos_pendentes_oc[col] = pedidos_pendentes_oc[col].apply(
                    lambda x: x.date() if pd.notna(x) else None
                )
        
        cols_para_editar = [
            "REQUISICAO", "DATA", "SOLICITANTE", "CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE",
            "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO",
            "PREVISAO_ENTREGA", "DATA_APROVACAO", "CONDICAO_FRETE"
        ]
        
        df_editavel = pedidos_pendentes_oc[cols_para_editar].copy()
        
        with st.form(key="form_atualizar_pedidos"):
            edited_df = st.data_editor(
                df_editavel,
                use_container_width=True,
                hide_index=True,
                column_order=cols_para_editar,
                column_config={
                    "REQUISICAO": st.column_config.Column("N° Requisição", disabled=True),
                    "DATA": st.column_config.DateColumn("Data da Requisição", disabled=True),
                    "SOLICITANTE": st.column_config.TextColumn("Solicitante", disabled=True),
                    "CODIGO_MATERIAL": st.column_config.TextColumn("Cód. Material", disabled=True),
                    "MATERIAL": st.column_config.TextColumn("Material", disabled=True),
                    "UN": st.column_config.TextColumn("UN", disabled=True),
                    "QUANTIDADE": st.column_config.NumberColumn("Qtd.", disabled=True),
                    "FORNECEDOR": st.column_config.TextColumn("Nome Fornecedor"),
                    "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                    "VALOR_ITEM": st.column_config.NumberColumn("Valor Unitário (R$)", format="R$ %.2f"),
                    "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado (R$)", format="R$ %.2f"),
                    "PREVISAO_ENTREGA": st.column_config.DateColumn("Previsão de Entrega"),
                    "DATA_APROVACAO": st.column_config.DateColumn("Data de Aprovação"),
                    "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB"]),
                }
            )
            
            submitted = st.form_submit_button("Salvar Atualizações")

        if submitted:
            st.info("Detectando alterações...")
            
            # Converte os valores do editor para o tipo correto
            for col_val in ['VALOR_ITEM', 'VALOR_RENEGOCIADO']:
                edited_df[col_val] = edited_df[col_val].astype(str).str.replace(r'[^0-9,]+', '', regex=True).str.replace(',', '.', regex=False)
                edited_df[col_val] = pd.to_numeric(edited_df[col_val], errors='coerce').fillna(0)

            edited_df['DATA_APROVACAO'] = pd.to_datetime(edited_df['DATA_APROVACAO'], errors='coerce')
            edited_df['PREVISAO_ENTREGA'] = pd.to_datetime(edited_df['PREVISAO_ENTREGA'], errors='coerce')
            edited_df['DATA'] = pd.to_datetime(edited_df['DATA'], errors='coerce')
            
            edited_df['DIAS_EMISSAO'] = edited_df.apply(
                lambda row: (row['DATA_APROVACAO'] - row['DATA']).days if pd.notna(row['DATA_APROVACAO']) and pd.notna(row['DATA']) else 0,
                axis=1
            )
            
            for index, edited_row in edited_df.iterrows():
                original_row = pedidos_pendentes_oc.iloc[index]
                original_index = st.session_state.df_pedidos[
                    (st.session_state.df_pedidos['REQUISICAO'] == original_row['REQUISICAO']) &
                    (st.session_state.df_pedidos['MATERIAL'] == original_row['MATERIAL'])
                ].index
                
                if not original_index.empty:
                    original_index = original_index[0]
                    st.session_state.df_pedidos.loc[original_index, 'FORNECEDOR'] = edited_row['FORNECEDOR']
                    st.session_state.df_pedidos.loc[original_index, 'ORDEM_COMPRA'] = edited_row['ORDEM_COMPRA']
                    st.session_state.df_pedidos.loc[original_index, 'VALOR_ITEM'] = edited_df.loc[index, 'VALOR_ITEM']
                    st.session_state.df_pedidos.loc[original_index, 'VALOR_RENEGOCIADO'] = edited_row['VALOR_RENEGOCIADO']
                    st.session_state.df_pedidos.loc[original_index, 'PREVISAO_ENTREGA'] = edited_row['PREVISAO_ENTREGA']
                    st.session_state.df_pedidos.loc[original_index, 'DATA_APROVACAO'] = edited_row['DATA_APROVACAO']
                    st.session_state.df_pedidos.loc[original_index, 'CONDICAO_FRETE'] = edited_row['CONDICAO_FRETE']
                    st.session_state.df_pedidos.loc[original_index, 'DIAS_EMISSAO'] = edited_row['DIAS_EMISSAO']
            
            salvar_dados_pedidos(st.session_state.df_pedidos)
            st.success("Dados atualizados com sucesso!")
            st.rerun()

    elif menu == "📜 Histórico ":
        st.markdown("""
            <div class='header-container'>
                <h1>📜 HISTÓRICO E EDIÇÃO DE PEDIDOS</h1>
                <p>Gerencie e Edite os Registros Anteriores</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("📜 Histórico de Requisições e Pedidos")
        st.info("Edite os dados diretamente na tabela abaixo. As alterações serão salvas automaticamente.")
        
        df_history = st.session_state.df_pedidos.copy()
        
        df_history['DATA'] = pd.to_datetime(df_history['DATA'], errors='coerce', dayfirst=True)
        
        df_history['VALOR_TOTAL'] = df_history['QUANTIDADE'] * df_history['VALOR_ITEM']
        df_history['VALOR_TOTAL'] = df_history['VALOR_TOTAL'].round(2)

        df_almox = st.session_state.df_almoxarifado.copy()
        if not df_almox.empty:
            df_history = pd.merge(df_history, df_almox[['ORDEM_COMPRA', 'DOC NF']], on='ORDEM_COMPRA', how='left', suffixes=('', '_almox'))
            df_history['DOC NF'] = df_history['DOC NF_almox'].fillna(df_history['DOC NF'])
            df_history.drop(columns=['DOC NF_almox'], inplace=True, errors='ignore')

        df_valid_dates = df_history.dropna(subset=['DATA'])
        
        if not df_valid_dates.empty:
            meses_disponiveis = df_valid_dates['DATA'].dt.month.unique()
            anos_disponiveis = df_valid_dates['DATA'].dt.year.unique()
            
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            
            col_filter_row1_1, col_filter_row1_2, col_filter_row1_3, col_filter_row1_4 = st.columns(4)
            col_filter_row2_1, col_filter_row2_2, col_filter_row2_3 = st.columns(3)

            with col_filter_row1_1:
                mes_selecionado_h = st.selectbox("Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x))
            with col_filter_row1_2:
                ano_selecionado_h = st.selectbox("Ano", sorted(anos_disponiveis, reverse=True))
            with col_filter_row1_3:
                status_options = ['Todos'] + sorted(df_history['STATUS_PEDIDO'].unique().tolist())
                status_selecionado_h = st.selectbox("Status", status_options)
            with col_filter_row1_4:
                solicitantes_disponiveis = ['Todos'] + sorted(df_history['SOLICITANTE'].unique().tolist())
                solicitante_selecionado_h = st.selectbox("Solicitante", solicitantes_disponiveis)
                
            with col_filter_row2_1:
                req_filter = st.text_input("N° Requisição")
            with col_filter_row2_2:
                oc_filter = st.text_input("N° Ordem de Compra")
            with col_filter_row2_3:
                cod_material_filter = st.text_input("Código Material")
            
            df_history = df_history[(df_history['DATA'].dt.month == mes_selecionado_h) & (df_history['DATA'].dt.year == ano_selecionado_h)]
        else:
            st.info("Nenhum dado com data válida para filtragem. Por favor, registre uma requisição primeiro.")
            st.stop()
        
        if status_selecionado_h != 'Todos':
            df_history = df_history[df_history['STATUS_PEDIDO'] == status_selecionado_h]
        if solicitante_selecionado_h != 'Todos':
            df_history = df_history[df_history['SOLICITANTE'] == solicitante_selecionado_h]
        if req_filter:
            df_history = df_history[df_history['REQUISICAO'].str.contains(req_filter, case=False, na=False)]
        if oc_filter:
            df_history = df_history[df_history['ORDEM_COMPRA'].str.contains(oc_filter, case=False, na=False)]
        if cod_material_filter:
            df_history = df_history[df_history['CODIGO_MATERIAL'].str.contains(cod_material_filter, case=False, na=False)]

        if df_history.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            st.stop()
        
        df_display = df_history.copy()

        def formatar_status_display(status):
            if status == 'ENTREGUE':
                return '🟢 ENTREGUE'
            elif status == 'PENDENTE':
                return '🟡 PENDENTE'
            else:
                return 'EM ANDAMENTO'
        
        df_display['STATUS_PEDIDO'] = df_display['STATUS_PEDIDO'].apply(formatar_status_display)
        
        data_cols_history = ['DATA', 'DATA_APROVACAO', 'PREVISAO_ENTREGA', 'DATA_ENTREGA']
        for col in data_cols_history:
            if col in df_display.columns:
                df_display[col] = pd.to_datetime(df_display[col], errors='coerce').dt.date

        # Adiciona o link para o DOC NF
        df_display['DOC NF'] = df_display['DOC NF'].apply(
            lambda x: f"[📥 Anexo]({x})" if x and x.startswith('http') else 'Não Anexado'
        )

        edited_history_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=False,
            key='history_editor',
            column_config={
                "STATUS_PEDIDO": st.column_config.SelectboxColumn("Status", options=['🟢 ENTREGUE', '🟡 PENDENTE', 'EM ANDAMENTO']),
                "REQUISICAO": st.column_config.TextColumn("N° Requisição", disabled=True),
                "DATA": st.column_config.DateColumn("Data Requisição", format="DD/MM/YYYY", disabled=True),
                "SOLICITANTE": st.column_config.TextColumn("Solicitante", disabled=True),
                "DEPARTAMENTO": "Departamento",
                "FILIAL": "Filial",
                "CODIGO_MATERIAL": st.column_config.TextColumn("Cód. Material", disabled=True),
                "MATERIAL": st.column_config.TextColumn("Material", disabled=True),
                "UN": st.column_config.TextColumn("UN", disabled=True),
                "QUANTIDADE": st.column_config.NumberColumn("Quantidade", format="%d", disabled=True),
                "TIPO_PEDIDO": st.column_config.SelectboxColumn("Tipo de Pedido", options=["LOCAL", "EMERGENCIAL", "PROGRAMADO"]),
                "FORNECEDOR": st.column_config.TextColumn("Fornecedor"),
                "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                "VALOR_ITEM": st.column_config.NumberColumn("Valor Unitário (R$)", format="R$ %.2f"),
                "VALOR_TOTAL": st.column_config.NumberColumn("Valor Total (R$)", format="R$ %.2f", disabled=True),
                "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado (R$)", format="R$ %.2f"),
                "PREVISAO_ENTREGA": st.column_config.DateColumn("Previsão de Entrega", format="DD/MM/YYYY"),
                "DATA_APROVACAO": st.column_config.DateColumn("Data Aprovação", format="DD/MM/YYYY"),
                "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB"]),
                "DATA_ENTREGA": st.column_config.DateColumn("Data Entrega", format="DD/MM/YYYY"),
                "DIAS_ATRASO": "Dias Atraso",
                "DOC NF": "Anexo NF"
            },
            column_order=[
                "STATUS_PEDIDO", "REQUISICAO", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "CODIGO_MATERIAL", "MATERIAL", "UN", "QUANTIDADE",
                "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_TOTAL", "VALOR_RENEGOCIADO", "DATA", "DATA_APROVACAO",
                "PREVISAO_ENTREGA", "CONDICAO_FRETE", "DATA_ENTREGA", "DIAS_ATRASO", "DOC NF"
            ]
        )

        if not edited_history_df.equals(df_display):
            st.info("Salvando alterações...")
            
            edited_history_df['STATUS_PEDIDO'] = edited_history_df['STATUS_PEDIDO'].map({
                '🟢 ENTREGUE': 'ENTREGUE',
                '🟡 PENDENTE': 'PENDENTE',
                'EM ANDAMENTO': 'EM ANDAMENTO'
            }).fillna(edited_history_df['STATUS_PEDIDO'])
            
            for col_val in ['VALOR_ITEM', 'VALOR_RENEGOCIADO']:
                edited_history_df[col_val] = edited_history_df[col_val].astype(str).str.replace(r'[^0-9,]+', '', regex=True).str.replace(',', '.', regex=False)
                edited_history_df[col_val] = pd.to_numeric(edited_history_df[col_val], errors='coerce').fillna(0).round(2)
            
            edited_history_df['DATA_APROVACAO'] = pd.to_datetime(edited_history_df['DATA_APROVACAO'], errors='coerce')
            edited_history_df['DATA_ENTREGA'] = pd.to_datetime(edited_history_df['DATA_ENTREGA'], errors='coerce')
            edited_history_df['PREVISAO_ENTREGA'] = pd.to_datetime(edited_history_df['PREVISAO_ENTREGA'], errors='coerce')
            edited_history_df['DATA'] = pd.to_datetime(edited_history_df['DATA'], errors='coerce')

            def calcular_dias_atraso(row):
                if pd.notna(row['DATA_ENTREGA']) and pd.notna(row['PREVISAO_ENTREGA']):
                    if row['DATA_ENTREGA'] > row['PREVISAO_ENTREGA']:
                        return (row['DATA_ENTREGA'] - row['PREVISAO_ENTREGA']).days
                return 0

            edited_history_df['DIAS_ATRASO'] = edited_history_df.apply(calcular_dias_atraso, axis=1)

            for col in edited_history_df.columns:
                if col in st.session_state.df_pedidos.columns:
                    st.session_state.df_pedidos.loc[edited_history_df.index, col] = edited_history_df[col]
            
            salvar_dados_pedidos(st.session_state.df_pedidos)
            st.success("Histórico atualizado com sucesso!")
            st.rerun()

        st.markdown("---")
        st.subheader("💰 Resumo do Custo Total")
        total_historico = df_history['VALOR_TOTAL'].sum()
        st.metric(label="Custo Total no Período Selecionado", value=f"R$ {total_historico:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    elif menu == "👤 Cadastro ":
        st.markdown("""
            <div class='header-container'>
                <h1>👤 CADASTRO</h1>
                <p>Adicione novos Solicitantes e Materiais ao Sistema</p>
            </div>
        """, unsafe_allow_html=True)
        
        col_solicitante, col_material = st.columns(2)

        with col_solicitante:
            st.subheader("➕ Cadastro de Solicitante")
            st.info("Cadastre os solicitantes para que eles possam ser selecionados nas requisições.")
            with st.form("form_solicitante"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    nome = st.text_input("Nome do Solicitante")
                with col2:
                    departamento = st.text_input("Departamento")
                with col3:
                    filial = st.text_input("Filial")
                email = st.text_input("E-mail")
                
                if st.form_submit_button("Cadastrar Solicitante"):
                    if nome and departamento and filial and email:
                        novo_solicitante = pd.DataFrame([{
                            "NOME": nome.upper(),
                            "DEPARTAMENTO": departamento.upper(),
                            "EMAIL": email,
                            "FILIAL": filial.upper()
                        }])
                        st.session_state.df_solicitantes = pd.concat([st.session_state.df_solicitantes, novo_solicitante], ignore_index=True)
                        salvar_dados_solicitantes(st.session_state.df_solicitantes)
                        st.success(f"Solicitante '{nome}' cadastrado com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos para cadastrar o solicitante.")
        
        with col_material:
            st.subheader("➕ Cadastro de Material")
            st.info("Cadastre os materiais para que eles sejam preenchidos automaticamente na requisição.")
            
            col_manual, col_upload = st.columns(2)
            with col_manual:
                with st.form("form_material_individual"):
                    codigo = st.text_input("Código do Material")
                    descricao = st.text_input("Descrição do Material")
                    
                    if st.form_submit_button("Cadastrar Material"):
                        if codigo and descricao:
                            novo_material = pd.DataFrame([{"CODIGO": codigo.upper(), "DESCRICAO": descricao.upper()}])
                            st.session_state.df_materiais = pd.concat([st.session_state.df_materiais, novo_material], ignore_index=True)
                            salvar_dados_materiais(st.session_state.df_materiais)
                            st.success(f"Material '{descricao}' (Cód: {codigo}) cadastrado com sucesso!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Por favor, preencha o código e a descrição do material.")
            
            with col_upload:
                st.subheader("⬆️ Cadastro em Lote")
                st.info("Envie um arquivo .csv ou .xlsx com as colunas `CODIGO` e `DESCRICAO` para cadastrar vários materiais de uma vez.")
                uploaded_file = st.file_uploader("Escolha um arquivo para upload", type=["csv", "xlsx"])
                
                if uploaded_file:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df_novos_materiais = pd.read_csv(uploaded_file)
                        else:
                            df_novos_materiais = pd.read_excel(uploaded_file)
                        
                        df_novos_materiais.columns = [col.upper().strip() for col in df_novos_materiais.columns]

                        if 'CODIGO' not in df_novos_materiais.columns or 'DESCRICAO' not in df_novos_materiais.columns:
                            st.error("O arquivo deve conter as colunas 'CODIGO' e 'DESCRICAO'.")
                        else:
                            df_novos_materiais = df_novos_materiais.fillna('')
                            df_novos_materiais['CODIGO'] = df_novos_materiais['CODIGO'].astype(str).str.upper()
                            df_novos_materiais['DESCRICAO'] = df_novos_materiais['DESCRICAO'].astype(str).str.upper()

                            st.session_state.df_materiais = pd.concat([st.session_state.df_materiais, df_novos_materiais], ignore_index=True)
                            st.session_state.df_materiais.drop_duplicates(subset=['CODIGO'], inplace=True, ignore_index=True)
                            
                            salvar_dados_materiais(st.session_state.df_materiais)
                            st.success(f"Cadastro em lote concluído! Foram adicionados {len(df_novos_materiais)} novos materiais.")
                            st.balloons()
                            time.sleep(3)
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

    elif menu == "📊 Dashboards ":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 DASHBOARD DE DESEMPENHO</h1>
                <p>Análise de Prazos e Custos de Pedidos</p>
            </div>
        """, unsafe_allow_html=True)

        st.header("📊 Análise de Desempenho de Entregas")
        
        if st.session_state.df_pedidos.empty:
            st.info("Nenhum pedido registrado para análise.")
            st.stop()

        df_analise = st.session_state.df_pedidos.copy()
        df_analise['DATA'] = pd.to_datetime(df_analise['DATA'], errors='coerce', dayfirst=True)
        
        st.subheader("Filtros de Período")
        col_filtro1, col_filtro2 = st.columns(2)
        
        if not df_analise['DATA'].isnull().all():
            meses_disponiveis = df_analise['DATA'].dt.month.unique()
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            with col_filtro1:
                mes_selecionado = st.multiselect("Selecione o Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis))
            with col_filtro2:
                anos_disponiveis = df_analise['DATA'].dt.year.unique()
                ano_selecionado = st.selectbox("Selecione o Ano", sorted(anos_disponiveis, reverse=True))
        else:
            mes_selecionado = []
            ano_selecionado = None
            st.info("Nenhum dado com data válida para filtragem.")
            st.stop()

        if mes_selecionado and ano_selecionado:
            df_filtrado_dash = df_analise[(df_analise['DATA'].dt.month.isin(mes_selecionado)) & (df_analise['DATA'].dt.year == ano_selecionado)]
        else:
            df_filtrado_dash = pd.DataFrame()
        
        if df_filtrado_dash.empty:
            st.warning("Nenhum dado disponível para o período selecionado.")
            st.stop()
        
        df_filtrado_dash['VALOR_TOTAL'] = df_filtrado_dash['QUANTIDADE'] * df_filtrado_dash['VALOR_ITEM']
        
        st.subheader("Visão Geral")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_pedidos = len(df_filtrado_dash)
            st.metric("Total de Pedidos", total_pedidos)
        with col2:
            pedidos_pendentes = len(df_filtrado_dash[df_filtrado_dash['STATUS_PEDIDO'] == 'PENDENTE'])
            st.metric("Pedidos Pendentes", pedidos_pendentes)
        with col3:
            valor_total = df_filtrado_dash['VALOR_TOTAL'].sum()
            st.metric("Valor Total dos Itens", f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with col4:
            media_atraso = df_filtrado_dash['DIAS_ATRASO'].mean() if not df_filtrado_dash.empty else 0
            st.metric("Média de Dias de Atraso", f"{media_atraso:.1f} dias")

        st.subheader("Análise de Pedidos com Atraso de Entrega")
        pedidos_atrasados = df_filtrado_dash[df_filtrado_dash['DIAS_ATRASO'] > 0]
        
        if not pedidos_atrasados.empty:
            fig_atraso = px.bar(
                pedidos_atrasados.groupby('FORNECEDOR')['DIAS_ATRASO'].sum().reset_index().nlargest(10, 'DIAS_ATRASO'),
                x='FORNECEDOR',
                y='DIAS_ATRASO',
                title='Top 10 Fornecedores com Mais Dias de Atraso de Entrega',
                labels={'DIAS_ATRASO': 'Total de Dias de Atraso', 'FORNECEDOR': 'Fornecedor'}
            )
            st.plotly_chart(fig_atraso, use_container_width=True)
        else:
            st.info("Nenhum pedido com atraso de entrega registrado no período.")

        st.subheader("Custo Total por Departamento")
        pedidos_com_custo = df_filtrado_dash[df_filtrado_dash['DEPARTAMENTO'].notna() & (df_filtrado_dash['VALOR_TOTAL'] > 0)]
        
        if not pedidos_com_custo.empty:
            custo_por_departamento = pedidos_com_custo.groupby('DEPARTAMENTO')['VALOR_TOTAL'].sum().sort_values(ascending=False).reset_index()
            custo_por_departamento.columns = ['Departamento', 'Custo Total']
            
            fig_custo = px.bar(
                custo_por_departamento,
                x='Custo Total',
                y='Departamento',
                orientation='h',
                title='Custo Total de Pedidos por Departamento',
                labels={'Custo Total': 'Custo Total (R$)', 'Departamento': 'Departamento'},
                text_auto='.2s'
            )
            st.plotly_chart(fig_custo, use_container_width=True)
        else:
            st.info("Nenhum pedido com valor e departamento registrados no período para esta análise.")
        
        st.subheader("Evolução Mensal de Pedidos e Entregas")
        
        df_com_data_aprovacao = df_filtrado_dash.dropna(subset=['DATA_APROVACAO']).copy()
        if not df_com_data_aprovacao.empty:
            df_com_data_aprovacao['MES_APROVACAO'] = df_com_data_aprovacao['DATA_APROVACAO'].dt.to_period('M').astype(str)
            mensal = df_com_data_aprovacao.groupby('MES_APROVACAO').agg(
                pedidos=('REQUISICAO', 'count'),
                entregues=('STATUS_PEDIDO', lambda x: (x == 'ENTREGUE').sum())
            ).reset_index()
            
            fig_evolucao = go.Figure()
            fig_evolucao.add_trace(go.Bar(x=mensal['MES_APROVACAO'], y=mensal['pedidos'], name='Pedidos Aprovados'))
            fig_evolucao.add_trace(go.Bar(x=mensal['MES_APROVACAO'], y=mensal['entregues'], name='Entregas Realizadas'))
            fig_evolucao.update_layout(
                title_text='Volume de Pedidos Aprovados vs. Entregas Realizadas por Mês',
                xaxis_title="Mês/Ano",
                yaxis_title="Quantidade de Pedidos"
            )
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("Não há pedidos com data de aprovação registrada no período para a análise de evolução mensal.")

        st.subheader("Ranking de Tempo de Entrega")
        df_entregues = df_filtrado_dash[df_filtrado_dash['STATUS_PEDIDO'] == 'ENTREGUE'].copy()
        
        if not df_entregues.empty:
            df_entregues['TEMPO_ENTREGA'] = (df_entregues['DATA_ENTREGA'] - df_entregues['DATA_APROVACAO']).dt.days

            ranking_fornecedores = df_entregues.groupby('FORNECEDOR')['TEMPO_ENTREGA'].mean().sort_values().reset_index()
            fig_ranking = px.bar(
                ranking_fornecedores,
                x='FORNECEDOR',
                y='TEMPO_ENTREGA',
                title='Tempo Médio de Entrega por Fornecedor (dias)',
                labels={'TEMPO_ENTREGA': 'Tempo Médio (dias)', 'FORNECEDOR': 'Fornecedor'}
            )
            st.plotly_chart(fig_ranking, use_container_width=True)
        else:
            st.info("Não há pedidos entregues no período para criar o ranking.")
        
        # --- Curva ABC ---
        st.markdown("---")
        st.header("Análise de Materiais - Curva ABC")
        
        df_abc = df_filtrado_dash.copy()

        df_abc = df_abc[df_abc['VALOR_TOTAL'] > 0]
        if df_abc.empty:
            st.info("Nenhum dado com custo total para gerar a Curva ABC.")
        else:
            custo_por_material = df_abc.groupby(['CODIGO_MATERIAL', 'MATERIAL'])['VALOR_TOTAL'].sum().reset_index()
            custo_por_material.sort_values(by='VALOR_TOTAL', ascending=False, inplace=True)
            custo_por_material.reset_index(drop=True, inplace=True)

            custo_total_geral = custo_por_material['VALOR_TOTAL'].sum()
            custo_por_material['PARTICIPACAO'] = (custo_por_material['VALOR_TOTAL'] / custo_total_geral)
            custo_por_material['PARTICIPACAO_ACUMULADA'] = custo_por_material['PARTICIPACAO'].cumsum()

            def classificar_abc(row):
                if row['PARTICIPACAO_ACUMULADA'] <= 0.8:
                    return 'A'
                elif row['PARTICIPACAO_ACUMULADA'] <= 0.95:
                    return 'B'
                else:
                    return 'C'

            custo_por_material['CLASSE'] = custo_por_material.apply(classificar_abc, axis=1)

            st.subheader("Visualização da Curva ABC")
            col_abc_1, col_abc_2 = st.columns(2)
            
            with col_abc_1:
                fig_abc = make_subplots(specs=[[{"secondary_y": True}]])

                fig_abc.add_trace(
                    go.Bar(
                        x=custo_por_material['CODIGO_MATERIAL'],
                        y=custo_por_material['VALOR_TOTAL'],
                        name='Custo Total (R$)',
                        marker_color='#1C4D86',
                    ),
                    secondary_y=False,
                )

                fig_abc.add_trace(
                    go.Scatter(
                        x=custo_por_material['CODIGO_MATERIAL'],
                        y=custo_por_material['PARTICIPACAO_ACUMULADA'],
                        name='Participação Acumulada',
                        mode='lines+markers',
                        line=dict(color='red', width=2),
                    ),
                    secondary_y=True,
                )

                fig_abc.add_hline(y=0.8, line_dash="dash", line_color="green", annotation_text="80% (Classe A)", annotation_position="bottom right")
                fig_abc.add_hline(y=0.95, line_dash="dash", line_color="orange", annotation_text="95% (Classe B)", annotation_position="bottom right")

                fig_abc.update_layout(
                    title_text="Curva ABC do Custo dos Materiais",
                    xaxis_title="Material (Código)",
                    legend_orientation="h",
                    legend_y=-0.15,
                    legend_x=0.5
                )
                fig_abc.update_yaxes(title_text="Custo Total (R$)", secondary_y=False, tickformat=',.2f')
                fig_abc.update_yaxes(title_text="Participação Acumulada", secondary_y=True, tickformat='.0%')
                
                st.plotly_chart(fig_abc, use_container_width=True)

            with col_abc_2:
                st.subheader("Resumo por Classe")
                total_custo_por_classe = custo_por_material.groupby('CLASSE')['VALOR_TOTAL'].sum().reset_index()
                total_custo_por_classe['PARTICIPACAO'] = (total_custo_por_classe['VALOR_TOTAL'] / custo_total_geral) * 100
                fig_pie = px.pie(
                    total_custo_por_classe,
                    values='VALOR_TOTAL',
                    names='CLASSE',
                    title='Distribuição de Custo por Classe ABC',
                    color_discrete_sequence=['#1C4D86', '#007ea7', '#6c757d'],
                    hole=0.4
                )
                fig_pie.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=1)))
                st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("Ranking de Materiais por Custo Total")
            st.info("Tabela com os materiais mais caros, ideal para focar as negociações.")
            st.dataframe(
                custo_por_material[['CLASSE', 'CODIGO_MATERIAL', 'MATERIAL', 'VALOR_TOTAL', 'PARTICIPACAO_ACUMULADA']],
                column_config={
                    "CLASSE": st.column_config.TextColumn("Classe"),
                    "CODIGO_MATERIAL": st.column_config.TextColumn("Cód. Material"),
                    "MATERIAL": st.column_config.TextColumn("Material"),
                    "VALOR_TOTAL": st.column_config.NumberColumn("Custo Total (R$)", format="R$ %.2f"),
                    "PARTICIPACAO_ACUMULADA": st.column_config.NumberColumn("Part. Acumulada", format="%.2%")
                },
                hide_index=True,
                use_container_width=True
            )

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
                mes_selecionado_p = st.multiselect("Selecione o Mês", sorted(meses_disponiveis_p), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis_p))
            with col_filtro_p2:
                ano_selecionado_p = st.selectbox("Selecione o Ano", sorted(anos_disponiveis_p, reverse=True))
        else:
            st.info("Nenhum pedido com data válida para análise.")
            st.stop()
        
        if mes_selecionado_p and ano_selecionado_p:
            df_performance_filtrado = df_performance[(df_performance['DATA'].dt.month.isin(mes_selecionado_p)) & (df_performance['DATA'].dt.year == ano_selecionado_p)]
        else:
            df_performance_filtrado = pd.DataFrame()
        
        if df_performance_filtrado.empty:
            st.info("Nenhum dado disponível para o período selecionado.")
            st.stop()

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
            st.metric("Total de Pedidos Locais", total_pedidos_local)
        with col2:
            media_economia = df_negociados['PERC_ECONOMIA'].mean() if 'PERC_ECONOMIA' in df_negociados.columns and not df_negociados.empty else 0
            st.metric("Média de Economia (%)", f"{media_economia:.2f}%")
        with col3:
            total_economizado = df_negociados['ECONOMIA'].sum() if 'ECONOMIA' in df_negociados.columns and not df_negociados.empty else 0
            st.metric("Total Economizado", f"R$ {total_economizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
        st.markdown("---")

        csv_performance = df_negociados.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Download Dados de Negociação",
            data=csv_performance,
            file_name=f"performance_negociacao_{'_'.join([str(m) for m in mes_selecionado_p])}-{ano_selecionado_p}.csv",
            mime="text/csv"
        )

        st.subheader("Curva de Desempenho da Negociação (Média Mensal)")
        df_negociados['MES_APROVACAO'] = pd.to_datetime(df_negociados['DATA_APROVACAO']).dt.to_period('M').astype(str)
        
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
