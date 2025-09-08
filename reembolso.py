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

# Carrega os segredos do arquivo secrets.toml
try:
    with open(".streamlit/secrets.toml", "r") as f:
        secrets_dict = toml.load(f)
except FileNotFoundError:
    st.error("O arquivo .streamlit/secrets.toml não foi encontrado.")
    st.stop()

# --- Configuração do Layout e Tema ---
st.set_page_config(page_title="Gestão de Reembolsos", layout="wide", page_icon="💰")

# --- Configuração de Dados e Lógica de Backend (Google Sheets e APIs) ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]

@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=3600)
def get_google_api_service():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"],
        ['https://www.googleapis.com/auth/gmail.send']
    )
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service

gs_client = get_gspread_client()
gmail_service = get_google_api_service()

def get_reembolsos_sheet():
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Reembolsos")
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de autenticação ou acesso à planilha: {e}. Por favor, verifique as permissões.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Reembolsos' não foi encontrada na planilha.")
        return None

# --- Funções para Envio de E-mail ---
def create_message(sender, to, subject, message_text):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    msg = MIMEText(message_text)
    message.attach(msg)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        st.success(f"E-mail enviado com sucesso!")
        return message
    except Exception as e:
        st.error(f"Ocorreu um erro ao enviar o e-mail: {e}")
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
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 60)
        if 'signedURL' in response:
            return response['signedURL']
        else:
            st.error(f"Erro ao gerar URL assinada: {response}")
            return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar gerar a URL: {e}")
        return None

# --- Funções do Aplicativo ---

def load_reembolsos_data():
    sheet = get_reembolsos_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
        return df
    return pd.DataFrame()

def add_reembolso(data, nome, departamento, tipo_despesa, valor, justificativa, caminho_recibo, status="Pendente"):
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        try:
            row = [data_formatada, nome, departamento, tipo_despesa, valor, justificativa, status, caminho_recibo]
            sheet.append_row(row)
            st.success("Reembolso adicionado com sucesso!")
            
            # 1. Envia e-mail para o usuário
            user_email = nome # Supondo que 'NOME' seja o e-mail do usuário
            subject_user = "Confirmação de Envio de Reembolso"
            body_user = f"""
            Olá, {nome}!
            
            Seu pedido de reembolso foi enviado com sucesso e está em análise.
            
            Detalhes do Reembolso:
            - Data: {data_formatada}
            - Departamento: {departamento}
            - Tipo de Despesa: {tipo_despesa}
            - Valor: R$ {valor:,.2f}
            - Justificativa: {justificativa}
            
            Em breve, você receberá uma notificação sobre o status do seu pedido.
            
            Atenciosamente,
            Equipe de Reembolsos
            """
            message_user = create_message("me", user_email, subject_user, body_user)
            send_message(gmail_service, "me", message_user)

            # 2. Envia e-mail para o administrador
            admin_email = "earaujo@essencis.com.br"
            subject_admin = f"Novo Reembolso Pendente de {nome}"
            body_admin = f"""
            Olá, Administrador(a)!
            
            Um novo pedido de reembolso foi submetido e está aguardando sua aprovação.
            
            Detalhes do Reembolso:
            - Solicitante: {nome}
            - Data: {data_formatada}
            - Departamento: {departamento}
            - Tipo de Despesa: {tipo_despesa}
            - Valor: R$ {valor:,.2f}
            - Justificativa: {justificativa}
            - ID do Anexo: {caminho_recibo}
            
            Por favor, acesse o painel de gerenciamento para analisar este pedido.
            
            Atenciosamente,
            Sistema de Reembolsos
            """
            message_admin = create_message("me", admin_email, subject_admin, body_admin)
            send_message(gmail_service, "me", message_admin)

        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")

# --- Interface do Usuário (Streamlit) ---
st.title("💰 Gestão de Reembolsos")

menu = st.sidebar.selectbox("Menu Principal", ["Dashboard", "Adicionar Reembolso", "Meu Histórico"])

# --- Seção do Dashboard ---
if menu == "Dashboard":
    st.header("Resumo dos Reembolsos")
    st.info("O dashboard para o usuário é um resumo geral e não exibe dados individuais.")
    df_reembolsos = load_reembolsos_data()
    
    if not df_reembolsos.empty:
        if 'STATUS' in df_reembolsos.columns:
            fig_status = px.bar(df_reembolsos['STATUS'].value_counts(),
                                 title="Total de Reembolsos por Status",
                                 labels={'index': 'STATUS', 'value': 'Quantidade'})
            st.plotly_chart(fig_status)
        else:
            st.warning("Coluna 'STATUS' não encontrada nos dados.")
        
        st.subheader("Estatísticas")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Reembolsos", len(df_reembolsos))
        with col2:
            if 'VALOR' in df_reembolsos.columns:
                total_valor = df_reembolsos['VALOR'].sum()
                st.metric("Valor Total", f"R$ {total_valor:,.2f}")
        with col3:
            if 'STATUS' in df_reembolsos.columns:
                pendentes = df_reembolsos[df_reembolsos['STATUS'] == 'Pendente'].shape[0]
                st.metric("Pendentes", pendentes)
    else:
        st.warning("Não há dados de reembolso para exibir.")

# --- Seção de Adicionar Reembolso ---
elif menu == "Adicionar Reembolso":
    st.header("Adicionar Novo Reembolso")
    
    # Lista de tipos de despesa e custos
    tipos_despesa = ["Aéreo", "Combustível", "Hospedagem", "Pedágio", "Alimentação", "Outros"]
    
    with st.form("form_reembolso"):
        nome_funcionario = st.text_input("Nome Completo")
        email_funcionario = st.text_input("E-mail (Para Notificação)")
        departamento = st.text_input("Departamento")
        tipo_despesa_selecionada = st.selectbox("Tipo de Despesa", tipos_despesa)
        valor_reembolso = st.number_input("Valor", min_value=0.01, format="%.2f")
        justificativa = st.text_area("Justificativa")
        data_reembolso = st.date_input("Data", value=datetime.date.today())
        
        recibo_anexo = st.file_uploader("Comprovante (Imagem ou PDF)", type=["jpg", "jpeg", "png", "pdf"])
        
        submit_button = st.form_submit_button("Salvar Reembolso")
        
        if submit_button:
            if nome_funcionario and email_funcionario and valor_reembolso and data_reembolso and departamento and tipo_despesa_selecionada and justificativa:
                caminho_recibo = None
                if recibo_anexo:
                    try:
                        caminho_recibo = upload_to_supabase(recibo_anexo)
                        if not caminho_recibo:
                            st.warning("Upload do arquivo falhou, mas o reembolso será salvo sem anexo.")
                    except Exception as e:
                        st.warning(f"Erro no upload: {e}. O reembolso será salvo sem anexo.")
                
                # Use o e-mail como 'nome' para a função de e-mail, mas o nome real para a planilha
                add_reembolso(data_reembolso, nome_funcionario, departamento, tipo_despesa_selecionada, 
                              valor_reembolso, justificativa, caminho_recibo)
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# --- Seção Meu Histórico ---
elif menu == "Meu Histórico":
    st.header("Meu Histórico de Reembolsos")
    
    # Simula a autenticação para saber quem é o usuário
    # Em uma aplicação real, você usaria um sistema de login
    usuario_atual = st.text_input("Digite seu Nome para ver o histórico:")
    
    if usuario_atual:
        df_reembolsos = load_reembolsos_data()
        
        if not df_reembolsos.empty and 'NOME' in df_reembolsos.columns:
            # Filtra os reembolsos pelo nome do usuário
            df_usuario = df_reembolsos[df_reembolsos['NOME'].str.lower() == usuario_atual.lower()]
            
            if not df_usuario.empty:
                st.write(df_usuario[['DATA', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS']])
            else:
                st.info("Nenhum reembolso encontrado para este nome.")
        else:
            st.warning("Não foi possível carregar os dados de reembolso.")
