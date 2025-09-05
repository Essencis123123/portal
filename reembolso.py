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
from googleapiclient.http import MediaIoBaseUpload
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import re

# --- Configuração do Layout e Tema ---
st.set_page_config(page_title="Gestão de Reembolsos", layout="wide", page_icon="💰")

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

# --- Funções para carregar recursos ---
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        st.error(f"Erro ao carregar a logo: {e}")
        return None

# --- Configuração de Dados e Lógica de Backend (Google Sheets e Drive) ---
SHEET_ID = st.secrets["sheet_id"]
PASTA_DRIVE_ID = "1FyHsl2dR9kMiRvBhp0i_WV1fvYgEeNPY"

# Conexão com Google Sheets (gspread)
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

# Conexão com Google Drive e Gmail API
@st.cache_resource(ttl=3600)
def get_google_api_service():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/gmail.send']
    )
    drive_service = build('drive', 'v3', credentials=creds)
    gmail_service = build('gmail', 'v1', credentials=creds)
    return drive_service, gmail_service

gs_client = get_gspread_client()
drive_service, gmail_service = get_google_api_service()


def carregar_dados_usuarios():
    try:
        sheet = gs_client.open_by_key(SHEET_ID).worksheet("Usuarios")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error("A planilha 'Usuarios' não foi encontrada. Certifique-se de que ela existe na planilha 'despesas'.")
        return pd.DataFrame(columns=['Nome', 'Matricula', 'Email', 'Senha'])
    except Exception as e:
        st.error(f"Erro ao carregar dados de usuários: {e}")
        return pd.DataFrame(columns=['Nome', 'Matricula', 'Email', 'Senha'])

def carregar_dados_reembolsos():
    try:
        sheet = gs_client.open_by_key(SHEET_ID).worksheet("Reembolsos")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error("A planilha 'Reembolsos' não foi encontrada. Certifique-se de que ela existe na planilha 'despesas'.")
        return pd.DataFrame(columns=['DATA', 'NOME', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS', 'ID_COMPROVANTE'])
    except Exception as e:
        st.error(f"Erro ao carregar dados de reembolsos: {e}")
        return pd.DataFrame(columns=['DATA', 'NOME', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS', 'ID_COMPROVANTE'])


def salvar_dados_reembolsos(df):
    try:
        sheet = gs_client.open_by_key(SHEET_ID).worksheet("Reembolsos")
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados na planilha do Google: {e}")
        return False

# --- Lógica de Login e Cadastro (Google Sheets) ---
def cadastrar_usuario(nome, matricula, email, senha):
    df_usuarios = carregar_dados_usuarios()
    
    email_limpo = email.strip()
    matricula_limpa = matricula.strip()

    if email_limpo in df_usuarios['Email'].astype(str).str.strip().values:
        st.error("❌ Email já cadastrado. Por favor, use outro.")
        return False
    if matricula_limpa in df_usuarios['Matricula'].astype(str).str.strip().values:
        st.error("❌ Matrícula já cadastrada.")
        return False

    novo_usuario = pd.DataFrame([{
        'Nome': nome.strip(),
        'Matricula': matricula_limpa,
        'Email': email_limpo,
        'Senha': senha
    }])
    df_usuarios = pd.concat([df_usuarios, novo_usuario], ignore_index=True)
    
    try:
        sheet = gs_client.open_by_key(SHEET_ID).worksheet("Usuarios")
        sheet.clear()
        sheet.update([df_usuarios.columns.values.tolist()] + df_usuarios.values.tolist())
        st.success("🎉 Cadastro realizado com sucesso! Você já pode fazer login.")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados de usuário: {e}")
        return False

def fazer_login(email, senha):
    df_usuarios = carregar_dados_usuarios()
    
    if not df_usuarios.empty:
        df_usuarios['Email'] = df_usuarios['Email'].astype(str).str.strip()
        df_usuarios['Senha'] = df_usuarios['Senha'].astype(str).str.strip()
        usuario_encontrado = df_usuarios[
            (df_usuarios['Email'] == email.strip()) & (df_usuarios['Senha'] == senha.strip())
        ]
        
        if not usuario_encontrado.empty:
            st.session_state['logado'] = True
            st.session_state['nome_colaborador'] = usuario_encontrado.iloc[0]['Nome']
            st.session_state['email_colaborador'] = usuario_encontrado.iloc[0]['Email'] # Guarda o email do usuário
            st.success(f"✅ Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
            st.rerun()
            return True
        else:
            st.error("❌ Email ou senha incorretos.")
            return False
    else:
        st.error("Planilha de usuários não encontrada ou vazia.")
        return False

# Função para enviar e-mail
def send_email(to_email, subject, body, from_email='suprimentosessencis.com.br'):
    try:
        message = MIMEMultipart()
        message['to'] = to_email
        message['from'] = from_email
        message['subject'] = subject
        message.attach(MIMEText(body, 'html'))
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = gmail_service.users().messages().send(
            userId=from_email,
            body={'raw': raw_message}).execute()
        return sent_message
    except Exception as e:
        st.error(f"Erro ao enviar e-mail para {to_email}: {e}")
        return None

# Função para fazer upload para o Google Drive
def upload_to_drive(file, folder_id):
    try:
        file_metadata = {
            'name': file.name,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(file.getvalue()), mimetype=file.type)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webContentLink'
        ).execute()
        return uploaded_file.get('webContentLink')
    except Exception as e:
        st.error(f"Erro ao fazer upload do arquivo para o Google Drive: {e}")
        return None

# Lista de Departamentos (Número sempre antes do nome)
DEPARTAMENTOS = [
    "1601 - Financeiro / Administrativo",
    "1201 - Administração da Manutenção",
    "2302 - Aterro K1",
    "2303 - Aterro K2",
    "1202 - Manutenção de veículos e equipamentos",
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

# Lista de Tipos de Despesa
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

# --- INTERFACE PRINCIPAL ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.title("💰 Login do Sistema de Reembolso")
    st.markdown("---")
    
    login_tab, cadastro_tab = st.tabs(["Fazer Login", "Cadastrar Novo Usuário"])
    
    with login_tab:
        st.subheader("Acesse sua conta")
        with st.form("login_form"):
            email_login = st.text_input("Email", key="email_login")
            senha_login = st.text_input("Senha", type="password", key="senha_login")
            if st.form_submit_button("Entrar"):
                fazer_login(email_login, senha_login)
    
    with cadastro_tab:
        st.subheader("Crie sua conta")
        with st.form("cadastro_form"):
            nome_cadastro = st.text_input("Nome completo")
            matricula_cadastro = st.text_input("Matrícula")
            email_cadastro = st.text_input("Email")
            senha_cadastro = st.text_input("Senha", type="password")
            repita_senha_cadastro = st.text_input("Repita a senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if not all([nome_cadastro, matricula_cadastro, email_cadastro, senha_cadastro, repita_senha_cadastro]):
                    st.error("Por favor, preencha todos os campos.")
                elif senha_cadastro != repita_senha_cadastro:
                    st.error("As senhas não coincidem.")
                else:
                    cadastrar_usuario(nome_cadastro, matricula_cadastro, email_cadastro, senha_cadastro)

else:
    # Exibição da logo no sidebar
    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)
    if logo_img:
        st.sidebar.image(logo_img, use_container_width=True)

    # Inicializa a lista de reembolsos no session state se ainda não existir
    if 'reembolsos_a_enviar' not in st.session_state:
        st.session_state.reembolsos_a_enviar = [{}]

    # Carregamento dos dados
    if 'df_reembolsos' not in st.session_state:
        st.session_state.df_reembolsos = carregar_dados_reembolsos()

    st.sidebar.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Gestor')}!**")
    st.sidebar.title("Menu de Navegação")
    menu_option = st.sidebar.radio(
        "Selecione a opção:",
        ["📝 Solicitar Reembolso", "📊 Dashboard", "🔍 Consultar", "⚙️ Configurações"],
        index=0
    )
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        st.session_state['logado'] = False
        st.session_state.pop('nome_colaborador', None)
        st.rerun()

    df_reembolsos = st.session_state.df_reembolsos
    
    # --- PÁGINA: SOLICITAR REEMBOLSO ---
    if menu_option == "📝 Solicitar Reembolso":
        st.markdown("""
            <div class='header-container'>
                <h1>📝 SOLICITAR REEMBOLSO</h1>
                <p>Preencha o formulário para enviar sua solicitação de reembolso.</p>
            </div>
        """, unsafe_allow_html=True)

        # Filtra os dados para o usuário logado
        df_reembolsos_usuario = df_reembolsos[df_reembolsos['NOME'] == st.session_state.nome_colaborador].copy()
        
        if not df_reembolsos_usuario.empty:
            df_reembolsos_usuario['VALOR'] = pd.to_numeric(df_reembolsos_usuario['VALOR'], errors='coerce').fillna(0)
            
            # --- MÉTRICAS DO USUÁRIO NA PÁGINA DE SOLICITAÇÃO ---
            total_pedidos = len(df_reembolsos_usuario)
            pedidos_pendentes = len(df_reembolsos_usuario[df_reembolsos_usuario['STATUS'] == 'PENDENTE'])
            pedidos_atendidos = total_pedidos - pedidos_pendentes
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Pedidos", total_pedidos)
            with col2:
                st.metric("Pedidos Pendentes", pedidos_pendentes)
            with col3:
                st.metric("Pedidos Atendidos", pedidos_atendidos)
            
            st.markdown("---")

        with st.expander("➕ Adicionar Nova Solicitação", expanded=True):
            st.subheader("Dados do Colaborador")
            nome_colaborador = st.text_input("Seu Nome Completo*", value=st.session_state.get('nome_colaborador', ''), disabled=True, key="nome_form")
            departamento = st.selectbox("Custo / Departamento*", options=DEPARTAMENTOS, key="depto_form")
            
            st.subheader("Detalhes dos Reembolsos")
            
            reembolsos_validos = True
            
            for i in range(len(st.session_state.reembolsos_a_enviar)):
                st.markdown(f"---")
                st.markdown(f"**Reembolso #{i + 1}**")

                tipo_despesa = st.selectbox(f"Tipo de Despesa* #{i + 1}", options=TIPOS_DESPESA, key=f"tipo_despesa_{i}")
                col_data, col_valor = st.columns(2)
                with col_data:
                    data_despesa = st.date_input(f"Data da Despesa* #{i + 1}", datetime.date.today(), key=f"data_despesa_{i}")
                with col_valor:
                    valor_reembolso = st.number_input(
                        f"Valor da Despesa (R$)* #{i + 1}", 
                        min_value=0.01, 
                        format="%.2f",
                        step=0.01,
                        key=f"valor_reembolso_{i}"
                    )
                justificativa = st.text_area(f"Justificativa* #{i + 1}", placeholder="Explique o motivo da despesa.", key=f"justificativa_{i}")
                comprovantes = st.file_uploader(
                    f"Anexe os Comprovantes (Recibos, Notas Fiscais)* #{i + 1}",
                    type=['pdf', 'jpg', 'jpeg', 'png'],
                    accept_multiple_files=True,
                    key=f"comprovantes_{i}"
                )

                st.session_state.reembolsos_a_enviar[i] = {
                    "tipo_despesa": tipo_despesa,
                    "data_despesa": data_despesa,
                    "valor_reembolso": valor_reembolso,
                    "justificativa": justificativa,
                    "comprovantes": comprovantes
                }

            col_add_send = st.columns(2)

            with col_add_send[0]:
                if st.button("➕ Adicionar Outro Reembolso", use_container_width=True):
                    st.session_state.reembolsos_a_enviar.append({})
                    st.rerun()
            
            with col_add_send[1]:
                if st.button("✅ Enviar Todas as Solicitações", key="enviar_todos", use_container_width=True):
                    reembolsos_validos = True
                    
                    for i, reembolso in enumerate(st.session_state.reembolsos_a_enviar):
                        if not all([st.session_state.nome_form, st.session_state.depto_form, reembolso['tipo_despesa'], reembolso['valor_reembolso'], reembolso['justificativa'], reembolso['comprovantes']]):
                            st.error(f"⚠️ Por favor, preencha todos os campos obrigatórios para o Reembolso #{i+1} e anexe os comprovantes.")
                            reembolsos_validos = False
                            break
                        elif reembolso['valor_reembolso'] <= 0:
                            st.error(f"⚠️ O valor do Reembolso #{i+1} deve ser maior que zero.")
                            reembolsos_validos = False
                            break
                    
                    if reembolsos_validos:
                        novos_registros = []
                        comprovante_links = []
                        for reembolso in st.session_state.reembolsos_a_enviar:
                            nomes_comprovantes = []
                            for comprovante in reembolso['comprovantes']:
                                link = upload_to_drive(comprovante, PASTA_DRIVE_ID)
                                if link:
                                    nomes_comprovantes.append(f"{comprovante.name}")
                                    comprovante_links.append(f"[{comprovante.name}]({link})")
                            
                            novo_registro = {
                                "DATA": reembolso['data_despesa'].strftime("%d/%m/%Y"),
                                "NOME": st.session_state.nome_form,
                                "DEPARTAMENTO": st.session_state.depto_form,
                                "TIPO_DESPESA": reembolso['tipo_despesa'],
                                "VALOR": reembolso['valor_reembolso'],
                                "JUSTIFICATIVA": reembolso['justificativa'],
                                "STATUS": "PENDENTE",
                                "ID_COMPROVANTE": ", ".join(comprovante_links)
                            }
                            novos_registros.append(novo_registro)
                        
                        df_novos_registros = pd.DataFrame(novos_registros)
                        st.session_state.df_reembolsos = pd.concat([st.session_state.df_reembolsos, df_novos_registros], ignore_index=True)

                        if salvar_dados_reembolsos(st.session_state.df_reembolsos):
                            st.success("🎉 Todas as solicitações de reembolso foram registradas com sucesso!")
                            
                            # Envio de e-mails
                            user_email = st.session_state.get('email_colaborador', '')
                            admin_email = "earaujo@essencis.com.br"
                            
                            if user_email:
                                subject_user = "Confirmação de Solicitação de Reembolso"
                                body_user = f"""
                                Olá {st.session_state.nome_form},<br><br>
                                Sua solicitação de reembolso foi registrada com sucesso.<br>
                                Acompanhe o status pelo dashboard do sistema.<br><br>
                                Atenciosamente,<br>
                                Equipe de Reembolsos
                                """
                                send_email(user_email, subject_user, body_user)
                            
                            subject_admin = f"Novo Reembolso Registrado - {st.session_state.nome_colaborador}"
                            body_admin = f"""
                            Olá,<br><br>
                            Um novo reembolso foi registrado por {st.session_state.nome_colaborador} ({st.session_state.depto_form}).<br><br>
                            **Detalhes do(s) Reembolso(s):**<br>
                            {df_novos_registros.to_html(index=False)}<br><br>
                            Acesse o sistema para analisar as solicitações.<br><br>
                            Atenciosamente,<br>
                            Sistema de Reembolsos
                            """
                            send_email(admin_email, subject_admin, body_admin)

                            st.session_state.reembolsos_a_enviar = [{}] # Limpa o formulário
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar os dados. Tente novamente.")
        
        st.markdown("---")
        
        # --- EXIBE O HISTÓRICO DO USUÁRIO NA PRÓPRIA PÁGINA ---
        st.subheader("Suas Solicitações Enviadas Recentemente")
        if not df_reembolsos_usuario.empty:
            df_usuario = df_reembolsos_usuario.copy()
            df_usuario['VALOR'] = df_usuario['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_usuario, use_container_width=True)
        else:
            st.info("Você ainda não enviou nenhuma solicitação de reembolso.")


    # --- PÁGINA: DASHBOARD ---
    elif menu_option == "📊 Dashboard":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 DASHBOARD DE REEMBOLSOS</h1>
                <p>Análise do fluxo de solicitações e custos.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if not df_reembolsos.empty:
            
            # Filtra os dados para o usuário logado
            df_reembolsos_usuario = df_reembolsos[df_reembolsos['NOME'] == st.session_state.nome_colaborador].copy()
            
            if df_reembolsos_usuario.empty:
                st.info("Você ainda não tem dados para o dashboard. Envie sua primeira solicitação de reembolso!")
            else:
                df_reembolsos_usuario['VALOR'] = pd.to_numeric(df_reembolsos_usuario['VALOR'], errors='coerce').fillna(0)
            
                # --- MÉTRICAS DO USUÁRIO ---
                st.subheader(f"Resumo das suas solicitações, {st.session_state.nome_colaborador}")
                total_pedidos = len(df_reembolsos_usuario)
                pedidos_pendentes = len(df_reembolsos_usuario[df_reembolsos_usuario['STATUS'] == 'PENDENTE'])
                pedidos_atendidos = total_pedidos - pedidos_pendentes
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Pedidos", total_pedidos)
                with col2:
                    st.metric("Pedidos Pendentes", pedidos_pendentes)
                with col3:
                    st.metric("Pedidos Atendidos", pedidos_atendidos)
                
                st.markdown("---")
                
                valor_total_solicitado = df_reembolsos_usuario['VALOR'].sum()
                
                col_metrica1, col_metrica2 = st.columns(2)
                with col_metrica1:
                    st.metric("Valor Total Solicitado", f"R$ {valor_total_solicitado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                with col_metrica2:
                    if total_pedidos > 0:
                        st.metric("Média por Reembolso", f"R$ {df_reembolsos_usuario['VALOR'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    else:
                        st.metric("Média por Reembolso", "R$ 0,00")
                
                st.subheader("Distribuição das suas Despesas por Tipo")
                dep_val = df_reembolsos_usuario.groupby('TIPO_DESPESA')['VALOR'].sum().reset_index()
                fig = px.bar(dep_val, x='TIPO_DESPESA', y='VALOR', title="Valor de Reembolso por Tipo de Despesa")
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Status das suas Solicitações")
                status_count = df_reembolsos_usuario['STATUS'].value_counts().reset_index()
                status_count.columns = ['Status', 'Quantidade']
                fig_pizza = px.pie(status_count, values='Quantidade', names='Status', title='Status das suas Solicitações')
                st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Nenhum dado de reembolso disponível para análise. Envie sua primeira solicitação!")

    # --- PÁGINA: CONSULTAR REEMBOLSOS ---
    elif menu_option == "🔍 Consultar":
        st.markdown("""
            <div class='header-container'>
                <h1>🔍 CONSULTAR SOLICITAÇÕES</h1>
                <p>Acompanhe e filtre as solicitações de reembolso.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if not df_reembolsos.empty:
            df_consulta = df_reembolsos.copy()
            df_consulta['VALOR'] = pd.to_numeric(df_consulta['VALOR'], errors='coerce').fillna(0)

            col1, col2 = st.columns(2)
            with col1:
                nome_consulta = st.text_input("Buscar por Nome", placeholder="Digite o nome do colaborador...")
            with col2:
                status_options = ["TODOS"] + sorted(df_reembolsos['STATUS'].dropna().unique().tolist())
                status_consulta = st.selectbox("Filtrar por Status", options=status_options)

            # Aplica os filtros
            if nome_consulta:
                df_consulta = df_consulta[df_consulta['NOME'].str.contains(nome_consulta, case=False, na=False)]
            if status_consulta != "TODOS":
                df_consulta = df_consulta[df_consulta['STATUS'] == status_consulta]
            
            # Formata a coluna de data para o padrão brasileiro
            if 'DATA' in df_consulta.columns:
                df_consulta['DATA'] = pd.to_datetime(df_consulta['DATA'], format='%d/%m/%Y', errors='coerce').dt.strftime('%d/%m/%Y')
            
            # Exibe a tabela com a coluna de links clicáveis
            st.dataframe(
                df_consulta, 
                use_container_width=True,
                column_config={
                    "ID_COMPROVANTE": st.column_config.LinkColumn(
                        "Comprovante",
                        help="Clique para baixar o comprovante",
                        display_text="📥 Download"
                    )
                }
            )

            csv_download = df_consulta.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download dos Resultados",
                data=csv_download,
                file_name='reembolsos_filtrados.csv',
                mime='text/csv'
            )

    # --- PÁGINA: CONFIGURAÇÕES ---
    elif menu_option == "⚙️ Configurações":
        st.markdown("""
            <div class='header-container'>
                <h1>⚙️ CONFIGURAÇÕES DO SISTEMA</h1>
                <p>Gerenciamento e manutenção dos dados.</p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Manutenção de Dados")
        if st.button("🔄 Recarregar Dados"):
            st.session_state.df_reembolsos = carregar_dados_reembolsos()
            st.success("Dados recarregados com sucesso!")
            st.rerun()

        st.subheader("Download de Backup")
        csv_backup = df_reembolsos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Fazer Backup de Reembolsos",
            data=csv_backup,
            file_name=f"backup_reembolsos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
