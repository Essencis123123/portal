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

def get_reembolsos_sheet():
    try:
        # Acessa a planilha e seleciona a aba "Reembolsos"
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
        # Acessa a planilha e seleciona a aba "Usuarios"
        spreadsheet = gs_client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Usuarios")
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        st.error("A aba 'Usuarios' não foi encontrada na planilha.")
        return None

def send_email_with_attachment(to, subject, body, attachment_path=None):
    # ... (Seu código de envio de e-mail) ...
    pass

# --- Supabase Integration ---
supabase_url = secrets_dict["supabase"]["url"]
# USE A SERVICE ROLE KEY PARA BYPASS DO RLS
supabase_key = secrets_dict["supabase"]["service_role_key"]
supabase_client: Client = create_client(supabase_url, supabase_key)

# Debug: Verifique se está usando a chave correta
st.sidebar.write("🔐 Usando Service Role Key")
st.sidebar.write(f"URL: {supabase_url}")
st.sidebar.write(f"Key: {supabase_key[:20]}...")

# Função para fazer upload para o Supabase Storage
def upload_to_supabase(file_uploader, bucket_name="reembolsos-anexos"):
    if file_uploader is not None:
        try:
            file_name = file_uploader.name
            unique_file_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
            file_bytes = file_uploader.read()
            
            # Debug info
            st.write(f"📤 Iniciando upload para bucket: {bucket_name}")
            st.write(f"📄 Arquivo: {file_uploader.name}")
            
            # Faz o upload usando a service role key
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
            # Log detalhado para debugging
            import traceback
            st.error(f"Traceback completo: {traceback.format_exc()}")
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
def load_reembolsos_data():
    sheet = get_reembolsos_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
        return df
    return pd.DataFrame()

# Função para adicionar novo reembolso
def add_reembolso(data, nome, departamento, tipo_despesa, valor, justificativa, caminho_recibo, status="Pendente"):
    sheet = get_reembolsos_sheet()
    if sheet:
        data_formatada = data.strftime('%d/%m/%Y')
        try:
            # A ordem dos dados deve ser a mesma das colunas na planilha "Reembolsos"
            row = [data_formatada, nome, departamento, tipo_despesa, valor, justificativa, status, caminho_recibo]
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
    df_reembolsos = load_reembolsos_data()
    
    if not df_reembolsos.empty:
        # Verifica se a coluna STATUS existe antes de tentar acessá-la
        if 'STATUS' in df_reembolsos.columns:
            # Gráfico de status
            fig_status = px.bar(df_reembolsos['STATUS'].value_counts(),
                                title="Total de Reembolsos por Status",
                                labels={'index': 'STATUS', 'value': 'Quantidade'})
            st.plotly_chart(fig_status)
        else:
            st.warning("Coluna 'STATUS' não encontrada nos dados.")
            
        # Mostra estatísticas básicas
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
    
    with st.form("form_reembolso"):
        nome_funcionario = st.text_input("NOME")
        departamento = st.text_input("DEPARTAMENTO")
        tipo_despesa = st.text_input("TIPO_DESPESA")
        valor_reembolso = st.number_input("VALOR", min_value=0.01, format="%.2f")
        justificativa = st.text_area("JUSTIFICATIVA")
        data_reembolso = st.date_input("DATA", value=datetime.date.today())
        
        # Campo para o anexo do recibo
        recibo_anexo = st.file_uploader("ID_COMPROVANTE", type=["jpg", "jpeg", "png", "pdf"])
        
        submit_button = st.form_submit_button("Salvar Reembolso")
        
        if submit_button:
            if nome_funcionario and valor_reembolso and data_reembolso and departamento and tipo_despesa and justificativa:
                # 1. Tenta fazer o upload do arquivo
                caminho_recibo = None
                if recibo_anexo:
                    try:
                        caminho_recibo = upload_to_supabase(recibo_anexo)
                        if not caminho_recibo:
                            st.warning("Upload do arquivo falhou, mas o reembolso será salvo sem anexo.")
                    except Exception as e:
                        st.warning(f"Erro no upload: {e}. O reembolso será salvo sem anexo.")
                
                # 2. Salva os dados no Google Sheets (com ou sem anexo)
                add_reembolso(data_reembolso, nome_funcionario, departamento, tipo_despesa, 
                             valor_reembolso, justificativa, caminho_recibo)
                
            else:
                st.error("Por favor, preencha todos os campos obrigatórios.")

# --- Seção de Gerenciar Reembolsos (com visualização do recibo) ---
elif menu == "Gerenciar Reembolsos":
    st.header("Gerenciar Reembolsos")
    
    df_reembolsos = load_reembolsos_data()

    if not df_reembolsos.empty:
        # Verifica se a coluna ID_COMPROVANTE existe
        if 'ID_COMPROVANTE' in df_reembolsos.columns:
            # Cria uma cópia para exibição
            df_display = df_reembolsos.copy()
            
            # Cria a coluna "Ver Recibo" com links clicáveis
            df_display['Ver Recibo'] = df_display['ID_COMPROVANTE'].apply(
                lambda x: "🔗 Ver Recibo" if x and str(x).strip() != "" else "📝 Sem Anexo"
            )
            
            colunas_para_exibir = ['DATA', 'NOME', 'DEPARTAMENTO', 'TIPO_DESPESA', 'VALOR', 'JUSTIFICATIVA', 'STATUS', 'Ver Recibo']
            
            # Filtra apenas as colunas que existem no DataFrame
            colunas_existentes = [col for col in colunas_para_exibir if col in df_display.columns]
            
            # Exibe a tabela
            for idx, row in df_display.iterrows():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
                
                with col1:
                    st.write(row['DATA'] if 'DATA' in row else '')
                with col2:
                    st.write(row['NOME'] if 'NOME' in row else '')
                with col3:
                    st.write(row['DEPARTAMENTO'] if 'DEPARTAMENTO' in row else '')
                with col4:
                    st.write(row['TIPO_DESPESA'] if 'TIPO_DESPESA' in row else '')
                with col5:
                    st.write(f"R$ {row['VALOR']:,.2f}" if 'VALOR' in row else '')
                with col6:
                    st.write(row['JUSTIFICATIVA'] if 'JUSTIFICATIVA' in row else '')
                with col7:
                    st.write(row['STATUS'] if 'STATUS' in row else '')
                with col8:
                    if row['Ver Recibo'] == "🔗 Ver Recibo" and row['ID_COMPROVANTE']:
                        if st.button("🔗 Ver Recibo", key=f"btn_{idx}"):
                            caminho_recibo = row['ID_COMPROVANTE']
                            st.subheader(f"Recibo para {row['NOME']}")
                            
                            # Gera a URL assinada
                            url_recibo = get_signed_url(caminho_recibo)
                            if url_recibo:
                                # Verifica se é uma imagem ou PDF
                                if caminho_recibo.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(url_recibo, caption="Recibo do Reembolso", width=300)
                                elif caminho_recibo.lower().endswith('.pdf'):
                                    st.markdown(f"[📄 Abrir PDF]({url_recibo})", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"[📎 Baixar Arquivo]({url_recibo})", unsafe_allow_html=True)
                            else:
                                st.error("Não foi possível carregar o recibo.")
                    else:
                        st.write("📝 Sem Anexo")
                
                st.divider()
                
        else:
            st.warning("Coluna 'ID_COMPROVANTE' não encontrada nos dados.")
    else:
        st.warning("Não há dados de reembolso para exibir.")
