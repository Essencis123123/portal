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
    st.error("O arquivo .streamlit/secrets.toml não foi encontrado. Por favor, crie-o com suas credenciais.")
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
    "Manutenção de Máquinas e Equipamentos",
    "Materiais de baixo custo (torneiras, lâmpadas, tomadas)",
    "Outros"
]

# --- Gerenciamento de Estado da Sessão ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None
if 'google_creds' not in st.session_state: # Renomeado para clareza
    st.session_state.google_creds = None
if 'user_email_oauth' not in st.session_state:
    st.session_state.user_email_oauth = None
if 'gmail_service' not in st.session_state:
    st.session_state.gmail_service = None

# --- Conexão com Google Sheets e APIs ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_FILE = 'token.json' # Arquivo para armazenar as credenciais OAuth do Gmail

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Autentica e retorna um cliente gspread."""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            secrets_dict["gcp_service_account"],
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro ao autenticar com Google Sheets: {e}. Verifique suas credenciais no secrets.toml.")
        return None

gs_client = get_gspread_client()

def get_reembolsos_sheet():
    """Retorna o objeto da aba 'Reembolsos'."""
    if not gs_client:
        st.error("Cliente do Google Sheets não inicializado.")
        return None
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Reembolsos")
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de API ao acessar a planilha 'Reembolsos': {e}.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Reembolsos' não foi encontrada na planilha. Verifique o nome.")
        return None

def get_usuarios_sheet():
    """Retorna o objeto da aba 'Usuarios'."""
    if not gs_client:
        st.error("Cliente do Google Sheets não inicializado.")
        return None
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Usuarios")
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de API ao acessar a planilha 'Usuarios': {e}.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Usuarios' não foi encontrada na planilha. Verifique o nome.")
        return None

# --- Funções de Envio de E-mail (Dependem de Autorização Gmail) ---
def create_message(sender, to, subject, message_text):
    """Cria uma mensagem MIME para envio por e-mail."""
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    msg = MIMEText(message_text, 'html')
    message.attach(msg)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    """Envia a mensagem de e-mail usando a API do Gmail."""
    if not service:
        st.error("Serviço do Gmail não está configurado. Não é possível enviar e-mail.")
        return None
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        st.success(f"E-mail enviado com sucesso!")
        return message
    except Exception as e:
        st.error(f"Ocorreu um erro ao enviar e-mail: {e}")
        return None

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
supabase_key = secrets_dict["supabase"]["service_role_key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

def upload_to_supabase(file_uploader, bucket_name="reembolsos-anexos"):
    """Faz upload de um arquivo para o bucket especificado no Supabase."""
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

            if response: # Supabase retorna None em caso de sucesso para upload
                st.success("✅ Arquivo enviado com sucesso para o Supabase!")
                return unique_file_name
            else:
                st.error("❌ Falha ao enviar o arquivo. Verifique as configurações do Supabase.")
                return None
        except Exception as e:
            st.error(f"❌ Ocorreu um erro no upload para o Supabase: {str(e)}")
            return None
    return None

def get_signed_url(file_path, bucket_name="reembolsos-anexos"):
    """Gera uma URL assinada para download de um arquivo no Supabase."""
    try:
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 604800) # Validade de 7 dias
        if 'signedURL' in response:
            return response['signedURL']
        else:
            st.error(f"Erro ao gerar URL assinada: {response}")
            return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar gerar a URL assinada: {e}")
        return None

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=300) # Cache por 5 minutos
def load_reembolsos_data():
    """Carrega os dados da planilha 'Reembolsos'."""
    sheet = get_reembolsos_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = df.columns.str.upper() # Padroniza nomes de colunas para maiúsculas
                if 'DATA' in df.columns:
                    df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                if 'VALOR' in df.columns:
                    # Limpa e converte a coluna VALOR para numérico
                    df['VALOR'] = df['VALOR'].astype(str).str.replace(',', '.', regex=False).str.replace('R\$', '', regex=False).str.strip()
                    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')
                return df
            else:
                return pd.DataFrame() # Retorna DataFrame vazio se a planilha estiver vazia
        except Exception as e:
            st.error(f"Erro ao processar dados da planilha 'Reembolsos': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache por 1 hora
def load_usuarios_data():
    """Carrega os dados da planilha 'Usuarios'."""
    sheet = get_usuarios_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = df.columns.str.upper() # Padroniza nomes de colunas para maiúsculas
                return df
            else:
                return pd.DataFrame() # Retorna DataFrame vazio se a planilha estiver vazia
        except Exception as e:
            st.error(f"Erro ao processar dados da planilha 'Usuarios': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- Funções de Adicionar Reembolso e Cadastro ---
def add_reembolso(data, nome, email, departamento, tipo_despesa, valor, justificativa, caminho_recibo, status="Pendente"):
    """Adiciona um novo registro de reembolso à planilha e envia notificações por e-mail (se configurado)."""
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        valor_formatado = f"{valor:.2f}".replace('.', ',') # Formato brasileiro para exibição
        try:
            row = [data_formatada, nome, departamento, tipo_despesa, valor_formatado, justificativa, status, caminho_recibo, email]
            sheet.append_row(row)
            st.success("Reembolso adicionado com sucesso!")

            # Limpa o cache para recarregar a tabela com o novo item
            load_reembolsos_data.clear()

            # --- Envio de E-mails (se Gmail configurado) ---
            # Só tenta enviar se o serviço do Gmail estiver disponível
            if st.session_state.gmail_service and st.session_state.user_email_oauth:
                sender_email = st.session_state.user_email_oauth
                recibo_url = None
                if caminho_recibo:
                    recibo_url = get_signed_url(caminho_recibo)

                # 1. Envia e-mail para o usuário solicitante
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
                if recibo_url:
                    body_user += f"<p>Clique aqui para baixar a notinha: <a href='{recibo_url}'>Baixar Comprovante</a></p>"
                body_user += "<p>Em breve, você receberá uma notificação sobre o status do seu pedido.</p><p>Atenciosamente,<br>Equipe de Suprimentos Essencis</p>"

                message_user = create_message(sender_email, email, subject_user, body_user)
                send_message(st.session_state.gmail_service, 'me', message_user)

                # 2. Envia e-mail para o administrador
                admin_email = "earaujo@essencis.com.br" # E-mail do administrador
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
                if recibo_url:
                    body_admin += f"<p>Clique aqui para baixar o comprovante: <a href='{recibo_url}'>Baixar Comprovante</a></p>"
                body_admin += "<p>Atenciosamente,<br>Sistema de Reembolsos</p>"

                message_admin = create_message(sender_email, admin_email, subject_admin, body_admin)
                send_message(st.session_state.gmail_service, 'me', message_admin)
            else:
                st.warning("O serviço de e-mail não está configurado ou autorizado. Notificações por e-mail não serão enviadas.")

        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")
    else:
        st.error("Não foi possível acessar a planilha de reembolsos. Verifique as configurações.")

# --- Funções de Autenticação de Login (Independente do Gmail) ---
def login(email, password):
    """Realiza o login do usuário usando credenciais da planilha 'Usuarios'."""
    df_usuarios = load_usuarios_data()
    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and 'SENHA' in df_usuarios.columns:
        # Busca o usuário com email e senha corretos (case-insensitive para email)
        user_data = df_usuarios[(df_usuarios['EMAIL'].str.lower() == email.lower()) & (df_usuarios['SENHA'] == password)]
        if not user_data.empty:
            st.session_state.logged_in = True
            st.session_state.current_user = user_data.iloc[0] # Armazena os dados do usuário logado
            st.success("Login bem-sucedido!")
            st.rerun() # Atualiza a página para carregar o menu principal
        else:
            st.error("E-mail ou senha incorretos.")
    else:
        st.error("Não foi possível carregar os dados de usuário ou as colunas necessárias não foram encontradas. Verifique a planilha 'Usuarios' e suas permissões.")

def logout():
    """Realiza o logout do usuário, limpando o estado da sessão."""
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.info("Você foi desconectado.")
    st.rerun() # Atualiza a página para mostrar a tela de login

# --- Autenticação OAuth (com persistência) para Gmail ---
# Esta seção é *apenas* para autorizar o envio de e-mails.
# O aplicativo funciona mesmo se o usuário não autorizar aqui.
def authenticate_gmail():
    """Autentica o usuário para acesso ao Gmail e salva as credenciais."""
    if 'google_creds' not in st.session_state or not st.session_state.google_creds or not st.session_state.google_creds.valid:
        if os.path.exists(TOKEN_FILE):
            try:
                st.session_state.google_creds = Credentials.from_authorized_user_file(TOKEN_FILE, GMAIL_SCOPES)
                if st.session_state.google_creds.expired and st.session_state.google_creds.refresh_token:
                    st.session_state.google_creds.refresh(Request())
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(st.session_state.google_creds.to_json())
            except Exception as e:
                st.error(f"Erro ao carregar token existente do Gmail: {e}. Por favor, autorize novamente.")
                st.session_state.google_creds = None
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE) # Remove token inválido

        if not st.session_state.google_creds or not st.session_state.google_creds.valid:
            st.warning("Para que o aplicativo possa enviar e-mails (notificações de reembolso), você precisa autorizá-lo.")
            try:
                # Gera o link de autorização
                redirect_uri_oob = "urn:ietf:wg:oauth:2.0:oob" # Para aplicação desktop
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": secrets_dict["google_oauth"]["client_id"],
                            "client_secret": secrets_dict["google_oauth"]["client_secret"],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    }, GMAIL_SCOPES, redirect_uri=redirect_uri_oob)

                auth_url, _ = flow.authorization_url(prompt='consent')
                
                # Exibe o link para o usuário clicar e um campo para colar o código
                st.markdown(f"Por favor, **[clique aqui para autorizar o acesso ao seu Gmail](%s)**." % auth_url)
                authorization_code = st.text_input("Cole o código de autorização que você recebeu aqui:")

                if authorization_code:
                    try:
                        flow.fetch_token(code=authorization_code)
                        st.session_state.google_creds = flow.credentials
                        with open(TOKEN_FILE, 'w') as token:
                            token.write(st.session_state.google_creds.to_json())

                        # Tenta obter o e-mail do usuário a partir do token (se disponível)
                        if hasattr(st.session_state.google_creds, 'id_token') and st.session_state.google_creds.id_token:
                            st.session_state.user_email_oauth = st.session_state.google_creds.id_token.get('email')
                        else:
                            st.warning("Não foi possível obter o e-mail do usuário diretamente do token. Usando um endereço padrão para remetente.")
                            st.session_state.user_email_oauth = "noreply@essencis.com.br" # Um e-mail padrão

                        st.success("Autorização do Gmail bem-sucedida! Você poderá receber notificações.")
                        st.rerun() # Recarrega para ativar o serviço Gmail
                    except Exception as e:
                        st.error(f"Erro ao obter o token do Gmail: {e}")
                        st.session_state.google_creds = None
                        if os.path.exists(TOKEN_FILE):
                            os.remove(TOKEN_FILE)
            except Exception as e:
                st.error(f"Erro no fluxo de autenticação do Gmail: {e}")
                st.session_state.google_creds = None

# Tenta construir o serviço Gmail se as credenciais forem válidas
if st.session_state.google_creds and st.session_state.google_creds.valid:
    try:
        st.session_state.gmail_service = build('gmail', 'v1', credentials=st.session_state.google_creds)
        # Se o email não foi obtido durante a autenticação inicial, tenta agora
        if not st.session_state.user_email_oauth:
            if hasattr(st.session_state.google_creds, 'id_token') and st.session_state.google_creds.id_token:
                st.session_state.user_email_oauth = st.session_state.google_creds.id_token.get('email')
            else:
                st.warning("Não foi possível obter o e-mail do usuário. Usando um endereço padrão para remetente.")
                st.session_state.user_email_oauth = "noreply@essencis.com.br"
    except Exception as e:
        st.error(f"Erro ao construir serviço Gmail: {e}")
        st.session_state.gmail_service = None # Garante que o serviço não seja usado se houver erro

# --- Layout do Aplicativo ---
st.markdown("""
    <div class='header-container'>
        <h1>💰 Gestão de Reembolsos Essencis</h1>
        <p>Sistema de Controle e Análise de Reembolsos</p>
    </div>
""", unsafe_allow_html=True)

# --- Seção de Login/Cadastro (quando o usuário não está logado) ---
if not st.session_state.logged_in:
    # Adiciona o logo no sidebar apenas quando não logado (ou em modo de escolha)
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
            styles={
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#0055a5"},
            }
        )
    
    if selected_page == "Login":
        st.header("Login")
        with st.form("login_form"):
            email_login = st.text_input("E-mail")
            password_login = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
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
                    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and (df_usuarios['EMAIL'].str.lower() == email.lower()).any():
                        st.error("Este e-mail já está cadastrado. Por favor, use a opção de Login.")
                    else:
                        sheet = get_usuarios_sheet()
                        if sheet:
                            try:
                                # Adiciona o novo usuário à planilha
                                row = [nome, matricula, email, password_cad]
                                sheet.append_row(row)
                                st.success(f"Usuário '{nome}' cadastrado com sucesso! Agora você pode fazer o login.")
                                # Limpa o cache dos usuários para carregar o novo registro na próxima leitura
                                load_usuarios_data.clear()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar usuário na planilha: {e}")
                        else:
                            st.error("Não foi possível acessar a planilha de usuários. Verifique as configurações.")
                else:
                    st.error("Por favor, preencha todos os campos para o cadastro.")

# --- Seção Principal do Aplicativo (quando o usuário está logado) ---
else:
    # Adiciona o logo e informações do usuário no sidebar quando logado
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        st.header(f"Bem-vindo, {st.session_state.current_user['NOME'].split()[0]}!") # Mostra o primeiro nome do usuário
        
        # Botão de Logout
        if st.sidebar.button("Sair", on_click=logout):
            pass # A ação de logout é tratada pela função logout()
    
    # Menu de navegação principal
    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Adicionar Reembolso", "Meu Histórico"],
        icons=["house", "cash-stack", "clock-history"],
        menu_icon="cast",
        default_index=1, # Default para Adicionar Reembolso
        orientation="horizontal",
        styles={
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#0055a5"},
        }
    )

    # --- Conteúdo do Dashboard ---
    if menu == "Dashboard":
        st.header("Resumo dos Seus Reembolsos")
        df_reembolsos = load_reembolsos_data()
        user_email = st.session_state.current_user['EMAIL']

        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()].copy() # Use .copy() para evitar SettingWithCopyWarning
            
            if not df_usuario.empty:
                st.subheader("Estatísticas Gerais")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total de Reembolsos", len(df_usuario))
                with col2:
                    if 'VALOR' in df_usuario.columns:
                        total_valor = df_usuario['VALOR'].sum()
                        st.metric("Valor Total Solicitado", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) # Formato BR
                with col3:
                    if 'STATUS' in df_usuario.columns:
                        pendentes = df_usuario[df_usuario['STATUS'] == 'Pendente'].shape[0]
                        st.metric("Pendentes de Aprovação", pendentes)

                # Gráficos
                if 'DEPARTAMENTO' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    st.subheader("Custo por Departamento (Seus Reembolsos)")
                    df_depto = df_usuario.groupby('DEPARTAMENTO')['VALOR'].sum().reset_index()
                    fig_depto = px.bar(df_depto, x='DEPARTAMENTO', y='VALOR',
                                       title="Custo por Departamento",
                                       labels={'VALOR': 'Valor (R$)', 'DEPARTAMENTO': 'Departamento'})
                    fig_depto.update_layout(margin=dict(l=20, r=20, t=40, b=20)) # Ajusta margens
                    st.plotly_chart(fig_depto, use_container_width=True)

                if 'TIPO_DESPESA' in df_usuario.columns and 'VALOR' in df_usuario.columns:
                    st.subheader("Custo por Tipo de Despesa (Seus Reembolsos)")
                    df_despesa = df_usuario.groupby('TIPO_DESPESA')['VALOR'].sum().reset_index()
                    fig_despesa = px.bar(df_despesa, x='TIPO_DESPESA', y='VALOR',
                                         title="Custo por Tipo de Despesa",
                                         labels={'VALOR': 'Valor (R$)', 'TIPO_DESPESA': 'Tipo de Despesa'})
                    fig_despesa.update_layout(margin=dict(l=20, r=20, t=40, b=20)) # Ajusta margens
                    st.plotly_chart(fig_despesa, use_container_width=True)

                if 'STATUS' in df_usuario.columns:
                    st.subheader("Seus Reembolsos por Status")
                    status_counts = df_usuario['STATUS'].value_counts().reset_index()
                    status_counts.columns = ['STATUS', 'count']
                    fig_status = px.pie(status_counts, values='count', names='STATUS', title='Distribuição por Status')
                    fig_status.update_layout(margin=dict(l=20, r=20, t=40, b=20)) # Ajusta margens
                    st.plotly_chart(fig_status, use_container_width=True)

            else:
                st.info("Você ainda não registrou nenhum reembolso.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso ou a coluna 'EMAIL' não existe na planilha 'Reembolsos'.")

    # --- Conteúdo da Adição de Reembolso ---
    elif menu == "Adicionar Reembolso":
        st.header("Adicionar Novo Reembolso")
        user_info = st.session_state.current_user
        nome_funcionario = user_info['NOME']
        email_funcionario = user_info['EMAIL']
        
        st.subheader("Informações do Solicitante:")
        st.info(f"**Nome:** {nome_funcionario} | **E-mail:** {email_funcionario}")

        # Campo para definir quantos reembolsos serão adicionados de uma vez
        num_reembolsos = st.number_input("Quantos reembolsos deseja adicionar nesta etapa?", min_value=1, value=1, step=1, key="num_reembolsos_input")

        # Loop para criar formulários para cada reembolso
        for i in range(int(num_reembolsos)):
            st.markdown(f"### Reembolso #{i + 1}")
            with st.form(f"form_reembolso_{i}"):
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
                    valor_reembolso = st.number_input(
                        "Valor (R$)", 
                        min_value=0.01, 
                        format="%.2f", 
                        key=f"valor_{i}"
                    )
                with col2_date:
                    data_reembolso = st.date_input(
                        "Data da Despesa", 
                        value=datetime.date.today(), 
                        key=f"data_{i}"
                    )

                justificativa = st.text_area("Justificativa da Despesa", key=f"justificativa_{i}")
                recibo_anexo = st.file_uploader(
                    "Anexar Comprovante (Imagem JPG/PNG ou PDF)", 
                    type=["jpg", "jpeg", "png", "pdf"], 
                    key=f"recibo_{i}"
                )

                # Botão para submeter um único formulário de reembolso
                submit_button = st.form_submit_button("Salvar Este Reembolso")

                if submit_button:
                    if valor_reembolso and data_reembolso and justificativa:
                        caminho_recibo = None
                        if recibo_anexo:
                            # Tenta fazer o upload para o Supabase
                            caminho_recibo = upload_to_supabase(recibo_anexo)
                            if not caminho_recibo:
                                st.warning("Upload do arquivo falhou, mas o reembolso será salvo sem anexo.")

                        # Chama a função para adicionar o reembolso
                        add_reembolso(
                            data_reembolso, 
                            nome_funcionario, 
                            email_funcionario, 
                            departamento_selecionado,
                            tipo_despesa_selecionada, 
                            valor_reembolso, 
                            justificativa, 
                            caminho_recibo
                        )
                        # Redireciona para o histórico após salvar para ver o novo item (opcional)
                        st.success("Reembolso adicionado. Você pode visualizá-lo em 'Meu Histórico'.")
                        # Limpa o formulário atual de forma simulada (exibindo uma mensagem)
                        st.experimental_rerun() # Recarrega a página para limpar campos de formulário
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios (Valor, Data, Justificativa).")

    # --- Conteúdo do Histórico de Reembolsos ---
    elif menu == "Meu Histórico":
        st.header("Meu Histórico de Reembolsos")
        user_email = st.session_state.current_user['EMAIL']
        df_reembolsos = load_reembolsos_data()
        
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            # Filtra os reembolsos do usuário logado
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()].copy() # Use .copy() para evitar SettingWithCopyWarning
            
            if not df_usuario.empty:
                # Formatação para exibição no DataFrame
                # Garante que a coluna 'VALOR' seja tratada corretamente antes da formatação final
                df_usuario['VALOR_FORMATADO'] = df_usuario['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                df_usuario['DATA'] = pd.to_datetime(df_usuario['DATA']).dt.strftime('%d/%m/%Y')

                # Seleciona e renomeia colunas para exibição mais amigável
                df_display = df_usuario[['DATA', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR_FORMATADO', 'JUSTIFICATIVA', 'STATUS']]
                df_display.columns = ['Data', 'Departamento', 'Tipo de Despesa', 'Valor', 'Justificativa', 'Status']
                
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("Nenhum reembolso encontrado para este usuário.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso ou a coluna 'EMAIL' não existe na planilha 'Reembolsos'.")

# --- Bloco para solicitar autorização do Gmail se o serviço não estiver pronto ---
# Este bloco só aparece se o usuário não estiver logado ou se estiver logado mas o Gmail ainda não foi autorizado
if not st.session_state.logged_in or (st.session_state.logged_in and (not st.session_state.gmail_service or not st.session_state.user_email_oauth)):
    # Chama a função para tentar autenticar o Gmail se o serviço ainda não estiver ativo
    authenticate_gmail()
