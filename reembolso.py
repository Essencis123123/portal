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

# Carrega os segredos do arquivo secrets2.toml
try:
    with open(".streamlit/secrets2.toml", "r") as f:
        secrets_dict = toml.load(f)
except FileNotFoundError:
    st.error("O arquivo .streamlit/secrets2.toml não foi encontrado.")
    st.stop()

# --- Configuração do Layout e Tema ---
st.set_page_config(page_title="Gestão de Reembolsos", layout="wide", page_icon="💰")

# ... (todo o resto do seu código permanece o mesmo) ...

# --- Configuração de Dados e Lógica de Backend (Google Sheets) ---
SHEET_ID = secrets_dict["gcp_service_account"]["sheet_id"] # Use secrets_dict aqui

# Conexão com Google Sheets (gspread)
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"], # Use secrets_dict aqui
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

# Conexão com Gmail API (mantida para envio de e-mails)
@st.cache_resource(ttl=3600)
def get_google_api_service():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        secrets_dict["gcp_service_account"], # Use secrets_dict aqui
        ['https://www.googleapis.com/auth/gmail.send']
    )
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service

gs_client = get_gspread_client()
gmail_service = get_google_api_service()

# ... (todo o resto do seu código) ...

# Inicialização do Supabase Client
supabase_url = secrets_dict["supabase"]["url"] # Use secrets_dict aqui
supabase_key = secrets_dict["supabase"]["key"] # Use secrets_dict aqui
supabase_client: Client = create_client(supabase_url, supabase_key)

# ... (todo o resto do seu código) ...
