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

# --- CSS Personalizado para a Sidebar ---
# Você pode ajustar as cores aqui. Ex:
# --sidebar-background-color: #0E1117; (um cinza bem escuro, quase preto)
# --accent-color: #1C4D86; (azul Essencis)
custom_css = """
<style>
    [data-testid="stSidebar"] {
        background-color: #0E1117; /* Cor de fundo da sidebar */
    }
    /* Ajustes para o option_menu */
    .st-emotion-cache-16txt4v { /* Tenta pegar o container principal do option_menu */
        background-color: #0E1117 !important;
    }
    .st-emotion-cache-16txt4v button[data-testid="stSidebarNav"] ul li a {
        color: white !important; /* Cor do texto dos links */
    }
    .st-emotion-cache-16txt4v button[data-testid="stSidebarNav"] ul li a:hover {
        background-color: #262730 !important; /* Cor ao passar o mouse */
    }
    .st-emotion-cache-16txt4v button[data-testid="stSidebarNav"] ul li span {
        color: white !important; /* Cor dos ícones */
    }
    .st-emotion-cache-16txt4v button[data-testid="stSidebarNav"] ul li.st-emotion-cache-14g7ou a { /* Estilo do item selecionado */
        background-color: #1C4D86 !important; /* Cor de fundo do item selecionado */
        color: white !important; /* Cor do texto do item selecionado */
    }
    /* Título do menu da sidebar */
    .st-emotion-cache-16txt4v div[role="menu"] p {
        color: white !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


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
    "Manutenção de Máquinas e Equipamentos",
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
            return df
    return pd.DataFrame()

# --- Funções de Adicionar Reembolso e Cadastro ---
def add_reembolso(data, nome, email, departamento, tipo_despesa, valor, justificativa, caminho_recibo, status="Pendente"):
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        valor_formatado = f"{valor:.2f}".replace('.', ',')
        try:
            row = [data_formatada, nome, departamento, tipo_despesa, valor_formatado, justificativa, status, caminho_recibo, email]
            sheet.append_row(row)
            st.success("Reembolso adicionado com sucesso!")

            # Limpa o cache para recarregar a tabela com o novo item
            load_reembolsos_data.clear()

            sender_email = st.session_state.user_email_oauth

            recibo_url = None
            if caminho_recibo:
                recibo_url = get_signed_url(caminho_recibo)

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
            if recibo_url:
                body_user += f"<p>Clique aqui para baixar a notinha: <a href='{recibo_url}'>Baixar Comprovante</a></p>"
            body_user += "<p>Em breve, você receberá uma notificação sobre o status do seu pedido.</p><p>Atenciosamente,<br>Equipe de Suprimentos Essencis</p>"

            message_user = create_message(sender_email, email, subject_user, body_user)
            send_message(st.session_state.gmail_service, 'me', message_user)

            # 2. Envia e-mail para o administrador
            admin_email = "earaujo@essencis.com.br"
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

        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")

# --- Funções de Autenticação de Login ---
def login(email, password):
    df_usuarios = load_usuarios_data()
    if not df_usuarios.empty and 'EMAIL' in df_usuarios.columns and 'SENHA' in df_usuarios.columns:
        user_data = df_usuarios[(df_usuarios['EMAIL'].str.lower() == email.lower()) & (df_usuarios['SENHA'] == password)]
        if not user_data.empty:
            st.session_state.logged_in = True
            st.session_state.current_user = user_data.iloc[0]
            st.success("Login bem-sucedido!")
            st.rerun()
        else:
            st.error("E-mail ou senha incorretos.")
    else:
        st.error("Não foi possível carregar os dados de usuário. Verifique a planilha 'Usuarios'.")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.info("Você foi desconectado.")
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

if not st.session_state.creds or not st.session_state.creds.valid:
    st.info("Para que o aplicativo possa enviar e-mails, você precisa autorizá-lo.")

    try:
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

        st.markdown(f"Por favor, **[clique aqui para autorizar o acesso](%s)**." % auth_url)

        authorization_code = st.text_input("Cole o código de autorização aqui:")

        if authorization_code:
            try:
                flow.fetch_token(code=authorization_code)
                if flow.credentials:
                    st.session_state.creds = flow.credentials
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(st.session_state.creds.to_json())

                    if hasattr(st.session_state.creds, 'id_token') and st.session_state.creds.id_token:
                        st.session_state.user_email_oauth = st.session_state.creds.id_token.get('email')
                    else:
                        st.warning("Token ID não disponível. Tentando obter email do usuário...")
                        st.session_state.user_email_oauth = "noreply@essencis.com.br" # Email padrão

                    st.session_state.gmail_service = build('gmail', 'v1', credentials=st.session_state.creds)
                    st.success("Autorização bem-sucedida! Você pode usar o aplicativo.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao obter o token: {e}")
    except Exception as e:
        st.error(f"Erro no fluxo de autenticação: {e}")

# Só constrói o serviço se as credenciais forem válidas
if st.session_state.creds and st.session_state.creds.valid:
    try:
        st.session_state.gmail_service = build('gmail', 'v1', credentials=st.session_state.creds)
        if not st.session_state.user_email_oauth:
            if hasattr(st.session_state.creds, 'id_token') and st.session_state.creds.id_token:
                st.session_state.user_email_oauth = st.session_state.creds.id_token.get('email')
            else:
                st.session_state.user_email_oauth = "noreply@essencis.com.br"
    except Exception as e:
        st.error(f"Erro ao construir serviço Gmail: {e}")
        st.session_state.gmail_service = None

# --- Sidebar ---
with st.sidebar:
    # Adicionar a logo no topo da sidebar
    # Certifique-se de que 'logo.png' está na mesma pasta ou ajuste o caminho
    try:
        # Tente carregar a logo. Ajuste o caminho se necessário.
        logo = Image.open("logo.png") # Exemplo: se a logo estiver na pasta 'assets', use "assets/logo.png"
        st.image(logo, use_column_width=True)
    except FileNotFoundError:
        st.warning("Logo não encontrada. Verifique se o arquivo 'logo.png' está no caminho correto.")

    st.markdown("---") # Linha divisória

    if st.session_state.logged_in:
        # Tenta exibir o nome do usuário em branco, caso contrário usa um placeholder
        user_nome_display = st.session_state.current_user.get('NOME', '').split()[0] if st.session_state.current_user and 'NOME' in st.session_state.current_user else "Usuário"
        st.markdown(f"<h3 style='color:white;'>Bem-vindo, {user_nome_display}!</h3>", unsafe_allow_html=True)
        st.button("Sair", on_click=logout)
    else:
        # Se não estiver logado, mostra apenas o título e a opção de sair se houver credenciais salvas
        if os.path.exists(TOKEN_FILE):
            # Limpa o token e recarrega a página
            st.button("Sair (Autorização)", on_click=lambda: os.remove(TOKEN_FILE) or st.rerun())

    st.markdown("---")

    # Menu de navegação para usuários logados
    if st.session_state.logged_in:
        selected_page = option_menu(
            menu_title="Navegação", # Título do menu
            options=["Dashboard", "Adicionar Reembolso", "Meu Histórico"],
            icons=["house", "cash-stack", "clock-history"],
            menu_icon="cast",
            default_index=1,
            styles={
                "container": {"padding": "5!important", "background-color": "#0E1117"},
                "icon": {"color": "white", "font-size": "20px"},
                "nav-link": {"font-size": "18px", "text-align": "left", "margin":"0px", "--hover-color": "#262730", "color": "white"},
                "nav-link-selected": {"background-color": "#1C4D86", "color": "white"},
            }
        )
    else:
        # Menu de navegação para a tela de login/cadastro
        selected_page = option_menu(
            menu_title="Acesso", # Título do menu
            options=["Login", "Cadastre-se"],
            icons=["box-arrow-in-right", "person-add"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {"padding": "5!important", "background-color": "#0E1117"},
                "icon": {"color": "white", "font-size": "20px"},
                "nav-link": {"font-size": "18px", "text-align": "left", "margin":"0px", "--hover-color": "#262730", "color": "white"},
                "nav-link-selected": {"background-color": "#1C4D86", "color": "white"},
            }
        )

# --- Layout Principal ---
st.title("💰 Gestão de Reembolsos Essencis") # O título principal ainda pode ficar aqui

if not st.session_state.logged_in:
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
                        st.error("Este e-mail já está cadastrado.")
                    else:
                        sheet = get_usuarios_sheet()
                        if sheet:
                            try:
                                row = [nome, matricula, email, password_cad]
                                sheet.append_row(row)
                                st.success(f"Usuário {nome} cadastrado com sucesso! Agora você pode fazer o login.")
                            except Exception as e:
                                st.error(f"Erro ao cadastrar usuário: {e}")
                else:
                    st.error("Por favor, preencha todos os campos.")

else:
    if selected_page == "Dashboard":
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
                        st.metric("Valor Total", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
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
                    fig_status = px.bar(df_usuario['STATUS'].value_counts(),
                                         title="Seus Reembolsos por Status",
                                         labels={'index': 'STATUS', 'value': 'Quantidade'})
                    st.plotly_chart(fig_status)
            else:
                st.info("Você ainda não tem reembolsos para exibir.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso ou a coluna 'EMAIL' não existe na planilha 'Reembolsos'.")
    elif selected_page == "Adicionar Reembolso":
        st.header("Adicionar Novo Reembolso")
        user_info = st.session_state.current_user
        nome_funcionario = user_info['NOME']
        email_funcionario = user_info['EMAIL']
        st.subheader(f"Dados do Solicitante:")
        st.info(f"**Nome:** {nome_funcionario} | **E-mail:** {email_funcionario}")
        num_reembolsos = st.number_input("Quantos reembolsos deseja adicionar?", min_value=1, step=1)
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
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios.")
    elif selected_page == "Meu Histórico":
        st.header("Meu Histórico de Reembolsos")
        user_email = st.session_state.current_user['EMAIL']
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
            df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()]
            if not df_usuario.empty:
                # Corrigindo a formatação do valor
                df_usuario['VALOR'] = df_usuario['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                df_usuario['DATA'] = pd.to_datetime(df_usuario['DATA']).dt.strftime('%d/%m/%Y')

                st.dataframe(df_usuario[['DATA', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS']])
            else:
                st.info("Nenhum reembolso encontrado para este e-mail.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso.")
