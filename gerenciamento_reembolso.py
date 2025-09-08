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
st.set_page_config(page_title="Gestão de Reembolsos (Admin)", layout="wide", page_icon="🔑")

# --- Autenticação de Admin ---
st.sidebar.header("Login do Administrador")
password = st.sidebar.text_input("Senha", type="password")
if password == secrets_dict.get("admin", {}).get("password"):
    st.sidebar.success("Login bem-sucedido!")
    admin_logged_in = True
else:
    st.sidebar.error("Senha incorreta.")
    admin_logged_in = False

if not admin_logged_in:
    st.warning("Por favor, faça login para acessar o painel de gerenciamento.")
    st.stop()

# --- Configuração de Dados e Lógica de Backend ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"]

@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

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

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
supabase_key = secrets_dict["supabase"]["service_role_key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

def get_signed_url(file_path, bucket_name="reembolsos-anexos"):
    try:
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 3600) # 1h de validade
        if 'signedURL' in response:
            return response['signedURL']
        else:
            return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar gerar a URL: {e}")
        return None

def delete_supabase_file(file_path, bucket_name="reembolsos-anexos"):
    try:
        response = supabase_client.storage.from_(bucket_name).remove([file_path])
        if response:
            st.success(f"Arquivo '{file_path}' excluído com sucesso do Supabase!")
            return True
        else:
            st.error("Falha ao excluir o arquivo.")
            return False
    except Exception as e:
        st.error(f"Erro ao tentar excluir o arquivo: {e}")
        return False

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

def delete_reembolso_and_file(index, file_path):
    sheet = get_reembolsos_sheet()
    if sheet:
        try:
            # Excluir a linha da planilha
            sheet.delete_rows(index + 2) # +2 pois gspread é 1-based e a primeira linha é o cabeçalho
            st.success("Reembolso excluído com sucesso da planilha!")
            
            # Excluir o arquivo do Supabase, se existir
            if file_path:
                delete_supabase_file(file_path)
            
            st.experimental_rerun() # Atualiza a página
        except Exception as e:
            st.error(f"Erro ao excluir o reembolso: {e}")

# --- Interface do Usuário (Streamlit) ---
st.title("🔑 Painel de Gerenciamento de Reembolsos")

st.subheader("Gerenciar Todos os Reembolsos")
df_reembolsos = load_reembolsos_data()

if not df_reembolsos.empty:
    # Adiciona uma coluna de índice para a exclusão
    df_reembolsos['index'] = df_reembolsos.index
    
    # Exibe a tabela completa de reembolsos
    st.dataframe(df_reembolsos.drop(columns=['index']))
    
    st.subheader("Ações por Reembolso")
    
    # Itera sobre as linhas para criar botões de ação
    for idx, row in df_reembolsos.iterrows():
        col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
        
        with col1:
            st.write(f"ID: {idx+1}")
        with col2:
            if row['ID_COMPROVANTE']:
                if st.button("👁️ Ver Anexo", key=f"view_{idx}"):
                    url = get_signed_url(row['ID_COMPROVANTE'])
                    if url:
                        st.session_state[f"view_url_{idx}"] = url
                    else:
                        st.session_state[f"view_url_{idx}"] = "Não foi possível gerar a URL."
            else:
                st.write("Sem anexo")
        with col3:
            if st.button("❌ Excluir", key=f"delete_{idx}"):
                if st.session_state.get(f"confirm_{idx}", False):
                    delete_reembolso_and_file(idx, row['ID_COMPROVANTE'])
                else:
                    st.warning("Clique novamente para confirmar a exclusão.")
                    st.session_state[f"confirm_{idx}"] = True
            
        with col4:
            if st.session_state.get(f"view_url_{idx}"):
                st.write("---")
                url_display = st.session_state[f"view_url_{idx}"]
                if url_display.startswith("http"):
                    st.subheader(f"Anexo do Reembolso #{idx+1}")
                    if row['ID_COMPROVANTE'].lower().endswith(('.png', '.jpg', '.jpeg')):
                        st.image(url_display, caption="Recibo do Reembolso")
                    elif row['ID_COMPROVANTE'].lower().endswith('.pdf'):
                        st.markdown(f"[📄 Abrir PDF]({url_display})", unsafe_allow_html=True)
                    else:
                        st.markdown(f"[📎 Baixar Arquivo]({url_display})", unsafe_allow_html=True)
                else:
                    st.error(url_display)
                st.write("---")
                
else:
    st.warning("Não há dados de reembolso para gerenciar.") add