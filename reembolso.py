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
import hashlib

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

gs_client = get_gspread_client()

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

def get_usuarios_sheet():
    try:
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Usuarios")
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Usuarios' não foi encontrada na planilha.")
        return None

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
supabase_key = secrets_dict["supabase"]["service_role_key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

# --- Sistema de Autenticação ---
def check_password():
    """Retorna True se o usuário está autenticado corretamente."""
    
    def password_entered():
        """Verifica se a senha está correta."""
        if st.session_state["username"] in st.secrets["passwords"]:
            password_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
            if password_hash == st.secrets["passwords"][st.session_state["username"]]:
                st.session_state["password_correct"] = True
                st.session_state["user_role"] = st.session_state["username"]
                del st.session_state["password"]
                del st.session_state["username"]
            else:
                st.session_state["password_correct"] = False
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Usuário", key="username", on_change=password_entered)
        st.text_input("Senha", type="password", key="password", on_change=password_entered)
        st.write("")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Usuário", key="username", on_change=password_entered)
        st.text_input("Senha", type="password", key="password", on_change=password_entered)
        st.error("😕 Usuário ou senha incorretos")
        st.write("")
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.button("Entrar", on_click=password_entered)
        return False
    else:
        return True

def is_admin():
    """Verifica se o usuário logado é o administrador."""
    return st.session_state.get("user_role") == "admin"

# --- Logo e Header ---
def show_header():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://via.placeholder.com/300x100/007bff/ffffff?text=Sistema+Reembolsos", 
                use_column_width=True)
        st.markdown("---")

# --- Funções do Aplicativo ---
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
                st.success("✅ Arquivo enviado com sucesso!")
                return unique_file_name
            else:
                st.error("❌ Falha ao enviar o arquivo")
                return None
        except Exception as e:
            st.error(f"❌ Erro no upload: {str(e)}")
            return None
    return None

def get_signed_url(file_path, bucket_name="reembolsos-anexos"):
    try:
        response = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 60)
        if 'signedURL' in response:
            return response['signedURL']
        else:
            return None
    except Exception:
        return None

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
        except Exception as e:
            st.error(f"Erro ao adicionar reembolso: {e}")

# --- Aplicação Principal ---
def main():
    show_header()
    
    if not check_password():
        st.stop()
    
    # Menu baseado no tipo de usuário
    if is_admin():
        menu_options = ["Dashboard", "Adicionar Reembolso", "Gerenciar Reembolsos"]
        user_role = "Administrador"
    else:
        menu_options = ["Dashboard", "Adicionar Reembolso"]
        user_role = "Usuário"
    
    st.sidebar.write(f"👤 Logado como: **{user_role}**")
    st.sidebar.write("---")
    
    menu = st.sidebar.selectbox("Menu Principal", menu_options)
    
    # Logout button
    if st.sidebar.button("🚪 Sair"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # --- Seção do Dashboard ---
    if menu == "Dashboard":
        st.header("📊 Dashboard de Reembolsos")
        df_reembolsos = load_reembolsos_data()
        
        if not df_reembolsos.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                total = len(df_reembolsos)
                st.metric("Total de Reembolsos", total)
            with col2:
                if 'VALOR' in df_reembolsos.columns:
                    total_valor = df_reembolsos['VALOR'].sum()
                    st.metric("Valor Total", f"R$ {total_valor:,.2f}")
            with col3:
                if 'STATUS' in df_reembolsos.columns:
                    pendentes = df_reembolsos[df_reembolsos['STATUS'] == 'Pendente'].shape[0]
                    st.metric("Pendentes", pendentes)
            
            if 'STATUS' in df_reembolsos.columns:
                fig_status = px.bar(df_reembolsos['STATUS'].value_counts(),
                                    title="Distribuição por Status",
                                    labels={'index': 'Status', 'value': 'Quantidade'})
                st.plotly_chart(fig_status)
        else:
            st.warning("Não há dados de reembolso para exibir.")

    # --- Seção de Adicionar Reembolso ---
    elif menu == "Adicionar Reembolso":
        st.header("📝 Adicionar Novo Reembolso")
        
        with st.form("form_reembolso"):
            nome_funcionario = st.text_input("Nome do Funcionário *")
            departamento = st.text_input("Departamento *")
            tipo_despesa = st.text_input("Tipo de Despesa *")
            valor_reembolso = st.number_input("Valor (R$) *", min_value=0.01, format="%.2f")
            justificativa = st.text_area("Justificativa *")
            data_reembolso = st.date_input("Data *", value=datetime.date.today())
            
            recibo_anexo = st.file_uploader("Comprovante (opcional)", type=["jpg", "jpeg", "png", "pdf"])
            
            submit_button = st.form_submit_button("✅ Salvar Reembolso")
            
            if submit_button:
                required_fields = [nome_funcionario, departamento, tipo_despesa, valor_reembolso, justificativa]
                if all(required_fields):
                    caminho_recibo = None
                    if recibo_anexo:
                        caminho_recibo = upload_to_supabase(recibo_anexo)
                    
                    add_reembolso(data_reembolso, nome_funcionario, departamento, tipo_despesa, 
                                 valor_reembolso, justificativa, caminho_recibo)
                else:
                    st.error("Por favor, preencha todos os campos obrigatórios (*).")

    # --- Seção de Gerenciar Reembolsos (APENAS ADMIN) ---
    elif menu == "Gerenciar Reembolsos" and is_admin():
        st.header("⚙️ Gerenciar Reembolsos")
        
        df_reembolsos = load_reembolsos_data()

        if not df_reembolsos.empty and 'ID_COMPROVANTE' in df_reembolsos.columns:
            for idx, row in df_reembolsos.iterrows():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1,1,1,1,1,2,1,1])
                
                with col1:
                    st.write(row.get('DATA', ''))
                with col2:
                    st.write(row.get('NOME', ''))
                with col3:
                    st.write(row.get('DEPARTAMENTO', ''))
                with col4:
                    st.write(row.get('TIPO_DESPESA', ''))
                with col5:
                    st.write(f"R$ {row.get('VALOR', 0):.2f}")
                with col6:
                    st.write(row.get('JUSTIFICATIVA', ''))
                with col7:
                    status = st.selectbox(
                        "Status",
                        ["Pendente", "Aprovado", "Rejeitado"],
                        index=0 if row.get('STATUS') == "Pendente" else 1 if row.get('STATUS') == "Aprovado" else 2,
                        key=f"status_{idx}"
                    )
                with col8:
                    if row.get('ID_COMPROVANTE') and pd.notna(row.get('ID_COMPROVANTE')):
                        if st.button("👁️ Ver", key=f"view_{idx}"):
                            caminho_recibo = row['ID_COMPROVANTE']
                            url_recibo = get_signed_url(caminho_recibo)
                            if url_recibo:
                                if caminho_recibo.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(url_recibo, width=300)
                                else:
                                    st.markdown(f"[📎 Abrir arquivo]({url_recibo})")
                st.divider()
        else:
            st.warning("Não há dados de reembolso para exibir.")

# Executa a aplicação
if __name__ == "__main__":
    main()
