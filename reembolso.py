import streamlit as st
import pandas as pd
import datetime
import requests
from PIL import Image
from io import BytesIO
import os
from pandas.errors import EmptyDataError
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pickle
import base64
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import re
import mimetypes
from supabase import create_client, Client
import toml
from streamlit_option_menu import option_menu
import hashlib

# --- Configuração do Layout e Tema ---
st.set_page_config(page_title="Gestão de Reembolsos", layout="wide", page_icon="💰")

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

    /* Centralizar conteúdo do formulário de login */
    .login-form-container {
        display: flex;
        flex-direction: column;
        align-items: center; /* Centraliza horizontalmente */
        justify-content: center; /* Centraliza verticalmente */
    }
    .login-form-container .stTextInput,
    .login-form-container .stButton {
        width: 70%; /* Define uma largura para os elementos */
        margin-bottom: 15px; /* Espaçamento entre os itens */
    }
    .login-form-container .stButton button {
        width: 100%; /* Faz o botão ocupar toda a largura definida */
    }
    .login-form-container .stForm {
        width: 100%; /* Garante que o formulário ocupe a largura definida */
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Funções de Utilidade ---
def hash_password(password):
    """Hash da senha usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    """Valida se o email é do domínio Essencis"""
    pattern = r'^[a-zA-Z0-9._%+-]+@essencis\.com\.br$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """Verifica se a senha é forte"""
    return (len(password) >= 8 and 
            any(c.isupper() for c in password) and
            any(c.islower() for c in password) and
            any(c.isdigit() for c in password))

def format_currency(value):
    """Formata valores monetários corretamente"""
    try:
        if isinstance(value, str):
            # Remove possíveis formatações existentes
            value = value.replace('R$', '').replace('.', '').replace(',', '.').strip()
        formatted = f"R$ {float(value):.2f}"
        # Formatação brasileira: 1.50 → R$ 1,50
        return formatted.replace('.', ',')
    except:
        return "R$ 0,00"

def parse_currency(value):
    """Converte string monetária para float"""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove R$, pontos e substitui vírgula por ponto
            value = value.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return float(value)
        return 0.0
    except:
        return 0.0

# --- Carrega a imagem do logo a partir da URL ---
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

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- Carrega os segredos do Streamlit ---
secrets_dict = st.secrets

# --- Constantes para o formulário ---
DEPARTAMENTOS = [
    "1601 - Financeiro / Administrativo",
    "1201 - Administração da Manutenção",
    "2302 - Aterro K1",
    "2303 - Aterro K2",
    "1202 - Manutenção de veículos leves",
    "1203 - Manutenção Eletromecânica",
    "1301 - Balança",
    "1302 - Laboratório",
    "1303 - Manutenção de aterros",
    "1304 - Serviços Gerais",
    "1308 - Tecnologia da Informação",
    "1401 - Comercial",
    "1502 - Comunicação",
    "1505 - Segurança do Trabalho",
    "2401 - Coprocessamento",
    "2305 - Tratamento de efluentes privados",
]

TIPOS_DESPESA = [
    "Corridas de Uber, 99 ou táxi",
    "Estacionamento e pedágios",
    "Alimentação",
    "Material de escritório (canetas, papel, clips, etc.)",
    "Boletos de inscrição (cursos, eventos, concursos)",
    "Taxas públicas (DAE, GRU, cartório, etc.)",
    "Ingressos corporativos ou institucionais",
    "Manutenção de Máquinas y Equipamentos",
    "Materiais de baixo custo (torneiras, lâmpadas, tomadas)",
    "Outros"
]

# --- Gerenciamento de Estado da Sessão ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None
if "reembolsos_temp" not in st.session_state:
    st.session_state.reembolsos_temp = []

# --- Conexão com Google Sheets e APIs ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]

# Adiciona o escopo do Gmail às permissões
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# E-mail da conta de serviço que enviará as notificações
SENDER_EMAIL = 'suprimentosessencis@gmail.com'

@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    )
    return gspread.authorize(creds)

# --- CORREÇÃO: Função get_gmail_service simplificada ---
@st.cache_resource(ttl=3600)
def get_gmail_service():
    try:
        # Use as credenciais da service account
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Use as credenciais diretamente
        return build('gmail', 'v1', credentials=creds)
        
    except Exception as e:
        st.error(f"Erro ao criar serviço Gmail: {e}")
        return None

# Instância do cliente gspread e do serviço Gmail
gs_client = get_gspread_client()
st.session_state.gmail_service = get_gmail_service()

# --- Verificação de Configuração ---
st.sidebar.write("🔧 Configuração do Sistema")
if "GMAIL_TOKEN" in st.secrets:
    st.sidebar.success("✓ GMAIL_TOKEN configurado")
else:
    st.sidebar.info("ℹ GMAIL_TOKEN não configurado - usando Service Account")

if st.session_state.gmail_service:
    st.sidebar.success("✓ Serviço Gmail conectado")
else:
    st.sidebar.warning("⚠ Serviço Gmail não disponível")

def get_reembolsos_sheet():
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Reembolsos")
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de autenticação ou acesso à planilha: {e}.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Reembolsos' não foi encontrada na planilha.")
        return None

def get_usuarios_sheet():
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Usuarios")
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Usuarios' não foi encontrada na planilha.")
        return None

# --- Funções de Envio de E-mail ---
def create_message(sender, to, subject, message_text):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    msg = MIMEText(message_text, 'html')
    message.attach(msg)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    try:
        if service is None:
            st.warning("Serviço Gmail não disponível para enviar email")
            return None
            
        message = service.users().messages().send(userId=user_id, body=message).execute()
        st.success("✅ E-mail enviado com sucesso!")
        return message
    except Exception as e:
        st.error(f"❌ Erro ao enviar e-mail: {str(e)}")
        return None

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
supabase_key = secrets_dict["supabase"]["service_role_key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

def upload_to_supabase(file_uploader, bucket_name="reembolsos-anexos"):
    if file_uploader is not None:
        try:
            file_name = file_uploader.name
            unique_file_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
            file_bytes = file_uploader.read()

            response = supabase_client.storage.from_(bucket_name).upload(
                path=unique_file_name,
                file=file_bytes,
                file_options={"content-type": file_uploader.type}
            )

            if response:
                st.success("✅ Arquivo enviado com sucesso para o Supabase!")
                return unique_file_name
            else:
                st.error("❌ Falha ao enviar o arquivo")
                return None
        except Exception as e:
            st.error(f"❌ Ocorreu um erro no upload: {str(e)}")
            return None
    return None

def get_signed_url(file_path, bucket_name="reembolsos-anexos"):
    try:
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 604800)
        if 'signedURL' in response:
            return response['signedURL']
        else:
            st.error(f"Erro ao gerar URL assinada: {response}")
            return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar gerar a URL: {e}")
        return None

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=300, show_spinner="Carregando dados...")
def load_reembolsos_data():
    sheet = get_reembolsos_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.columns.str.upper()
            if 'DATA' in df.columns:
                df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
            if 'VALOR' in df.columns:
                # Corrige a formatação dos valores
                df['VALOR'] = df['VALOR'].apply(parse_currency)
            if 'ID_COMPROVANTE' in df.columns:
                df = df.drop(columns=['ID_COMPROVANTE'])
            return df
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner="Carregando usuários...")
def load_usuarios_data():
    sheet = get_usuarios_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.columns.str.upper()
            for col in ['NOME', 'MATRICULA', 'EMAIL', 'SENHA']:
                if col not in df.columns:
                    df[col] = None
            return df
    return pd.DataFrame()

# --- CORREÇÃO: Função simplificada de envio de email ---
def send_email_simple(to_email, subject, body):
    """Função simplificada de envio de email"""
    try:
        service = st.session_state.gmail_service
        if not service:
            st.warning("Serviço Gmail não disponível")
            return False
            
        message = create_message(SENDER_EMAIL, to_email, subject, body)
        result = send_message(service, 'me', message)
        return result is not None
        
    except Exception as e:
        st.error(f"Falha no envio de email: {e}")
        return False

# --- Funções de Adicionar Reembolso e Cadastro ---
def add_reembolso(data, nome, email, departamento, tipo_despesa, valor, justificativa, id_comprovante, status="Pendente"):
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        # Formata o valor corretamente para a planilha (com vírgula)
        valor_formatado = f"{valor:.2f}".replace('.', ',')
        
        try:
            row = [data_formatada, nome, departamento, tipo_despesa, valor_formatado, justificativa, status, id_comprovante, email]
            sheet.append_row(row)
            st.success("✅ Reembolso adicionado com sucesso!")
            load_reembolsos_data.clear()

            # Tenta enviar emails usando a função simplificada
            try:
                # 1. Envia e-mail para o usuário
                subject_user = "CONFIRMAÇÃO DE ENVIO - PEDIDO DE REEMBOLSO"
                body_user = f"""
                <p>Olá, {nome}!</p>
                <p>Seu pedido de reembolso foi enviado com sucesso e está em análise.</p>
                <p><b>Detalhes do Pedido:</b></p>
                <ul>
                    <li><b>Data:</b> {data_formatada}</li>
                    <li><b>Departamento:</b> {departamento}</li>
                    <li><b>Tipo de Despesa:</b> {tipo_despesa}</li>
                    <li><b>Valor:</b> R$ {valor_formatado}</li>
                    <li><b>Justificativa:</b> {justificativa}</li>
                </ul>
                """
                comprovante_link = get_signed_url(id_comprovante) if id_comprovante else None
                if comprovante_link:
                    body_user += f"<p>Clique aqui para baixar a notinha: <a href='{comprovante_link}'>Baixar Comprovante</a></p>"
                body_user += "<p>Em breve, você receberá uma notificação sobre o status do seu pedido.</p><p>Atenciosamente,<br>Equipe de Suprimentos Essencis</p>"

                if send_email_simple(email, subject_user, body_user):
                    st.success("✅ E-mail de confirmação enviado para o usuário")
                else:
                    st.warning("⚠ Reembolso salvo, mas e-mail não enviado")

                # 2. Envia e-mail para o administrador
                admin_email = "earaujo@essencis.com.br"
                subject_admin = f"📋 Novo Reembolso Pendente de {nome}"
                body_admin = f"""
                <p>Olá, Administrador(a)!</p>
                <p>Um novo pedido de reembolso foi submetido e está aguardando sua aprovação.</p>
                <p><b>Detalhes do Reembolso:</b></p>
                <ul>
                    <li><b>Solicitante:</b> {nome}</li>
                    <li><b>E-mail:</b> {email}</li>
                    <li><b>Data:</b> {data_formatada}</li>
                    <li><b>Departamento:</b> {departamento}</li>
                    <li><b>Tipo de Despesa:</b> {tipo_despesa}</li>
                    <li><b>Valor:</b> R$ {valor_formatado}</li>
                    <li><b>Justificativa:</b> {justificativa}</li>
                </ul>
                """
                if comprovante_link:
                    body_admin += f"<p>Clique aqui para baixar o comprovante: <a href='{comprovante_link}'>Baixar Comprovante</a></p>"
                body_admin += "<p>Atenciosamente,<br>Sistema de Reembolsos Essencis</p>"

                if send_email_simple(admin_email, subject_admin, body_admin):
                    st.success("✅ E-mail de notificação enviado para o administrador")
                else:
                    st.warning("⚠ E-mail para administrador não enviado")

            except Exception as email_error:
                st.warning(f"⚠ Reembolso salvo, mas email não enviado: {str(email_error)}")

        except Exception as e:
            st.error(f"❌ Erro ao adicionar reembolso: {e}")

# --- Funções de Autenticação de Login ---
def login(email, password):
    df_usuarios = load_usuarios_data()
    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and 'SENHA' in df_usuarios.columns:
        user_exists = (df_usuarios['EMAIL'].str.lower().str.strip() == email.lower().strip()).any()

        if not user_exists:
            st.error("❌ Este e-mail não está cadastrado em nosso sistema.")
            return

        # Hash da senha fornecida
        hashed_input = hash_password(password.strip())
        
        # Verifica se há senhas em texto plano e as converte para hash
        if df_usuarios['SENHA'].str.len().max() < 64:  # Se as senhas não estão hasheadas
            df_usuarios['SENHA_HASH'] = df_usuarios['SENHA'].astype(str).apply(lambda x: hash_password(x.strip().replace("'", "")))
        else:
            df_usuarios['SENHA_HASH'] = df_usuarios['SENHA']

        user_data = df_usuarios[
            (df_usuarios['EMAIL'].str.lower().str.strip() == email.lower().strip()) &
            (df_usuarios['SENHA_HASH'] == hashed_input)
        ]

        if not user_data.empty:
            st.session_state.logged_in = True
            st.session_state.current_user = user_data.iloc[0]
            st.success("✅ Login bem-sucedido!")
            st.rerun()
        else:
            st.error("❌ Senha incorreta.")
    else:
        st.error("❌ Não foi possível carregar os dados de usuário. Verifique a planilha 'Usuarios'.")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.info("ℹ Você foi desconectado.")
    st.rerun()

# --- Layout do Aplicativo ---
st.markdown("""
    <div class='header-container'>
        <h1>💰 Gestão de Reembolsos Essencis</h1>
        <p>Sistema de Controle e Análise de Reembolsos</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)

    selected_page = option_menu(
        menu_title=None,
        options=["Login", "Cadastre-se"],
        icons=["box-arrow-in-right", "person-add"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )
    if selected_page == "Login":
        st.header("Login")
        with st.form("login_form", clear_on_submit=True):
            st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
            email_login = st.text_input("E-mail")
            password_login = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            st.markdown('</div>', unsafe_allow_html=True)
            if submitted:
                login(email_login, password_login)

    elif selected_page == "Cadastre-se":
        st.header("Cadastrar Novo Usuário")
        st.info("💡 **Dica de segurança:** Crie uma senha forte com no mínimo 8 caracteres, usando letras maiúsculas e minúsculas, números e símbolos.")
        with st.form("cadastro_form"):
            nome = st.text_input("Nome Completo")
            matricula = st.text_input("Matrícula")
            email = st.text_input("E-mail Essencis")
            password_cad = st.text_input("Crie uma Senha", type="password")
            confirm_password_cad = st.text_input("Confirme a Senha", type="password")
            submitted_cad = st.form_submit_button("Cadastrar")
            if submitted_cad:
                if nome and matricula and email and password_cad and confirm_password_cad:
                    if password_cad != confirm_password_cad:
                        st.error("❌ As senhas digitadas não coincidem. Por favor, tente novamente.")
                    elif not is_valid_email(email):
                        st.error("❌ Por favor, use um e-mail corporativo da Essencis (@essencis.com.br)")
                    elif not is_strong_password(password_cad):
                        st.error("❌ A senha deve ter pelo menos 8 caracteres, incluindo maiúsculas, minúsculas e números.")
                    else:
                        df_usuarios = load_usuarios_data()
                        if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and (df_usuarios['EMAIL'].str.lower() == email.lower()).any():
                            st.error("❌ Este e-mail já está cadastrado.")
                        else:
                            sheet = get_usuarios_sheet()
                            if sheet:
                                try:
                                    # Hash da senha antes de salvar
                                    senha_hash = hash_password(password_cad.strip())
                                    row = [nome, matricula, email, senha_hash]
                                    sheet.append_row(row)
                                    st.success(f"✅ Usuário {nome} cadastrado com sucesso! Agora você pode fazer o login.")
                                    load_usuarios_data.clear()
                                except Exception as e:
                                    st.error(f"❌ Erro ao cadastrar usuário: {e}")
                else:
                    st.error("❌ Por favor, preencha todos os campos.")

else: # Usuário Logado
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        st.header(f"👋 Bem-vindo, {st.session_state.current_user['NOME'].split()[0]}!")
        st.sidebar.button("🚪 Sair", on_click=logout)

    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Adicionar Reembolso", "Meu Histórico"],
        icons=["house", "cash-stack", "clock-history"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal",
    )
    if menu == "Dashboard":
        st.header("📊 Resumo dos Seus Reembolsos")
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == st.session_state.current_user['EMAIL'].lower()]
            if not df_usuario.empty:
                st.subheader("📈 Estatísticas")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Reembolsos", len(df_usuario))
                with col2:
                    if 'VALOR' in df_usuario.columns:
                        total_valor = df_usuario['VALOR'].sum()
                        st.metric("Valor Total", format_currency(total_valor))
                with col3:
                    if 'STATUS' in df_usuario.columns:
                        pendentes = df_usuario[df_usuario['STATUS'] == 'Pendente'].shape[0]
                        st.metric("Pendentes", pendentes)

                st.subheader("🏢 Custo por Departamento (Seus Reembolsos)")
                if 'DEPARTAMENTO' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    df_depto = df_usuario.groupby('DEPARTAMENTO')['VALOR'].sum().reset_index()
                    fig_depto = px.bar(df_depto, x='DEPARTAMENTO', y='VALOR',
                                     title="Custo por Departamento",
                                     labels={'VALOR': 'Valor (R$)', 'DEPARTAMENTO': 'Departamento'})
                    st.plotly_chart(fig_depto, use_container_width=True)

                st.subheader("💰 Custo por Tipo de Despesa (Seus Reembolsos)")
                if 'TIPO_DESPESA' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    df_despesa = df_usuario.groupby('TIPO_DESPESA')['VALOR'].sum().reset_index()
                    fig_despesa = px.bar(df_despesa, x='TIPO_DESPESA', y='VALOR',
                                         title="Custo por Tipo de Despesa",
                                         labels={'VALOR': 'Valor (R$)', 'TIPO_DESPESA': 'Tipo de Despesa'})
                    st.plotly_chart(fig_despesa, use_container_width=True)

                if 'STATUS' in df_usuario.columns:
                    df_status_counts = df_usuario['STATUS'].value_counts().reset_index()
                    df_status_counts.columns = ['STATUS', 'count']
                    fig_status = px.bar(df_status_counts, x='STATUS', y='count',
                                         title="Seus Reembolsos por Status",
                                         labels={'count': 'Quantidade', 'STATUS': 'Status'})
                    st.plotly_chart(fig_status)
            else:
                st.info("ℹ Nenhum reembolso encontrado para este e-mail.")
        else:
            st.warning("⚠ Não foi possível carregar os dados de reembolso.")

    elif menu == "Adicionar Reembolso":
        st.header("➕ Adicionar Novo Reembolso")
        user_info = st.session_state.current_user
        nome_funcionario = user_info['NOME']
        email_funcionario = user_info['EMAIL']
        st.subheader(f"👤 Dados do Solicitante:")
        st.info(f"**Nome:** {nome_funcionario} | **E-mail:** {email_funcionario}")

        num_reembolsos = st.number_input("Quantos reembolsos deseja adicionar?", min_value=1, step=1, value=1, key="num_reembolsos_input")

        for i in range(int(num_reembolsos)):
            st.markdown(f"### 📋 Reembolso #{i + 1}")
            with st.form(f"form_reembolso_{i}", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    departamento_selecionado = st.selectbox(
                        "Departamento",
                        DEPARTAMENTOS,
                        key=f"depto_{i}"
                    )
                with col2:
                    tipo_despesa_selecionada = st.selectbox(
                        "Tipo de Despesa",
                        TIPOS_DESPESA,
                        key=f"despesa_{i}"
                    )

                col1_val, col2_date = st.columns(2)
                with col1_val:
                    valor_reembolso = st.number_input(f"Valor", min_value=0.01, format="%.2f", key=f"valor_{i}")
                with col2_date:
                    data_reembolso = st.date_input(f"Data", value=datetime.date.today(), key=f"data_{i}")

                justificativa = st.text_area("Justificativa", key=f"justificativa_{i}")
                recibo_anexo = st.file_uploader("Comprovante (Imagem ou PDF)", type=["jpg", "jpeg", "png", "pdf"], key=f"recibo_{i}")

                submit_button = st.form_submit_button("💾 Salvar Este Reembolso")

                if submit_button:
                    if valor_reembolso and data_reembolso and justificativa:
                        id_comprovante = None
                        if recibo_anexo:
                            with st.spinner("📤 Enviando arquivo..."):
                                id_comprovante = upload_to_supabase(recibo_anexo)
                                if not id_comprovante:
                                    st.warning("⚠ Upload do arquivo falhou, mas o reembolso será salvo sem anexo.")

                        add_reembolso(data_reembolso, nome_funcionario, email_funcionario, departamento_selecionado,
                                        tipo_despesa_selecionada, valor_reembolso, justificativa, id_comprovante)
                        st.rerun()
                    else:
                        st.error("❌ Por favor, preencha todos os campos obrigatórios (Valor, Data, Justificativa).")

    elif menu == "Meu Histórico":
        st.header("📋 Meu Histórico de Reembolsos")
        user_email = st.session_state.current_user['EMAIL']
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()]
            if not df_usuario.empty:
                # Formata os valores corretamente
                df_usuario['VALOR_FORMATADO'] = df_usuario['VALOR'].apply(format_currency)
                df_usuario['DATA'] = pd.to_datetime(df_usuario['DATA']).dt.strftime('%d/%m/%Y')
                
                colunas_exibir = ['DATA', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR_FORMATADO', 'JUSTIFICATIVA', 'STATUS']
                colunas_existentes = [col for col in colunas_exibir if col in df_usuario.columns]
                
                st.dataframe(df_usuario[colunas_existentes].rename(columns={'VALOR_FORMATADO': 'VALOR'}), 
                           use_container_width=True, height=400)
                
                # Adicionar filtros
                st.subheader("🔍 Filtrar Reembolsos")
                col1, col2 = st.columns(2)
                with col1:
                    status_filter = st.selectbox("Status", ["Todos"] + list(df_usuario['STATUS'].unique()))
                with col2:
                    depto_filter = st.selectbox("Departamento", ["Todos"] + list(df_usuario['DEPARTAMENTO'].unique()))
                
                filtered_df = df_usuario
                if status_filter != "Todos":
                    filtered_df = filtered_df[filtered_df['STATUS'] == status_filter]
                if depto_filter != "Todos":
                    filtered_df = filtered_df[filtered_df['DEPARTAMENTO'] == depto_filter]
                
                st.write(f"**📊 Resultados filtrados:** {len(filtered_df)} reembolsos")
                st.dataframe(filtered_df[colunas_existentes].rename(columns={'VALOR_FORMATADO': 'VALOR'}), 
                           use_container_width=True, height=300)
                
            else:
                st.info("ℹ Nenhum reembolso encontrado para este e-mail.")
        else:
            st.warning("⚠ Não foi possível carregar os dados de reembolso.")
