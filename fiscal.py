import streamlit as st
import time
import requests
from PIL import Image
from io import BytesIO

# ==============================================================================
# CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO CSS
# ==============================================================================
# Configuração da página com layout wide e ícone
st.set_page_config(page_title="Página de Login", layout="wide", page_icon="🔑")

# CSS personalizado para o tema Essencis
st.markdown(
    """
    <style>
    /* Aumenta o tamanho da fonte de todo o corpo do aplicativo */
    html, body, [data-testid="stAppViewContainer"] {
        font-size: 1.1rem;
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

    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# DADOS E FUNÇÕES DE LOGIN
# ==============================================================================
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

# ==============================================================================
# FUNÇÃO PARA CARREGAR O LOGO
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_logo(url: str):
    """Carrega logo da URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None

# URL do logo da Essencis
logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"

# ==============================================================================
# EXECUÇÃO PRINCIPAL DA PÁGINA
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # Tela de login centralizada
    st.markdown("<h1 style='text-align: center; color: #1C4D86;'>Login - Painel de Notas Fiscais</h1>", unsafe_allow_html=True)
    
    # Criar colunas para centralizar o formulário
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.image(logo_url, use_container_width=True)
        st.write("") # Espaço em branco
        
        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="seu.email@essencis.com.br")
            senha = st.text_input("Senha", type="password")
            
            st.write("") # Espaço em branco
            if st.form_submit_button("Entrar"):
                fazer_login(email, senha)
else:
    # Conteúdo da aplicação após o login
    st.success(f"Bem-vindo(a), {st.session_state['nome_colaborador']}!")
    st.write("Aqui seria o restante da sua aplicação.")
    if st.button("Logout"):
        st.session_state.logado = False
        st.rerun()
