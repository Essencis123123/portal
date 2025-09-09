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
from googleapiclient.discovery import build
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import re
import mimetypes
from supabase import create_client, Client
import toml
from streamlit_option_menu import option_menu
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

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
        /* height: 100%;  Opcional: para ocupar toda a altura disponível */
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

# --- Carrega os segredos do arquivo secrets.toml ---
try:
    with open(".streamlit/secrets.toml", "r") as f:
        secrets_dict = toml.load(f)
except FileNotFoundError:
    st.error("O arquivo .streamlit/secrets.toml não foi encontrado.")
    st.stop()

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
if 'creds' not in st.session_state:
    st.session_state.creds = None
if 'user_email_oauth' not in st.session_state:
    st.session_state.user_email_oauth = None
if 'gmail_service' not in st.session_state:
    st.session_state.gmail_service = None

# --- Conexão com Google Sheets e APIs ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_FILE = 'token.json'

@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

# --- Instância do cliente gspread ---
gs_client = get_gspread_client()

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
        message = service.users().messages().send(userId=user_id, body=message).execute()
        # st.success(f"E-mail enviado com sucesso!") # Removido para não poluir a UI em cada envio
        return message
    except Exception as e:
        st.error(f"Ocorreu um erro ao enviar e-mail: {e}")
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
                # Gera a URL assinada e retorna para salvar na planilha
                signed_url = get_signed_url(unique_file_name, bucket_name)
                if signed_url:
                    return signed_url
                else:
                    st.warning("Arquivo enviado mas não foi possível gerar URL. Salvando apenas o nome do arquivo.")
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
@st.cache_data(ttl=300)
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
                # Converte para string, substitui vírgula por ponto e depois para numérico
                df['VALOR'] = df['VALOR'].astype(str).str.replace(',', '.', regex=False)
                df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')
            return df
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_usuarios_data():
    sheet = get_usuarios_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.columns.str.upper()
            # Certifica que as colunas esperadas existam
            for col in ['NOME', 'MATRICULA', 'EMAIL', 'SENHA']:
                if col not in df.columns:
                    df[col] = None # Adiciona a coluna com None se não existir
            return df
    return pd.DataFrame()

# --- Funções de Adicionar Reembolso e Cadastro ---
def add_reembolso(data, nome, email, departamento, tipo_despesa, valor, justificativa, caminho_recibo, status="Pendente"):
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        valor_formatado = f"{valor:.2f}".replace('.', ',') # Formato Brasileiro
        try:
            # Inclui o caminho do recibo (que pode ser None) na linha
            row = [data_formatada, nome, departamento, tipo_despesa, valor_formatado, justificativa, status, caminho_recibo, email]
            sheet.append_row(row)
            st.success("Reembolso adicionado com sucesso!")

            # Limpa o cache para recarregar a tabela com o novo item
            load_reembolsos_data.clear()

            sender_email = st.session_state.user_email_oauth if st.session_state.user_email_oauth else "noreply@essencis.com.br"

            # 1. Envia e-mail para o usuário
            subject_user = "CONFIRMACAO DE ENVIO - PEDIDO DE REEMBOLSO"
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
            if caminho_recibo:
                body_user += f"<p>Clique aqui para baixar a notinha: <a href='{caminho_recibo}'>Baixar Comprovante</a></p>"
            body_user += "<p>Em breve, você receberá uma notificação sobre o status do seu pedido.</p><p>Atenciosamente,<br>Equipe de Suprimentos Essencis</p>"

            message_user = create_message(sender_email, email, subject_user, body_user)
            if st.session_state.gmail_service:
                send_message(st.session_state.gmail_service, 'me', message_user)
            else:
                st.warning("Serviço Gmail não inicializado. E-mail de confirmação para o usuário não enviado.")

            # 2. Envia e-mail para o administrador
            admin_email = "earaujo@essencis.com.br" # Altere para o e-mail do administrador, se necessário
            subject_admin = f"Novo Reembolso Pendente de {nome}"
            body_admin = f"""
            <p>Olá, Administrador(a)!</p>
            <p>Um novo pedido de reembolso foi submetido e está aguardando sua aprovação.</p>
            <p><b>Detalhes do Reembolso:</b></p>
            <ul>
                <li><b>Solicitante:</b> {nome}</li>
                <li><b>Data:</b> {data_formatada}</li>
                <li><b>Departamento:</b> {departamento}</li>
                <li><b>Tipo de Despesa:</b> {tipo_despesa}</li>
                <li><b>Valor:</b> R$ {valor_formatado}</li>
                <li><b>Justificativa:</b> {justificativa}</li>
            </ul>
            """
            if caminho_recibo:
                body_admin += f"<p>Clique aqui para baixar o comprovante: <a href='{caminho_recibo}'>Baixar Comprovante</a></p>"
            body_admin += "<p>Atenciosamente,<br>Sistema de Reembolsos</p>"

            message_admin = create_message(sender_email, admin_email, subject_admin, body_admin)
            if st.session_state.gmail_service:
                send_message(st.session_state.gmail_service, 'me', message_admin)
            else:
                st.warning("Serviço Gmail não inicializado. E-mail de notificação para administrador não enviado.")

        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")

# --- Funções de Autenticação de Login ---
def login(email, password):
    df_usuarios = load_usuarios_data()
    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and 'SENHA' in df_usuarios.columns:
        # Verifica se o e-mail está na base de usuários (ignorando case)
        user_exists = (df_usuarios['EMAIL'].str.lower() == email.lower()).any()

        if not user_exists:
            st.error("Este e-mail não está cadastrado em nosso sistema.")
            return

        # Se o usuário existe, tenta autenticar com a senha
        user_data = df_usuarios[
            (df_usuarios['EMAIL'].str.lower() == email.lower()) &
            (df_usuarios['SENHA'] == password)
        ]

        if not user_data.empty:
            st.session_state.logged_in = True
            st.session_state.current_user = user_data.iloc[0] # Armazena a linha inteira do usuário
            st.success("Login bem-sucedido!")
            st.rerun()
        else:
            st.error("Senha incorreta.")
    else:
        st.error("Não foi possível carregar os dados de usuário. Verifique a planilha 'Usuarios'.")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.info("Você foi desconectado.")
    # Limpa o token do Google OAuth para forçar uma nova autorização na próxima vez
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    st.rerun()

# --- Autenticação OAuth (com persistência) ---
TOKEN_FILE = 'token.json'
if os.path.exists(TOKEN_FILE):
    try:
        st.session_state.creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if st.session_state.creds and st.session_state.creds.expired and st.session_state.creds.refresh_token:
            st.session_state.creds.refresh(Request())
    except Exception as e:
        st.error(f"Erro ao carregar token: {e}")
        st.session_state.creds = None

# Só solicita autorização OAuth se o usuário estiver logado
if st.session_state.logged_in and (not st.session_state.creds or not st.session_state.creds.valid):
    st.info("Para que o aplicativo possa enviar e-mails, você precisa autorizá-lo.")

    try:
        # Define redirect_uri_oob para que o código seja exibido no navegador
        redirect_uri_oob = "urn:ietf:wg:oauth:2.0:oob"
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": secrets_dict["google_oauth"]["client_id"],
                    "client_secret": secrets_dict["google_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }, SCOPES, redirect_uri=redirect_uri_oob)

        auth_url, _ = flow.authorization_url(prompt='consent')

        # Usa markdown para criar um link clicável para autorização
        st.markdown(f"Por favor, **[clique aqui para autorizar o acesso](%s)**." % auth_url)

        authorization_code = st.text_input("Cole o código de autorização que apareceu na tela aqui:")

        if authorization_code:
            try:
                flow.fetch_token(code=authorization_code)
                if flow.credentials:
                    st.session_state.creds = flow.credentials
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(st.session_state.creds.to_json())

                    # Tenta obter o email do usuário através do token ID
                    if hasattr(st.session_state.creds, 'id_token') and st.session_state.creds.id_token:
                        st.session_state.user_email_oauth = st.session_state.creds.id_token.get('email')
                    else:
                        # Se não conseguir, usa um email padrão ou avisa
                        st.warning("Token ID não disponível. Usando email padrão para envio de notificações.")
                        st.session_state.user_email_oauth = "noreply@essencis.com.br" # Email padrão para envio

                    st.session_state.gmail_service = build('gmail', 'v1', credentials=st.session_state.creds)
                    st.success("Autorização bem-sucedida! Agora você pode usar o aplicativo.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao obter o token: {e}")
    except Exception as e:
        st.error(f"Erro no fluxo de autenticação: {e}")

# Só constrói o serviço se as credenciais forem válidas e o email do usuário tiver sido obtido
if st.session_state.creds and st.session_state.creds.valid:
    try:
        st.session_state.gmail_service = build('gmail', 'v1', credentials=st.session_state.creds)
        if not st.session_state.user_email_oauth: # Garante que o email do remetente esteja definido
            if hasattr(st.session_state.creds, 'id_token') and st.session_state.creds.id_token:
                st.session_state.user_email_oauth = st.session_state.creds.id_token.get('email')
            else:
                st.session_state.user_email_oauth = "noreply@essencis.com.br" # Email padrão para envio
    except Exception as e:
        st.error(f"Erro ao construir serviço Gmail: {e}")
        st.session_state.gmail_service = None

# --- Layout do Aplicativo ---
st.markdown("""
    <div class='header-container'>
        <h1>💰 Gestão de Reembolsos Essencis</h1>
        <p>Sistema de Controle e Análise de Reembolsos</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    # Adiciona o logo no sidebar
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
        # Aplica a classe CSS ao container do formulário de login
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
        with st.form("cadastro_form"):
            nome = st.text_input("Nome Completo")
            matricula = st.text_input("Matrícula")
            email = st.text_input("E-mail Essencis")
            password_cad = st.text_input("Crie uma Senha", type="password")
            submitted_cad = st.form_submit_button("Cadastrar")
            if submitted_cad:
                if nome and matricula and email and password_cad:
                    df_usuarios = load_usuarios_data()
                    # Verifica se o email já existe na planilha (ignorando case)
                    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and (df_usuarios['EMAIL'].str.lower() == email.lower()).any():
                        st.error("Este e-mail já está cadastrado.")
                    else:
                        sheet = get_usuarios_sheet()
                        if sheet:
                            try:
                                row = [nome, matricula, email, password_cad]
                                sheet.append_row(row)
                                st.success(f"Usuário {nome} cadastrado com sucesso! Agora você pode fazer o login.")
                                # Limpa o cache dos usuários após adicionar um novo
                                load_usuarios_data.clear()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar usuário: {e}")
                else:
                    st.error("Por favor, preencha todos os campos.")

else: # Usuário Logado
    # Adiciona o logo no sidebar
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        st.header(f"Bem-vindo, {st.session_state.current_user['NOME'].split()[0]}!")
        st.sidebar.button("Sair", on_click=logout)

    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Adicionar Reembolso", "Meu Histórico"],
        icons=["house", "cash-stack", "clock-history"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal",
    )
    if menu == "Dashboard":
        st.header("Resumo dos Seus Reembolsos")
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == st.session_state.current_user['EMAIL'].lower()]
            if not df_usuario.empty:
                st.subheader("Estatísticas")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Reembolsos", len(df_usuario))
                with col2:
                    if 'VALOR' in df_usuario.columns:
                        total_valor = df_usuario['VALOR'].sum()
                        st.metric("Valor Total", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) # Formatação BR
                with col3:
                    if 'STATUS' in df_usuario.columns:
                        pendentes = df_usuario[df_usuario['STATUS'] == 'Pendente'].shape[0]
                        st.metric("Pendentes", pendentes)

                st.subheader("Custo por Departamento (Seus Reembolsos)")
                if 'DEPARTAMENTO' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    df_depto = df_usuario.groupby('DEPARTAMENTO')['VALOR'].sum().reset_index()
                    fig_depto = px.bar(df_depto, x='DEPARTAMENTO', y='VALOR',
                                       title="Custo por Departamento",
                                       labels={'VALOR': 'Valor (R$)', 'DEPARTAMENTO': 'Departamento'})
                    st.plotly_chart(fig_depto, use_container_width=True)

                st.subheader("Custo por Tipo de Despesa (Seus Reembolsos)")
                if 'TIPO_DESPESA' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    df_despesa = df_usuario.groupby('TIPO_DESPESA')['VALOR'].sum().reset_index()
                    fig_despesa = px.bar(df_despesa, x='TIPO_DESPESA', y='VALOR',
                                         title="Custo por Tipo de Despesa",
                                         labels={'VALOR': 'Valor (R$)', 'TIPO_DESPESA': 'Tipo de Despesa'})
                    st.plotly_chart(fig_despesa, use_container_width=True)

                if 'STATUS' in df_usuario.columns:
                    # Agrupa os status para contagem
                    df_status_counts = df_usuario['STATUS'].value_counts().reset_index()
                    df_status_counts.columns = ['STATUS', 'count'] # Renomeia colunas para Plotly
                    fig_status = px.bar(df_status_counts, x='STATUS', y='count',
                                        title="Seus Reembolsos por Status",
                                        labels={'count': 'Quantidade', 'STATUS': 'Status'})
                    st.plotly_chart(fig_status)
            else:
                st.info("Você ainda não tem reembolsos registrados.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso ou a coluna 'EMAIL' não existe na planilha 'Reembolsos'.")

    elif menu == "Adicionar Reembolso":
        st.header("Adicionar Novo Reembolso")
        user_info = st.session_state.current_user
        nome_funcionario = user_info['NOME']
        email_funcionario = user_info['EMAIL']
        st.subheader(f"Dados do Solicitante:")
        st.info(f"**Nome:** {nome_funcionario} | **E-mail:** {email_funcionario}")

        # Adicionado um controle para adicionar um ou mais reembolsos
        num_reembolsos = st.number_input("Quantos reembolsos deseja adicionar?", min_value=1, step=1, value=1, key="num_reembolsos_input")

        for i in range(int(num_reembolsos)):
            st.markdown(f"### Reembolso #{i + 1}")
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

                submit_button = st.form_submit_button("Salvar Este Reembolso")

                if submit_button:
                    if valor_reembolso and data_reembolso and justificativa:
                        caminho_recibo = None
                        if recibo_anexo:
                            caminho_recibo = upload_to_supabase(recibo_anexo)
                            if not caminho_recibo:
                                st.warning("Upload do arquivo falhou, mas o reembolso será salvo sem anexo.")

                        add_reembolso(data_reembolso, nome_funcionario, email_funcionario, departamento_selecionado,
                                        tipo_despesa_selecionada, valor_reembolso, justificativa, caminho_recibo)
                        # Limpa o formulário atual após submissão bem-sucedida
                        st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios (Valor, Data, Justificativa).")

    elif menu == "Meu Histórico":
        st.header("Meu Histórico de Reembolsos")
        user_email = st.session_state.current_user['EMAIL']
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()]
            if not df_usuario.empty:
                # Formata a coluna de valor para o padrão brasileiro
                df_usuario['VALOR'] = df_usuario['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                # Formata a coluna de data para o padrão brasileiro
                df_usuario['DATA'] = pd.to_datetime(df_usuario['DATA']).dt.strftime('%d/%m/%Y')

                # Seleciona e exibe as colunas desejadas
                colunas_exibir = ['DATA', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS', 'CAMINHO_RECIBO']
                # Garante que todas as colunas desejadas existam no DataFrame antes de tentar exibi-las
                colunas_existentes = [col for col in colunas_exibir if col in df_usuario.columns]

                st.dataframe(df_usuario[colunas_existentes], use_container_width=True)
            else:
                st.info("Nenhum reembolso encontrado para este e-mail.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso.")
