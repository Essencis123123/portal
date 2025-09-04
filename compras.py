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
from google.oauth2.service_account import Credentials

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

# Carregar a imagem do logo a partir da URL
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- Funções de Carregamento e Salvamento de Dados ---

def carregar_dados_pedidos():
    """Carrega o DataFrame de pedidos do Google Sheets."""
    try:
        # Configuração das credenciais (usando st.secrets para segurança)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # Abre a planilha pelo ID
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0) # Pega a primeira aba
        
        # Lê os dados
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Garante que as colunas de data sejam do tipo datetime
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
            if col in df.columns and not df[col].empty:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # Garante que as colunas numéricas tenham o tipo correto
        for col in ['QUANTIDADE', 'VALOR_ITEM', 'VALOR_RENEGOCIADO', 'DIAS_ATRASO', 'DIAS_EMISSAO']:
            if col in df.columns and not df[col].empty:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Garante que colunas importantes existam, se o arquivo estiver vazio
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ""
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        st.info("Criando um DataFrame vazio. Verifique suas credenciais e a planilha.")
        return criar_dataframe_pedidos_vazio()

def criar_dataframe_pedidos_vazio():
    """Cria um DataFrame de pedidos vazio com a estrutura correta."""
    return pd.DataFrame(columns=[
        "DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "TIPO_PEDIDO",
        "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO",
        "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", "DIAS_ATRASO", "DIAS_EMISSAO", "DOC NF"
    ])

def salvar_dados_pedidos(df):
    """Salva o DataFrame de pedidos no Google Sheets."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(0)

        # Prepara o DataFrame para salvar, convertendo datas para string
        df_to_save = df.copy()
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
                )
        
        # Converte o DataFrame para uma lista de listas para salvar
        data_to_write = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        
        # Limpa o conteúdo da planilha e atualiza com os novos dados
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        
        st.success("Dados salvos na planilha com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")

# Adicionado para carregar dados do almoxarifado
def carregar_dados_almoxarifado():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(2)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Reordena e limpa as colunas para evitar KeyErrors
        ordem_colunas = ['ORDEM_COMPRA', 'DOC NF']
        df = df.reindex(columns=ordem_colunas)
        
        return df
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar dados do Almoxarifado para preencher a nota fiscal. Verifique a aba 'Almoxarifado' da planilha. {e}")
        return pd.DataFrame(columns=['ORDEM_COMPRA', 'DOC NF'])

def carregar_dados_solicitantes():
    """Carrega o DataFrame de solicitantes do Google Sheets."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(1) # Pega a segunda aba (índice 1)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de solicitantes do Google Sheets: {e}")
        return criar_dataframe_solicitantes_vazio()

def criar_dataframe_solicitantes_vazio():
    """Cria um DataFrame de solicitantes vazio."""
    return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])

def salvar_dados_solicitantes(df):
    """Salva o DataFrame de solicitantes no Google Sheets."""
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
        worksheet = spreadsheet.get_worksheet(1) # Pega a segunda aba (índice 1)

        data_to_write = [df.columns.values.tolist()] + df.values.tolist()
        
        # Limpa o conteúdo da planilha e atualiza com os novos dados
        worksheet.clear()
        worksheet.update(data_to_write, value_input_option='USER_ENTERED')
        
        st.success("Solicitante cadastrado na planilha com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar dados de solicitantes no Google Sheets: {e}")

# --- LÓGICA DE LOGIN (SEM INTEGRAÇÃO COM SMTP) ---
USERS = {
    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},
    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},
    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAULA SOARES"},
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

# --- INICIALIZAÇÃO E LAYOUT DA PÁGINA ---
if 'logado' not in st.session_state or not st.session_state.logado:
    st.title("Login - Painel do Comprador")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    # A lógica para carregar dados foi movida para as funções acima
    if 'df_pedidos' not in st.session_state:
        st.session_state.df_pedidos = carregar_dados_pedidos()
    if 'df_solicitantes' not in st.session_state:
        st.session_state.df_solicitantes = carregar_dados_solicitantes()
    if 'itens_requisicao_temp' not in st.session_state:
        st.session_state.itens_requisicao_temp = pd.DataFrame(columns=["MATERIAL", "QUANTIDADE"])
    if 'df_almoxarifado' not in st.session_state: # Adicionado o carregamento do df_almoxarifado
        st.session_state.df_almoxarifado = carregar_dados_almoxarifado()

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
        solicitante_selecionado = st.selectbox("Selecione o Solicitante", solicitantes_nomes)
        
        departamento_selecionado = ""
        filial_selecionada = ""
        if solicitante_selecionado:
            solicitante_info = st.session_state.df_solicitantes[st.session_state.df_solicitantes['NOME'] == solicitante_selecionado].iloc[0]
            departamento_selecionado = solicitante_info['DEPARTAMENTO']
            filial_selecionada = solicitante_info['FILIAL']

        col1, col2 = st.columns(2)
        with col1:
            data_requisicao = st.date_input("Data da Requisição", datetime.date.today())
            st.text_input("Departamento", value=departamento_selecionado, disabled=True)
            st.text_input("Filial", value=filial_selecionada, disabled=True)
            tipo_pedido = st.selectbox("Tipo de Pedido", ["LOCAL", "EMERGENCIAL", "PROGRAMADO"])
        
        with col2:
            requisicao = st.text_input("Número da Requisição")

        st.markdown("---")
        st.subheader("Itens da Requisição")
        col_item1, col_item2, col_item3 = st.columns([3, 1, 1])
        with col_item1:
            item_material = st.text_input("Material", key="material_input")
        with col_item2:
            item_quantidade = st.number_input("Quantidade", min_value=1, value=1, key="quantidade_input")
        with col_item3:
            st.markdown("##")
            if st.button("➕ Adicionar Item"):
                if item_material and item_quantidade > 0:
                    novo_item = pd.DataFrame([{"MATERIAL": item_material, "QUANTIDADE": item_quantidade}])
                    st.session_state.itens_requisicao_temp = pd.concat([st.session_state.itens_requisicao_temp, novo_item], ignore_index=True)
                    st.success("Item adicionado! Adicione mais ou finalize a requisição.")
                else:
                    st.error("Por favor, preencha o material e a quantidade.")
        
        st.write("---")
        st.subheader("Itens Adicionados")
        st.dataframe(st.session_state.itens_requisicao_temp, use_container_width=True)

        if st.button("Finalizar e Registrar Requisição"):
            if requisicao and not st.session_state.itens_requisicao_temp.empty:
                linhas_a_adicionar = []
                for _, item_row in st.session_state.itens_requisicao_temp.iterrows():
                    nova_linha = {
                        "DATA": data_requisicao,
                        "SOLICITANTE": solicitante_selecionado,
                        "DEPARTAMENTO": departamento_selecionado,
                        "FILIAL": filial_selecionada,
                        "MATERIAL": item_row["MATERIAL"],
                        "QUANTIDADE": item_row["QUANTIDADE"],
                        "TIPO_PEDIDO": tipo_pedido,
                        "REQUISICAO": requisicao,
                        "FORNECEDOR": "", "ORDEM_COMPRA": "", "VALOR_ITEM": 0.0, "VALOR_RENEGOCIADO": 0.0,
                        "DATA_APROVACAO": pd.NaT, "CONDICAO_FRETE": "",
                        "STATUS_PEDIDO": "PENDENTE", "DATA_ENTREGA": pd.NaT,
                        "DIAS_ATRASO": 0, "DIAS_EMISSAO": 0, "DOC NF": ""
                    }
                    linhas_a_adicionar.append(nova_linha)
                
                st.session_state.df_pedidos = pd.concat([st.session_state.df_pedidos, pd.DataFrame(linhas_a_adicionar)], ignore_index=True)
                salvar_dados_pedidos(st.session_state.df_pedidos)
                st.session_state.itens_requisicao_temp = pd.DataFrame(columns=["MATERIAL", "QUANTIDADE"])
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
        
        if pedidos_pendentes_oc.empty:
            st.success("🎉 Todas as requisições pendentes já foram atualizadas com uma Ordem de Compra!")
            st.stop()
        
        # Pega a nota fiscal da aba de almoxarifado
        df_almox = st.session_state.df_almoxarifado.copy()
        df_almox_oc = df_almox[['ORDEM_COMPRA', 'DOC NF']].copy()
        
        # Faz a junção com o dataframe de pedidos pendentes para preencher automaticamente o campo DOC NF
        pedidos_pendentes_oc = pedidos_pendentes_oc.merge(df_almox_oc, on='ORDEM_COMPRA', how='left', suffixes=('', '_almox'))
        pedidos_pendentes_oc['DOC NF'] = pedidos_pendentes_oc['DOC NF_almox'].fillna(pedidos_pendentes_oc['DOC NF'])
        pedidos_pendentes_oc.drop(columns=['DOC NF_almox'], inplace=True)

        cols_para_editar = [
            "REQUISICAO", "DATA", "SOLICITANTE", "MATERIAL", "QUANTIDADE",
            "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO",
            "DATA_APROVACAO", "CONDICAO_FRETE", "DOC NF"
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
                    "SOLICITANTE": "Solicitante",
                    "MATERIAL": "Material",
                    "QUANTIDADE": st.column_config.NumberColumn("Qtd.", disabled=True),
                    "FORNECEDOR": st.column_config.TextColumn("Nome Fornecedor"),
                    "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                    "VALOR_ITEM": st.column_config.NumberColumn("Valor do Item", format="%.2f"),
                    "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado", format="%.2f"),
                    "DATA_APROVACAO": st.column_config.DateColumn("Data de Aprovação"),
                    "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB"]),
                    "DOC NF": st.column_config.LinkColumn(
                        "DOC NF",
                        help="Link do anexo da Nota Fiscal.",
                        display_text="📎 Anexo"
                    )
                }
            )
            
            submitted = st.form_submit_button("Salvar Atualizações")

        if submitted:
            st.info("Detectando alterações...")
            
            edited_df['DATA_APROVACAO'] = pd.to_datetime(edited_df['DATA_APROVACAO'], errors='coerce', dayfirst=True)
            edited_df['DATA'] = pd.to_datetime(edited_df['DATA'], errors='coerce', dayfirst=True)
            
            for index, edited_row in edited_df.iterrows():
                original_index = st.session_state.df_pedidos[
                    (st.session_state.df_pedidos['REQUISICAO'] == edited_row['REQUISICAO']) & 
                    (st.session_state.df_pedidos['MATERIAL'] == edited_row['MATERIAL'])
                ].index
                
                if not original_index.empty:
                    original_index = original_index[0]
                    
                    st.session_state.df_pedidos.loc[original_index, 'FORNECEDOR'] = edited_row['FORNECEDOR']
                    st.session_state.df_pedidos.loc[original_index, 'ORDEM_COMPRA'] = edited_row['ORDEM_COMPRA']
                    st.session_state.df_pedidos.loc[original_index, 'VALOR_ITEM'] = edited_df.loc[index, 'VALOR_ITEM']
                    st.session_state.df_pedidos.loc[original_index, 'VALOR_RENEGOCIADO'] = edited_row['VALOR_RENEGOCIADO']
                    st.session_state.df_pedidos.loc[original_index, 'DATA_APROVACAO'] = edited_row['DATA_APROVACAO']
                    st.session_state.df_pedidos.loc[original_index, 'CONDICAO_FRETE'] = edited_row['CONDICAO_FRETE']
                    st.session_state.df_pedidos.loc[original_index, 'DOC NF'] = edited_row['DOC NF']
                    
                    if pd.notna(st.session_state.df_pedidos.loc[original_index, 'DATA_APROVACAO']):
                        data_requisicao = st.session_state.df_pedidos.loc[original_index, 'DATA']
                        data_aprovacao = st.session_state.df_pedidos.loc[original_index, 'DATA_APROVACAO']
                        dias_emissao = (data_aprovacao - data_requisicao).days
                        st.session_state.df_pedidos.loc[original_index, 'DIAS_EMISSAO'] = dias_emissao
                    else:
                        st.session_state.df_pedidos.loc[original_index, 'DIAS_EMISSAO'] = 0
            
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
        
        col_filter_h1, col_filter_h2, col_filter_h3, col_filter_h4 = st.columns(4)
        
        df_history = st.session_state.df_pedidos.copy()

        # Adição da correção: Converte a coluna 'DATA' para o tipo datetime
        df_history['DATA'] = pd.to_datetime(df_history['DATA'], errors='coerce', dayfirst=True)

        if not df_history['DATA'].isnull().all():
            with col_filter_h1:
                meses_disponiveis = df_history['DATA'].dt.month.unique()
                meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_selecionado_h = st.selectbox("Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x))
            with col_filter_h2:
                anos_disponiveis = df_history['DATA'].dt.year.unique()
                ano_selecionado_h = st.selectbox("Ano", sorted(anos_disponiveis, reverse=True))
            
            df_history = df_history[(df_history['DATA'].dt.month == mes_selecionado_h) & (df_history['DATA'].dt.year == ano_selecionado_h)]
        else:
            mes_selecionado_h = None
            ano_selecionado_h = None

        with col_filter_h3:
            solicitantes_disponiveis = ['Todos'] + df_history['SOLICITANTE'].unique().tolist()
            solicitante_selecionado_h = st.selectbox("Solicitante", solicitantes_disponiveis)
        with col_filter_h4:
            req_filter = st.text_input("N° Requisição")

        if solicitante_selecionado_h != 'Todos':
            df_history = df_history[df_history['SOLICITANTE'] == solicitante_selecionado_h]
        if req_filter:
            df_history = df_history[df_history['REQUISICAO'].str.contains(req_filter, case=False, na=False)]

        if df_history.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            st.stop()
        
        edited_history_df = st.data_editor(
            df_history,
            use_container_width=True,
            hide_index=False,
            column_config={
                "DATA": st.column_config.DateColumn("Data Requisição"),
                "SOLICITANTE": "Solicitante",
                "DEPARTAMENTO": "Departamento",
                "FILIAL": "Filial",
                "MATERIAL": "Material",
                "QUANTIDADE": "Quantidade",
                "TIPO_PEDIDO": st.column_config.SelectboxColumn("Tipo de Pedido", options=["LOCAL", "EMERGENCIAL", "PROGRAMADO"]),
                "REQUISICAO": "N° Requisição",
                "FORNECEDOR": st.column_config.TextColumn("Fornecedor"),
                "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                "VALOR_ITEM": st.column_config.NumberColumn("Valor do Item", format="%.2f"),
                "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado", format="%.2f"),
                "DATA_APROVACAO": st.column_config.DateColumn("Data Aprovação"),
                "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB"]),
                "STATUS_PEDIDO": st.column_config.SelectboxColumn("Status", options=["PENDENTE", "ENTREGUE"]),
                "DATA_ENTREGA": st.column_config.DateColumn("Data Entrega"),
                "DIAS_ATRASO": "Dias Atraso",
                "DIAS_EMISSAO": "Dias Emissão",
                "DOC NF": st.column_config.LinkColumn("Anexo NF", display_text="📥 Anexo")
            }
        )

        if not edited_history_df.equals(df_history):
            st.info("Salvando alterações...")
            
            for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
                edited_history_df[col] = pd.to_datetime(edited_history_df[col], errors='coerce', dayfirst=True)

            st.session_state.df_pedidos.update(edited_history_df)
            
            for index, row in edited_history_df.iterrows():
                if pd.notna(row['DATA_APROVACAO']) and pd.notna(row['DATA']):
                    dias_emissao = (row['DATA_APROVACAO'] - row['DATA']).days
                    st.session_state.df_pedidos.loc[index, 'DIAS_EMISSAO'] = dias_emissao
                else:
                    st.session_state.df_pedidos.loc[index, 'DIAS_EMISSAO'] = 0

                if pd.notna(row['DATA_ENTREGA']) and pd.notna(row['DATA_APROVACAO']):
                    data_limite = row['DATA_APROVACAO'] + pd.Timedelta(days=15)
                    if row['DATA_ENTREGA'] > data_limite:
                        dias_atraso = (row['DATA_ENTREGA'] - data_limite).days
                        st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = dias_atraso
                    else:
                        st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = 0
                else:
                    st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = 0

            salvar_dados_pedidos(st.session_state.df_pedidos)
            st.success("Histórico atualizado com sucesso!")
            st.rerun()

    elif menu == "👤 Cadastro ":
        st.markdown("""
            <div class='header-container'>
                <h1>👤 CADASTRO DE SOLICITANTES</h1>
                <p>Adicione novos Solicitantes ao Sistema</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("➕ Cadastro de Solicitante")
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
            
            if st.form_submit_button("Cadastrar"):
                if nome and departamento and filial and email:
                    novo_solicitante = pd.DataFrame([{
                        "NOME": nome,
                        "DEPARTAMENTO": departamento,
                        "EMAIL": email,
                        "FILIAL": filial
                    }])
                    st.session_state.df_solicitantes = pd.concat([st.session_state.df_solicitantes, novo_solicitante], ignore_index=True)
                    salvar_dados_solicitantes(st.session_state.df_solicitantes)
                    st.success(f"Solicitante '{nome}' cadastrado com sucesso!")
                    time.sleep(2) # Pausa para exibir a mensagem de sucesso
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos para cadastrar o solicitante.")

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
        
        # Garante que a coluna 'DATA' está no formato de data antes de ser usada.
        df_analise['DATA'] = pd.to_datetime(df_analise['DATA'], errors='coerce', dayfirst=True)
        
        st.subheader("Filtros de Período")
        col_filtro1, col_filtro2 = st.columns(2)
        
        if not df_analise['DATA'].isnull().all():
            meses_disponiveis = df_analise['DATA'].dt.month.unique()
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            mes_selecionado = col_filtro1.multiselect("Selecione o Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis))
        else:
            mes_selecionado = []
        
        if not df_analise['DATA'].isnull().all():
            anos_disponiveis = df_analise['DATA'].dt.year.unique()
            ano_selecionado = col_filtro2.selectbox("Selecione o Ano", sorted(anos_disponiveis, reverse=True))
        else:
            ano_selecionado = None

        if mes_selecionado and ano_selecionado:
            df_filtrado_dash = df_analise[(df_analise['DATA'].dt.month.isin(mes_selecionado)) & (df_analise['DATA'].dt.year == ano_selecionado)]
        else:
            df_filtrado_dash = pd.DataFrame()
        
        if df_filtrado_dash.empty:
            st.warning("Nenhum dado disponível para o período selecionado.")
            st.stop()

        st.subheader("Visão Geral")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_pedidos = len(df_filtrado_dash)
            st.markdown(f"### {total_pedidos}")
            st.markdown("Total de Pedidos")
        with col2:
            pedidos_pendentes = len(df_filtrado_dash[df_filtrado_dash['STATUS_PEDIDO'] == 'PENDENTE'])
            st.markdown(f"### {pedidos_pendentes}")
            st.markdown("Pedidos Pendentes")
        with col3:
            valor_total = df_filtrado_dash['VALOR_ITEM'].sum()
            st.markdown(f"### R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown("Valor Total dos Itens")
        with col4:
            media_atraso = df_filtrado_dash['DIAS_ATRASO'].mean() if not df_filtrado_dash.empty else 0
            st.markdown(f"### {media_atraso:.1f}")
            st.markdown("Média de Dias de Atraso")

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
        pedidos_com_custo = df_filtrado_dash[df_filtrado_dash['DEPARTAMENTO'].notna() & (df_filtrado_dash['VALOR_ITEM'] > 0)]
        
        if not pedidos_com_custo.empty:
            custo_por_departamento = pedidos_com_custo.groupby('DEPARTAMENTO')['VALOR_ITEM'].sum().sort_values(ascending=False).reset_index()
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
        
        df_com_data_aprovacao = df_filtrado_dash.dropna(subset=['DATA_APROVACAO'])
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

    elif menu == "📊 Performance ":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 PERFORMANCE DE NEGOCIAÇÃO LOCAL</h1>
                <p>Análise de Economia em Pedidos Locais</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("📊 Análise de Performance de Negociações Locais")

        df_performance = st.session_state.df_pedidos.copy()
        
        df_performance_local = df_performance[df_performance['TIPO_PEDIDO'] == 'LOCAL'].copy()
        
        # Garante que a coluna 'DATA' está no formato de data antes de ser usada.
        df_performance_local['DATA'] = pd.to_datetime(df_performance_local['DATA'], errors='coerce', dayfirst=True)
        
        st.markdown("---")
        st.subheader("Filtros de Período")
        col_filtro_p1, col_filtro_p2 = st.columns(2)
        
        mes_selecionado_p = []
        ano_selecionado_p = None
        if not df_performance_local['DATA'].isnull().all():
            meses_disponiveis_p = df_performance_local['DATA'].dt.month.unique()
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            mes_selecionado_p = col_filtro_p1.multiselect("Selecione o Mês", sorted(meses_disponiveis_p), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis_p))
        
        if not df_performance_local['DATA'].isnull().all():
            anos_disponiveis_p = df_performance_local['DATA'].dt.year.unique()
            ano_selecionado_p = col_filtro_p2.selectbox("Selecione o Ano", sorted(anos_disponiveis_p, reverse=True))
        else:
            ano_selecionado_p = None

        if mes_selecionado_p and ano_selecionado_p:
            df_performance_local = df_performance_local[(df_performance_local['DATA'].dt.month.isin(mes_selecionado_p)) & (df_performance_local['DATA'].dt.year == ano_selecionado_p)]
        else:
            df_performance_local = pd.DataFrame()
        
        if df_performance_local.empty:
            st.info("Nenhum pedido local com valores de negociação preenchidos para análise.")
            st.stop()
        
        df_performance_local = df_performance_local[df_performance_local['VALOR_ITEM'].notna() & df_performance_local['VALOR_RENEGOCIADO'].notna()]
        df_performance_local = df_performance_local[df_performance_local['VALOR_ITEM'] > 0]

        if df_performance_local.empty:
            st.info("Nenhum pedido local com valores de negociação preenchidos para análise.")
            st.stop()
        
        df_performance_local['ECONOMIA'] = df_performance_local['VALOR_ITEM'] - df_performance_local['VALOR_RENEGOCIADO']
        df_performance_local['PERC_ECONOMIA'] = np.where(df_performance_local['VALOR_ITEM'] > 0, 
                                                         (df_performance_local['VALOR_ITEM'] - df_performance_local['VALOR_RENEGOCIADO']) / df_performance_local['VALOR_ITEM'] * 100, 
                                                         0)

        st.subheader("Visão Geral da Performance")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_pedidos_local = len(df_performance_local)
            st.markdown(f"### {total_pedidos_local}")
            st.markdown("Total de Pedidos Locais")
        with col2:
            media_economia = df_performance_local['PERC_ECONOMIA'].mean()
            st.markdown(f"### {media_economia:.2f}%")
            st.markdown("Média de Economia (%)")
        with col3:
            total_economizado = df_performance_local['ECONOMIA'].sum()
            st.markdown(f"### R$ {total_economizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown("Total Economizado")

        st.markdown("---")
        
        csv_performance = df_performance_local.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Download Dados da Performance",
            data=csv_performance,
            file_name=f"performance_local_{'_'.join([str(m) for m in mes_selecionado_p])}-{ano_selecionado_p}.csv",
            mime="text/csv"
        )

        st.subheader("Curva de Desempenho da Negociação (Média Mensal)")
        df_performance_local['MES_APROVACAO'] = df_performance_local['DATA_APROVACAO'].dt.to_period('M').astype(str)
        
        curva_mensal = df_performance_local.groupby('MES_APROVACAO')['PERC_ECONOMIA'].mean().reset_index()
        
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
            st.info("Dados de negociação local insuficientes para gerar a curva de desempenho.")
        
        st.markdown("---")

        st.subheader("Principais Solicitantes de Pedidos Locais")
        ranking_solicitantes = df_performance_local['SOLICITANTE'].value_counts().reset_index()
        ranking_solicitantes.columns = ['Solicitante', 'Total de Pedidos Locais']
        
        if not ranking_solicitantes.empty:
            fig_ranking = px.bar(
                ranking_solicitantes.nlargest(10, 'Total de Pedidos Locais'),
                x='Total de Pedidos Locais',
                y='Solicitante',
                orientation='h',
                title='Top 10 Solicitantes de Compras Locais',
                labels={'Total de Pedidos Locais': 'Número de Pedidos', 'Solicitante': 'Solicitante'}
            )
            st.plotly_chart(fig_ranking, use_container_width=True)
        else:
            st.info("Dados de solicitantes locais insuficientes para gerar o ranking.")
