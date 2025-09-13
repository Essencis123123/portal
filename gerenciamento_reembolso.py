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
    st.session_state.current_user = {'NOME': 'Admin', 'EMAIL': 'earaujo@essencis.com.br'} # Define o usuário padrão
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

# --- Funções para Envio de E-mail ---
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

# --- Funções para Área Administrativa ---
def update_reembolso_status(index, novo_status, email_usuario, nome_usuario):
    """Atualiza o status do reembolso e envia notificação"""
    try:
        sheet = get_reembolsos_sheet()
        if sheet:
            # A planilha começa na linha 2 (linha 1 é cabeçalho)
            row_number = index + 2
            
            # Atualiza o status na planilha
            sheet.update_cell(row_number, 7, novo_status) # Coluna 7 é STATUS
            
            st.success(f"Status atualizado para '{novo_status}'!")
            
            # Enviar notificação por email
            enviar_notificacao_status(email_usuario, nome_usuario, novo_status)
            
            # Atualizar a página
            st.rerun()
            
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")

def save_observacao(index, observacao, email_usuario, nome_usuario):
    """Salva observações no reembolso"""
    try:
        sheet = get_reembolsos_sheet()
        if sheet and observacao:
            # A planilha começa na linha 2 (linha 1 é cabeçalho)
            row_number = index + 2
            
            # Supondo que a coluna 10 seja para observações
            sheet.update_cell(row_number, 10, observacao)
            
            st.success("Observações salvas com sucesso!")
            
            # Enviar email com observações
            enviar_observacao_email(email_usuario, nome_usuario, observacao)
            
    except Exception as e:
        st.error(f"Erro ao salvar observações: {e}")

def enviar_notificacao_status(email_destinatario, nome, novo_status):
    """Envia email de notificação de mudança de status"""
    try:
        if st.session_state.gmail_service and st.session_state.user_email_oauth:
            subject = f"Status do seu reembolso foi atualizado para: {novo_status}"
            
            body = f"""
            <p>Olá, {nome}!</p>
            <p>O status do seu pedido de reembolso foi atualizado.</p>
            <p><b>Novo Status:</b> {novo_status}</p>
            """
            
            if novo_status == "Pago":
                body += """
                <p>✅ <b>Seu reembolso foi processado e pago!</b></p>
                <p>O valor será creditado em sua conta conforme o prazo estabelecido.</p>
                """
            elif novo_status == "Aprovado":
                body += """
                <p>📋 Seu reembolso foi aprovado e está na fila para pagamento.</p>
                <p>Você receberá uma nova notificação quando o pagamento for realizado.</p>
                """
            elif novo_status == "Rejeitado":
                body += """
                <p>❌ Seu reembolso não foi aprovado.</p>
                <p>Entre em contato com o departamento financeiro para mais informações.</p>
                """
            
            body += """
            <p>Atenciosamente,<br>Departamento Financeiro Essencis</p>
            """
            
            message = create_message(st.session_state.user_email_oauth, email_destinatario, subject, body)
            send_message(st.session_state.gmail_service, 'me', message)
            
    except Exception as e:
        st.error(f"Erro ao enviar notificação: {e}")

def enviar_observacao_email(email_destinatario, nome, observacao):
    """Envia email com observações do administrador"""
    try:
        if st.session_state.gmail_service and st.session_state.user_email_oauth:
            subject = f"Observações sobre seu reembolso - Essencis"
            
            body = f"""
            <p>Olá, {nome}!</p>
            <p>O administrador adicionou uma observação ao seu pedido de reembolso:</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0;">
                <p><b>Observação:</b></p>
                <p>{observacao}</p>
            </div>
            <p>Acesse a plataforma para visualizar seu reembolso completo.</p>
            <p>Atenciosamente,<br>Departamento Financeiro Essencis</p>
            """
            
            message = create_message(st.session_state.user_email_oauth, email_destinatario, subject, body)
            send_message(st.session_state.gmail_service, 'me', message)
            
    except Exception as e:
        st.error(f"Erro ao enviar email com observações: {e}")

def download_relatorio():
    """Gera e disponibiliza relatório em Excel"""
    try:
        df_reembolsos = load_reembolsos_data()
        
        if not df_reembolsos.empty:
            # Criar um arquivo Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_reembolsos.to_excel(writer, sheet_name='Reembolsos', index=False)
                
                # Formatação
                workbook = writer.book
                worksheet = writer.sheets['Reembolsos']
                
                # Formatar coluna de valores
                money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
                worksheet.set_column('E:E', 15, money_format) # Coluna E = VALOR
                
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📊 Baixar Relatório Completo (Excel)",
                data=output,
                file_name=f"relatorio_reembolsos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")

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
                        st.warning("Token ID não disponível. Usando email padrão.")
                        st.session_state.user_email_oauth = "noreply@essencis.com.br"
                    
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

# --- Layout do Aplicativo ---
st.title("💰 Gestão de Reembolsos Essencis")

# Acesso direto para o admin
if st.session_state.current_user['EMAIL'].lower() == "earaujo@essencis.com.br":
    st.sidebar.header(f"Bem-vindo, Administrador!")
    st.sidebar.button("Sair", on_click=lambda: st.session_state.clear() or st.rerun())

    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Área Administrativa"],
        icons=["house", "gear"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )

    if menu == "Dashboard":
        st.header("Resumo dos Reembolsos da Empresa")
        df_reembolsos = load_reembolsos_data()
        if not df_reembolsos.empty:
            st.subheader("Estatísticas Gerais")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Reembolsos", len(df_reembolsos))
            with col2:
                total_valor = df_reembolsos['VALOR'].sum()
                st.metric("Valor Total", f"R$ {total_valor:,.2f}")
            with col3:
                pendentes = df_reembolsos[df_reembolsos['STATUS'] == 'Pendente'].shape[0]
                st.metric("Pendentes", pendentes)

            st.subheader("Custo por Departamento")
            df_depto = df_reembolsos.groupby('DEPARTAMENTO')['VALOR'].sum().reset_index()
            fig_depto = px.bar(df_depto, x='DEPARTAMENTO', y='VALOR', 
                               title="Custo por Departamento",
                               labels={'VALOR': 'Valor (R$)', 'DEPARTAMENTO': 'Departamento'})
            st.plotly_chart(fig_depto, use_container_width=True)

            st.subheader("Custo por Tipo de Despesa")
            df_despesa = df_reembolsos.groupby('TIPO_DESPESA')['VALOR'].sum().reset_index()
            fig_despesa = px.bar(df_despesa, x='TIPO_DESPESA', y='VALOR', 
                                 title="Custo por Tipo de Despesa",
                                 labels={'VALOR': 'Valor (R$)', 'TIPO_DESPESA': 'Tipo de Despesa'})
            st.plotly_chart(fig_despesa, use_container_width=True)

            fig_status = px.bar(df_reembolsos['STATUS'].value_counts(),
                                 title="Reembolsos por Status",
                                 labels={'index': 'STATUS', 'value': 'Quantidade'})
            st.plotly_chart(fig_status)
        else:
            st.info("Nenhum reembolso encontrado para exibir no dashboard.")
    
    elif menu == "Área Administrativa":
        st.header("📊 Área Administrativa - Gestão de Reembolsos")
        
        # Carregar dados
        df_reembolsos = load_reembolsos_data()
        
        if df_reembolsos.empty:
            st.info("Nenhum reembolso encontrado.")
            st.stop()
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "Filtrar por Status",
                ["Todos", "Pendente", "Aprovado", "Pago", "Rejeitado"]
            )
        with col2:
            departamento_filter = st.selectbox(
                "Filtrar por Departamento",
                ["Todos"] + DEPARTAMENTOS
            )
        with col3:
            data_filter = st.date_input(
                "Filtrar por Data",
                value=None,
                help="Deixe em branco para todas as datas"
            )
        
        # Aplicar filtros
        filtered_df = df_reembolsos.copy()
        
        if status_filter != "Todos":
            filtered_df = filtered_df[filtered_df['STATUS'] == status_filter]
        
        if departamento_filter != "Todos":
            filtered_df = filtered_df[filtered_df['DEPARTAMENTO'] == departamento_filter]
        
        if data_filter:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['DATA']) == pd.to_datetime(data_filter)]
        
        # Estatísticas rápidas
        st.subheader("📈 Estatísticas Gerais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = len(df_reembolsos)
            st.metric("Total de Reembolsos", total)
        
        with col2:
            pendentes = len(df_reembolsos[df_reembolsos['STATUS'] == 'Pendente'])
            st.metric("Pendentes", pendentes)
        
        with col3:
            valor_total = df_reembolsos['VALOR'].sum()
            st.metric("Valor Total", f"R$ {valor_total:,.2f}")
        
        with col4:
            valor_pendente = df_reembolsos[df_reembolsos['STATUS'] == 'Pendente']['VALOR'].sum()
            st.metric("Valor Pendente", f"R$ {valor_pendente:,.2f}")
        
        # Lista de reembolsos
        st.subheader("📋 Lista de Reembolsos")
        
        if filtered_df.empty:
            st.info("Nenhum reembolso corresponde aos filtros aplicados.")
        else:
            for index, row in filtered_df.iterrows():
                with st.expander(f"Reembolso #{index+1} - {row['NOME']} - R$ {row['VALOR']:,.2f} - {row['STATUS']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Solicitante:** {row['NOME']}")
                        st.write(f"**Email:** {row['EMAIL']}")
                        st.write(f"**Departamento:** {row['DEPARTAMENTO']}")
                        st.write(f"**Data:** {row['DATA']}")
                    
                    with col2:
                        st.write(f"**Tipo de Despesa:** {row['TIPO_DESPESA']}")
                        st.write(f"**Valor:** R$ {row['VALOR']:,.2f}")
                        st.write(f"**Status:** {row['STATUS']}")
                        st.write(f"**Justificativa:** {row['JUSTIFICATIVA']}")
                    
                    # Visualizar comprovante
                    if pd.notna(row['ID_COMPROVANTE']) and row['ID_COMPROVANTE'] != '':
                        st.subheader("📎 Comprovante")
                        
                        try:
                            signed_url = get_signed_url(row['ID_COMPROVANTE'])
                            if signed_url:
                                if row['ID_COMPROVANTE'].lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(signed_url, caption="Comprovante", use_column_width=True)
                                elif row['ID_COMPROVANTE'].lower().endswith('.pdf'):
                                    st.markdown(f"[📄 Baixar PDF]({signed_url})")
                                else:
                                    st.markdown(f"[📎 Baixar Arquivo]({signed_url})")
                                
                                #st.markdown(f"**Link do comprovante:** [{signed_url}]({signed_url})")
                            else:
                                st.warning("Não foi possível gerar o link do comprovante.")
                        except Exception as e:
                            st.error(f"Erro ao carregar comprovante: {e}")
                    else:
                        st.info("Nenhum comprovante anexado.")
                    
                    # Controles administrativos
                    st.subheader("⚙️ Ações Administrativas")
                    
                    col_act1, col_act2, col_act3 = st.columns(3)
                    
                    with col_act1:
                        if st.button(f"✅ Aprovar", key=f"approve_{index}"):
                            update_reembolso_status(index, "Aprovado", row['EMAIL'], row['NOME'])
                    
                    with col_act2:
                        if st.button(f"💰 Marcar como Pago", key=f"pay_{index}"):
                            update_reembolso_status(index, "Pago", row['EMAIL'], row['NOME'])
                    
                    with col_act3:
                        if st.button(f"❌ Rejeitar", key=f"reject_{index}"):
                            update_reembolso_status(index, "Rejeitado", row['EMAIL'], row['NOME'])
                    
                    # Campo para observações
                    observacao = st.text_area("Observações (opcional)", key=f"obs_{index}")
                    
                    if st.button("💾 Salvar Observações", key=f"save_obs_{index}"):
                        save_observacao(index, observacao, row['EMAIL'], row['NOME'])
        
        # Ferramentas administrativas
        st.divider()
        st.subheader("📦 Ferramentas Administrativas")
        
        col_tool1, col_tool2 = st.columns(2)
        
        with col_tool1:
            download_relatorio()
        
        with col_tool2:
            if st.button("🔄 Atualizar Dados"):
                st.rerun()

else:
    st.error("Acesso restrito. Este aplicativo é apenas para uso administrativo.")
