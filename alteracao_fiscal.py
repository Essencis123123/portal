import streamlit as st
import pandas as pd
import datetime
import os
import time
import requests
from PIL import Image
from io import BytesIO
from pandas.errors import EmptyDataError
import numpy as np

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Fiscal - Edição", layout="wide", page_icon="📝")

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
        st.error("Erro ao carregar a imagem do logo")
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# Funções de carregamento e salvamento de dados
def carregar_dados():
    """Carrega os dados do arquivo CSV ou cria um novo se não existir"""
    arquivo_csv = "dados_pedidos.csv"
    
    # Variável definida fora dos blocos try/except
    colunas_necessarias = {
        "STATUS_FINANCEIRO": "N/A",
        "CONDICAO_PROBLEMA": "N/A",
        "REGISTRO_ADICIONAL": "",
        "VALOR_JUROS": 0.0,
        "DIAS_ATRASO": 0,
        "VALOR_FRETE": 0.0,
        "DOC NF": ""
    }

    if os.path.exists(arquivo_csv):
        try:
            df = pd.read_csv(arquivo_csv)
            # Converter colunas de data
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)
            if 'VENCIMENTO' in df.columns:
                df['VENCIMENTO'] = pd.to_datetime(df['VENCIMENTO'], errors='coerce', dayfirst=True)
            else:
                df['VENCIMENTO'] = pd.NaT
            
            # Garantir que colunas importantes existam
            for col, default_val in colunas_necessarias.items():
                if col not in df.columns:
                    df[col] = default_val
            
            return df
        except pd.errors.EmptyDataError:
            st.warning("O arquivo de dados existe, mas está vazio. Adicione dados pelo Painel do Almoxarifado.")
            return pd.DataFrame(columns=list(colunas_necessarias.keys()))
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {e}")
            return pd.DataFrame(columns=list(colunas_necessarias.keys()))
    else:
        return pd.DataFrame(columns=list(colunas_necessarias.keys()))

def salvar_dados(df):
    """Salva o DataFrame no arquivo CSV"""
    try:
        df_to_save = df.copy()
        for col in ['DATA', 'VENCIMENTO']:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
            
        df_to_save.to_csv("dados_pedidos.csv", index=False, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False

# --- Lógica de Login (UNIFICADA) ---
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
        time.sleep(1)
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# --- INICIALIZAÇÃO E LAYOUT DA PÁGINA ---

if 'logado' not in st.session_state or not st.session_state.logado:
    st.title("Login - Painel Fiscal")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    if 'df_fiscal' not in st.session_state:
        st.session_state.df_fiscal = carregar_dados()
    
    df_fiscal = st.session_state.df_fiscal

    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        
        st.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")
        st.title("💼 Menu Fiscal")
        st.divider()
        st.caption("Alterações salvas automaticamente.")
        if st.button("Logout"):
            st.session_state.logado = False
            st.rerun()

    st.markdown("""
        <div class='header-container'>
            <h1>📝 EDIÇÃO DE INFORMAÇÕES FISCAIS</h1>
            <p>Faça alterações diretamente nos dados das notas fiscais</p>
        </div>
    """, unsafe_allow_html=True)

    if df_fiscal.empty:
        st.info("Nenhuma nota fiscal registrada no sistema para edição.")
        st.stop()
    
    st.subheader("🔍 Filtros")
    col1, col2 = st.columns(2)
    with col1:
        fornecedores_disponiveis = ['Todos'] + sorted(df_fiscal['FORNECEDOR'].dropna().unique().tolist())
        filtro_fornecedor = st.selectbox("Filtrar por Fornecedor", options=fornecedores_disponiveis)
    with col2:
        status_options = ['Todos'] + sorted(df_fiscal['STATUS_FINANCEIRO'].dropna().unique().tolist())
        filtro_status = st.selectbox("Filtrar por Status", options=status_options)

    df_filtrado = df_fiscal.copy()
    if filtro_fornecedor != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['FORNECEDOR'] == filtro_fornecedor]
    if filtro_status != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['STATUS_FINANCEIRO'] == filtro_status]
        
    if df_filtrado.empty:
        st.warning("Nenhuma nota fiscal encontrada com os filtros aplicados.")
        st.stop()

    st.markdown("---")
    st.subheader("📋 Tabela de Edição de Notas Fiscais")
    st.info("Edite os campos diretamente na tabela. As alterações são salvas automaticamente.")

    edited_df = st.data_editor(
        df_filtrado,
        use_container_width=True,
        column_config={
            "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
            "FORNECEDOR": "Fornecedor",
            "NF": "N° NF",
            "PEDIDO": "N° Pedido",
            "V. TOTAL NF": st.column_config.NumberColumn("V. Total NF (R$)", format="%.2f", disabled=True),
            "VENCIMENTO": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
            "STATUS_FINANCEIRO": st.column_config.SelectboxColumn("Status Fiscal", options=["EM ANDAMENTO", "FINALIZADO", "NF PROBLEMA"]),
            "CONDICAO_PROBLEMA": st.column_config.SelectboxColumn("Problema", options=["N/A", "SEM PEDIDO", "VALOR INCORRETO", "OUTRO"]),
            "REGISTRO_ADICIONAL": "Observação",
            "VALOR_JUROS": st.column_config.NumberColumn("Juros (R$)", format="%.2f", disabled=True),
            "VALOR_FRETE": st.column_config.NumberColumn("Frete (R$)", format="%.2f", disabled=True),
            "DOC NF": st.column_config.LinkColumn("DOC NF", display_text="📥")
        }
    )

    if not edited_df.equals(df_filtrado):
        st.info("Salvando alterações...")
        st.session_state.df_fiscal.update(edited_df)
        if salvar_dados(st.session_state.df_fiscal):
            st.success("Alterações salvas com sucesso!")
            time.sleep(1)
            st.rerun()