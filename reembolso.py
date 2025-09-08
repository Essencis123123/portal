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

# --- Configuração de Dados e Lógica de Backend (Google Sheets) ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]

# Conexão com Google Sheets (gspread)
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

# Conexão com Gmail API (mantida para envio de e-mails)
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

def get_sheet():
    try:
        sheet = gs_client.open_by_key(SHEET_ID).sheet1
        return sheet
    except gspread.exceptions.APIError as e:
        st.error(f"Erro de autenticação ou acesso à planilha: {e}. Por favor, verifique as permissões.")
        return None

def send_email_with_attachment(to, subject, body, attachment_path=None):
    # ... (Seu código de envio de e-mail) ...
    pass

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
supabase_key = secrets_dict["supabase"]["key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

# Função para fazer upload para o Supabase Storage
def upload_to_supabase(file_uploader, bucket_name="reembolsos-anexos"):
    if file_uploader is not None:
        try:
            file_name = file_uploader.name
            unique_file_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
            file_bytes = file_uploader.read()
            
            response = supabase_client.storage.from_(bucket_name).upload(path=unique_file_name, file=file_bytes, file_options={"content-type": file_uploader.type})
            
            if response.status_code == 200:
                st.success("Arquivo enviado com sucesso para o Supabase!")
                return unique_file_name
            else:
                st.error(f"Falha ao enviar o arquivo: {response.text}")
                return None
        except Exception as e:
            st.error(f"Ocorreu um erro no upload: {e}")
            return None
    return None

# Função para obter URL assinada de um arquivo privado
def get_signed_url(file_path, bucket_name="reembolsos-anexos"):
    try:
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 60) # 60s de validade
        if 'signedURL' in response:
            return response['signedURL']
        else:
            st.error(f"Erro ao gerar URL assinada: {response}")
            return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar gerar a URL: {e}")
        return None

# --- Funções do Aplicativo ---

# Função para carregar dados do Google Sheets
def load_data():
    sheet = get_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce').dt.date
        return df
    return pd.DataFrame()

# Função para adicionar novo reembolso
def add_reembolso(data, nome, valor, caminho_recibo, status="Pendente"):
    sheet = get_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        try:
            row = [data_formatada, nome, valor, status, caminho_recibo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            sheet.append_row(row)
            st.success("Reembolso adicionado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")

# --- Interface do Usuário (Streamlit) ---
st.title("💰 Gestão de Reembolsos")

menu = st.sidebar.selectbox("Menu Principal", ["Dashboard", "Adicionar Reembolso", "Gerenciar Reembolsos"])

# --- Seção do Dashboard ---
if menu == "Dashboard":
    st.header("Resumo dos Reembolsos")
    df_reembolsos = load_data()
    if not df_reembolsos.empty:
        # Gráfico de status
        fig_status = px.bar(df_reembolsos['Status'].value_counts(),
                            title="Total de Reembolsos por Status",
                            labels={'index': 'Status', 'value': 'Quantidade'})
        st.plotly_chart(fig_status)
    else:
        st.warning("Não há dados de reembolso para exibir.")

# --- Seção de Adicionar Reembolso ---
elif menu == "Adicionar Reembolso":
    st.header("Adicionar Novo Reembolso")
    
    with st.form("form_reembolso"):
        nome_funcionario = st.text_input("Nome do Funcionário")
        valor_reembolso = st.number_input("Valor do Reembolso", min_value=0.01, format="%.2f")
        data_reembolso = st.date_input("Data do Reembolso", value=datetime.date.today())
        
        # Campo para o anexo do recibo
        recibo_anexo = st.file_uploader("Anexar Recibo", type=["jpg", "jpeg", "png", "pdf"])
        
        submit_button = st.form_submit_button("Salvar Reembolso")
        
        if submit_button:
            if nome_funcionario and valor_reembolso and data_reembolso:
                # 1. Faz o upload do arquivo para o Supabase Storage
                caminho_recibo = None
                if recibo_anexo:
                    caminho_recibo = upload_to_supabase(recibo_anexo)
                
                # 2. Salva os dados no Google Sheets
                if caminho_recibo or not recibo_anexo:
                    add_reembolso(data_reembolso, nome_funcionario, valor_reembolso, caminho_recibo)
                else:
                    st.warning("O reembolso não foi salvo pois o upload do arquivo falhou.")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# --- Seção de Gerenciar Reembolsos (com visualização do recibo) ---
elif menu == "Gerenciar Reembolsos":
    st.header("Gerenciar Reembolsos")
    
    df_reembolsos = load_data()

    if not df_reembolsos.empty:
        # Crie uma nova coluna 'Recibo' que contém o caminho do arquivo
        df_reembolsos['Recibo'] = df_reembolsos['Caminho Recibo'].apply(lambda x: "Ver Recibo" if x else "N/A")
        
        # Renomeie a coluna original para esconder na visualização principal
        df_reembolsos.rename(columns={'Caminho Recibo': 'Caminho_Recibo_Original'}, inplace=True)
        
        colunas_para_exibir = ['Data', 'Nome', 'Valor', 'Status', 'Recibo']
        
        edited_df = st.data_editor(
            df_reembolsos[colunas_para_exibir],
            column_config={
                "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                "Recibo": st.column_config.LinkColumn("Recibo", display_text="Ver Recibo", help="Clique para ver o recibo.")
            },
            hide_index=True,
        )

        st.info("Para ver o recibo, clique no link 'Ver Recibo' na tabela.")

        # Lógica para mostrar o recibo quando o usuário interage
        if 'last_edited_cell' in st.session_state:
            cell_info = st.session_state.last_edited_cell
            if cell_info and cell_info['column_name'] == 'Recibo':
                row_index = cell_info['row_index']
                caminho_recibo = df_reembolsos.iloc[row_index]['Caminho_Recibo_Original']
                
                if caminho_recibo:
                    st.subheader(f"Recibo para {df_reembolsos.iloc[row_index]['Nome']}")
                    # Gera a URL assinada e exibe a imagem
                    url_recibo = get_signed_url(caminho_recibo)
                    if url_recibo:
                        st.image(url_recibo, caption="Recibo do Reembolso")
                    else:
                        st.error("Não foi possível carregar a imagem do recibo.")
                else:
                    st.warning("Não há recibo anexado para este reembolso.")
