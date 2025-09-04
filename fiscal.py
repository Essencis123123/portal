import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import streamlit as st
import json
from oauth2client.service_account import ServiceAccountCredentials
import requests
from PIL import Image
from io import BytesIO
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Financeiro - Almoxarifado", layout="wide", page_icon="💼")

# ... (Seu CSS e funções load_logo, get_gspread_client permanecem os mesmos)

def carregar_dados():
    """
    Carrega os dados da aba "Almoxarifado" da planilha do Google Sheets.
    """
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado") 
        
        df = get_as_dataframe(worksheet)
        
        if df.empty or all(df.columns.isnull()):
            st.warning("A planilha existe, mas está vazia. Adicione dados pelo Painel do Almoxarifado.")
            return pd.DataFrame(columns=[
                "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V. TOTAL NF", "VENCIMENTO",
                "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC NF", "RECEBEDOR", "VOLUME"
            ])

        # Renomeia colunas para manter a compatibilidade com o código original
        # Isso garante que a lógica de "STATUS", "REGISTRO_ADICIONAL" e "VALOR_FRETE" funcione
        # Renomeação de colunas. Apenas as colunas que precisam de alteração
        df = df.rename(columns={
            'STATUS_FINANCEIRO': 'STATUS',
            'OBSERVACAO': 'REGISTRO_ADICIONAL',
            'V. TOTAL NF': 'V. TOTAL NF', # Renomeação redundante, mas mantém a clareza
            'VALOR FRETE': 'VALOR_FRETE',
            'DOC NF': 'DOC NF'
        })
        
        # Limpeza e conversão de dados
        df = df.dropna(how='all')
        df = df.astype(str).apply(lambda x: x.str.strip()).replace('nan', '', regex=True)

        # Converte para tipos corretos
        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)
        if 'VENCIMENTO' in df.columns:
            df['VENCIMENTO'] = pd.to_datetime(df['VENCIMENTO'], errors='coerce', dayfirst=True)
        else:
            df['VENCIMENTO'] = pd.NaT
        
        # Garantir que todas as colunas necessárias existam.
        # Isto previne erros se alguma coluna estiver faltando.
        colunas_final = [
            "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V. TOTAL NF", "VENCIMENTO",
            "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC NF", "RECEBEDOR", "VOLUME"
        ]
        
        for col in colunas_final:
            if col not in df.columns:
                df[col] = None
        
        df = df[colunas_final] # Reorganiza as colunas e remove qualquer duplicata
        
        # Converte colunas numéricas
        df['V. TOTAL NF'] = pd.to_numeric(df['V. TOTAL NF'], errors='coerce').fillna(0)
        df['VALOR_JUROS'] = pd.to_numeric(df['VALOR_JUROS'], errors='coerce').fillna(0)
        df['VALOR_FRETE'] = pd.to_numeric(df['VALOR_FRETE'], errors='coerce').fillna(0)
        df['DIAS_ATRASO'] = pd.to_numeric(df['DIAS_ATRASO'], errors='coerce').fillna(0)
        df['VOLUME'] = pd.to_numeric(df['VOLUME'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha. Verifique o nome/URL da planilha, o nome da aba e se as credenciais estão corretas. Erro: {e}")
        return pd.DataFrame()

# ... (O resto do seu código permanece o mesmo)
