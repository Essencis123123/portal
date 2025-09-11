import streamlit as st
import pandas as pd
import datetime
import os
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from PIL import Image
from io import BytesIO
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import json
import re
import pytz
from pandas.errors import EmptyDataError
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO CSS
# ==============================================================================
# Configuração da página com layout wide e ícone
st.set_page_config(page_title="Essencis - Painéis de Gestão", layout="wide", page_icon="💼")

# CSS personalizado para o tema Essencis
st.markdown(
    """
    <style>
    /* Aumenta o tamanho da fonte de todo o corpo do aplicativo */
    html, body, [data-testid="stAppViewContainer"] {
        font-size: 1.1rem;
    }

    [data-testid="stSidebar"] {
        background-color: #1C4D86;
        color: white;
    }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
    .stDownloadButton button p { color: white !important; }

    /* Estilo para o radio button, garantindo que o texto dele também seja branco */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span {
        color: white !important;
    }
    /* Estilo para o texto do multiselect no sidebar */
    [data-testid="stSidebar"] .stMultiSelect label p { color: white !important; }
    [data-testid="stSidebar"] .stMultiSelect div[role="listbox"] * { color: black !important; }
    /* Estilo para o texto do date_input no sidebar */
    [data-testid="stSidebar"] .stDateInput label p { color: white !important; }
    [data-testid="stSidebar"] .stDateInput input { color: black !important; }
    
    .stButton button p { color: black !important; }
    .stDownloadButton button p { color: white !important; }

    [data-testid="stSidebar"] img {
        display: block; margin-left: auto; margin-right: auto;
        width: 80%; border-radius: 10px; padding: 10px 0;
    }

    .main-container {
        background-color: white; padding: 40px; border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15); color: #333;
    }

    .header-container {
        background: linear-gradient(135deg, #0055a5 0%, #1C4D86 100%);
        padding: 25px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; color: white;
    }
    .header-container h1 { color: white; margin: 0; }
    .header-container p { color: white; margin: 5px 0 0 0; font-size: 18px; }

    h2, h3 { color: #1C4D86; font-weight: 600; }

    .stButton button {
        background-color: #0055a5; color: white; border-radius: 8px; transition: background-color .3s;
    }
    .stButton button:hover { background-color: #007ea7; }

    /* CORREÇÃO: Reduz o tamanho da fonte dos cards de métricas */
    [data-testid="stMetric"] > div {
        background-color: #f0f2f5; color: #1C4D86; padding: 5px; border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    [data-testid="stMetric"] .stMetricValue {
        font-size: 0.9rem;
    }
    [data-testid="stMetric"] .stMetricLabel {
        font-size: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# DADOS E FUNÇÕES DE LOGIN
# ==============================================================================
USERS = {
    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},
    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},
    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAULA SOARES"},
    "acsouza@essencis.com.br": {"password": "Essencis01", "name": "ANDRE CASTRO DE SOUZA"},
    "bcampos@essencis.com.br": {"password": "Essencis01", "name": "BARBARA DA SILVA CAMPOS"},
    "earaujo@essencis.com.br": {"password": "Essencis01", "name": "EMERSON ALMEIDA DE ARAUJO"},
    "wrezende@essencis.com.br": {"password": "Essencis01", "name": "WELLINGTON CASSIO DE REZENDE"}
}

def fazer_login(email, senha):
    """Função de login unificada."""
    if email in USERS and USERS[email]["password"] == senha:
        st.session_state['logado'] = True
        st.session_state['nome_colaborador'] = USERS[email]["name"]
        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")
        time.sleep(1)
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# ==============================================================================
# FUNÇÕES DE CONEXÃO COM GOOGLE SHEETS E PROCESSAMENTO DE DADOS
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_logo(url: str):
    """Carrega logo da URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials_info = st.secrets["gcp_service_account"]
    
    if isinstance(credentials_info, str):
        try:
            credentials_info = json.loads(credentials_info)
        except json.JSONDecodeError as e:
            st.error(f"Erro ao decodificar as credenciais JSON: {e}. Verifique a formatação do secrets.toml.")
            return None
    
    creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def _to_datetime(series, dayfirst=True):
    """Converte uma Series para datetime, retornando NaT para erros."""
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)

def parse_brazil_number(value_str):
    """Converte string de número no formato brasileiro (1.234,56) para float (1234.56)."""
    if not isinstance(value_str, str):
        return value_str
    cleaned_value = re.sub(r'R\$\s*', '', value_str).strip()
    cleaned_value = cleaned_value.replace('.', '').replace(',', '.')
    try:
        return float(cleaned_value)
    except (ValueError, TypeError):
        return pd.NaT

# --- Funções de Carregamento e Salvamento do Almoxarifado (aba 1) ---
@st.cache_data(show_spinner=False)
def carregar_dados_almoxarifado():
    """Carrega dados da aba 'Almoxarifado' da planilha 'dados_pedido'."""
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df = pd.DataFrame(worksheet.get_all_records())

        # Adiciona colunas se não existirem
        colunas_obrigatorias = [
            "DATA", "FORNECEDOR_NF", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "OBSERVACAO", "VALOR_JUROS",
            "VALOR_FRETE", "DOC_NF", "RECEBEDOR", "CONDICAO_FRETE", "VOLUME",
            "REGISTRO_ENVIO", "REGISTRO_LANCAMENTO"
        ]
        
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = ''
        
        df = df.rename(columns={
            'STATUS_FINANCEIRO': 'STATUS',
            'OBSERVACAO': 'REGISTRO_ADICIONAL',
            'FORNECEDOR_NF': 'FORNECEDOR',
            'V. TOTAL NF': 'V_TOTAL_NF',
            'DOC NF': 'DOC_NF',
        }, errors='ignore')

        df = df.loc[:,~df.columns.duplicated()]
        df = df.dropna(how='all')
        if not df.empty:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        for c in ["V_TOTAL_NF", "VALOR_JUROS", "VALOR_FRETE"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        df["DATA"] = _to_datetime(df["DATA"])
        df["VENCIMENTO"] = _to_datetime(df["VENCIMENTO"])
        df["REGISTRO_ENVIO"] = _to_datetime(df["REGISTRO_ENVIO"])
        df["REGISTRO_LANCAMENTO"] = _to_datetime(df["REGISTRO_LANCAMENTO"])

        ref = pd.Timestamp.today().normalize()
        df["DIAS_VENCIMENTO"] = (df["VENCIMENTO"] - ref).dt.days.fillna(0).astype(int)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha. Verifique nome/aba/credenciais. Detalhe: {e}")
        return pd.DataFrame(columns=colunas_obrigatorias + ["DIAS_VENCIMENTO"]).rename(columns={
            'STATUS_FINANCEIRO': 'STATUS', 'OBSERVACAO': 'REGISTRO_ADICIONAL',
            'FORNECEDOR_NF': 'FORNECEDOR', 'V. TOTAL NF': 'V_TOTAL_NF', 'DOC NF': 'DOC_NF'
        })

def salvar_dados_financeiro(df: pd.DataFrame) -> bool:
    """Salva o DataFrame na aba 'Almoxarifado' do Google Sheets."""
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df_to_save = df.copy()
        
        df_to_save["DATA"] = _to_datetime(df_to_save["DATA"])
        df_to_save["VENCIMENTO"] = _to_datetime(df_to_save["VENCIMENTO"])
        df_to_save["REGISTRO_ENVIO"] = _to_datetime(df_to_save["REGISTRO_ENVIO"])
        df_to_save["REGISTRO_LANCAMENTO"] = _to_datetime(df_to_save["REGISTRO_LANCAMENTO"])

        df_to_save = df_to_save.rename(columns={
            "STATUS": "STATUS_FINANCEIRO",
            "REGISTRO_ADICIONAL": "OBSERVACAO",
            "V_TOTAL_NF": "V. TOTAL NF",
            "DOC_NF": "DOC NF",
            "FORNECEDOR": "FORNECEDOR_NF"
        }, errors='ignore')

        if "DATA" in df_to_save.columns:
            df_to_save["DATA"] = df_to_save["DATA"].dt.strftime("%d/%m/%Y")
        if "VENCIMENTO" in df_to_save.columns:
            df_to_save["VENCIMENTO"] = df_to_save["VENCIMENTO"].dt.strftime("%d/%m/%Y")
        if "REGISTRO_ENVIO" in df_to_save.columns:
            df_to_save["REGISTRO_ENVIO"] = df_to_save["REGISTRO_ENVIO"].dt.strftime("%d/%m/%Y %H:%M:%S")
        if "REGISTRO_LANCAMENTO" in df_to_save.columns:
            df_to_save["REGISTRO_LANCAMENTO"] = df_to_save["REGISTRO_LANCAMENTO"].dt.strftime("%d/%m/%Y %H:%M:%S")

        df_to_save = df_to_save.drop(columns=["DIAS_VENCIMENTO"], errors="ignore")

        set_with_dataframe(worksheet, df_to_save, include_index=False, resize=True)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados na planilha: {e}")
        return False
        
# --- Funções de Carregamento e Salvamento do Almoxarifado (aba 0) ---
@st.cache_data(show_spinner=False)
def carregar_dados_pedidos():
    """Carrega os dados de pedidos do Google Sheets (primeira aba)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(0)  # Primeira aba (índice 0) é dados_pedido
        data = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
        
        if not data or len(data) <= 1:
            return pd.DataFrame()
            
        headers = data[0]
        records = data[1:]
        df = pd.DataFrame(records, columns=headers)
        
        if 'QUANTIDADE_ENTREGUE' not in df.columns:
            df['QUANTIDADE_ENTREGUE'] = 0.0
        
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df.columns:
                df[col] = _to_datetime(df[col], dayfirst=True)
        
        numeric_cols = ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(parse_brazil_number).fillna(0)
        
        if 'DOC NF' not in df.columns:
            df['DOC NF'] = ''
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados de pedidos: {e}")
        return pd.DataFrame(columns=["DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "QUANTIDADE_ENTREGUE", "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA", "DOC NF"])

def salvar_dados_pedidos(df):
    """Salva os dados de pedidos no Google Sheets (primeira aba)."""
    try:
        gc = get_gspread_client()
        sheet = gc.open("dados_pedido")
        worksheet = sheet.get_worksheet(0)  # Primeira aba (índice 0) é dados_pedido

        df_copy = df.copy()
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
        
        set_with_dataframe(worksheet, df_copy, include_index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados de pedidos: {e}")
        return False
    
# ==============================================================================
# FUNÇÕES DE RENDERIZAÇÃO DAS PÁGINAS
# ==============================================================================
def highlight_text(text, color):
    """Retorna um texto formatado com uma cor específica usando HTML."""
    return f"<span style='color:{color}; font-weight:bold;'>{text}</span>"

# --- Funções da Tela de Registro de Notas Fiscais (Almoxarifado)
@st.dialog("⚠️ Confirmação Necessária")
def confirm_divergence_dialog(novo_registro_nf, edited_items, valor_oc_total, divergencia_oc):
    
    col_v_1, col_v_2 = st.columns(2)
    
    with col_v_1:
        if abs(divergencia_oc) > 0.01:
            valor_oc_formatado = f"R$ {valor_oc_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            valor_nf_formatado = f"R$ {novo_registro_nf['V_TOTAL_NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            divergencia_formatada = f"R$ {divergencia_oc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            st.warning(f"**Atenção: Divergência de Valor!**")
            st.write(f"O **Valor da Ordem de Compra** é: **{valor_oc_formatado}**")
            st.write(f"O **Valor da Nota Fiscal** digitado é: **{valor_nf_formatado}**")
            st.write(f"A **diferença** é de: **{divergencia_formatada}**")

    itens_com_saldo = edited_items[edited_items['SALDO_PENDENTE'] > 0]
    if not itens_com_saldo.empty:
        with col_v_2:
            st.warning("**Atenção: Saldo Pendente!**")
            st.write("A entrega dos seguintes itens não foi total. Confirme a entrega parcial.")
            st.dataframe(
                itens_com_saldo[['CODIGO_MATERIAL', 'MATERIAL', 'SALDO_PENDENTE']].rename(columns={
                    'CODIGO_MATERIAL': 'Cód. Material',
                    'MATERIAL': 'Descrição Material',
                    'SALDO_PENDENTE': 'Saldo Pendente'
                }),
                hide_index=True
            )

    st.markdown("---")
    st.write("Você está ciente e concorda em registrar a nota fiscal com estas informações?")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✅ Sim, Salvar Nota Fiscal"):
            salvar_nota_fiscal(novo_registro_nf, edited_items)
            st.rerun()
    with col_btn2:
        if st.button("❌ Não, Corrigir Valores"):
            st.rerun()

def salvar_nota_fiscal(novo_registro_nf, edited_items_df):
    """Função para salvar a nota fiscal e atualizar os pedidos relacionados."""
    
    st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)
    
    for index, row in edited_items_df.iterrows():
        original_oc_items = st.session_state.df_pedidos[
            (st.session_state.df_pedidos['ORDEM_COMPRA'] == novo_registro_nf['ORDEM_COMPRA']) &
            (st.session_state.df_pedidos['CODIGO_MATERIAL'].astype(str).str.strip() == str(row['CODIGO_MATERIAL']).strip())
        ]
        
        if not original_oc_items.empty:
            original_idx = original_oc_items.index[0]
            
            quantidade_entregue_anterior = st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE_ENTREGUE']
            nova_quantidade_entregue = quantidade_entregue_anterior + row['QUANTIDADE_ENTREGUE']
            
            st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE_ENTREGUE'] = nova_quantidade_entregue
            st.session_state.df_pedidos.loc[original_idx, 'DOC NF'] = novo_registro_nf['DOC_NF']
            
            if nova_quantidade_entregue >= st.session_state.df_pedidos.loc[original_idx, 'QUANTIDADE']:
                st.session_state.df_pedidos.loc[original_idx, 'STATUS_PEDIDO'] = 'ENTREGUE'
                st.session_state.df_pedidos.loc[original_idx, 'DATA_ENTREGA'] = pd.to_datetime(novo_registro_nf['DATA'])
                st.cache_data.clear()
    salvar_dados_pedidos(st.session_state.df_pedidos)
    salvar_dados_financeiro(st.session_state.df_almoxarifado)

    st.success(f"🎉 Nota fiscal {novo_registro_nf['NF']} registrada com sucesso!")
    time.sleep(1)
    st.rerun()
    
def filter_oc():
    """Função de callback para filtrar a Ordem de Compra e recarregar o script."""
    st.session_state.oc_select = ''
    st.session_state.oc_items_for_nf = pd.DataFrame(columns=['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE', 'VALOR_ITEM'])

def render_almoxarifado_page():
    """Página para registrar novas notas fiscais."""
    st.markdown("""
        <div class='header-container'>
            <h1>🏭 PAINEL ALMOXARIFADO</h1>
            <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.df_pedidos.empty:
        st.warning("Nenhum pedido encontrado. Não é possível registrar notas fiscais. Verifique a planilha de pedidos.")
        st.stop()
    
    if 'oc_items_for_nf' not in st.session_state:
        st.session_state.oc_items_for_nf = pd.DataFrame(columns=['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE', 'VALOR_ITEM'])
    
    col1_form, col2_form = st.columns(2)
    with col1_form:
        fornecedores_disponiveis = st.session_state.df_pedidos['FORNECEDOR'].dropna().unique().tolist()
        fornecedor_selecionado = st.selectbox("Fornecedor da NF*", options=[''] + sorted(fornecedores_disponiveis), key="fornecedor_nf_select", on_change=filter_oc)

    with col2_form:
        ordens_disponiveis = ['']
        if fornecedor_selecionado and fornecedor_selecionado != '':
            pedidos_filtrados = st.session_state.df_pedidos[
                st.session_state.df_pedidos['FORNECEDOR'] == fornecedor_selecionado
            ]
            ordens_disponiveis.extend(pedidos_filtrados['ORDEM_COMPRA'].dropna().unique().tolist())
        
        ordem_compra_nf = st.selectbox(
            "N° Ordem de Compra*",
            options=sorted(ordens_disponiveis),
            help="Selecione o número da ordem de compra para vincular a nota.",
            key="oc_select"
        )
    
    if ordem_compra_nf and ordem_compra_nf != st.session_state.get('last_oc_selected'):
        oc_items = st.session_state.df_pedidos[
            st.session_state.df_pedidos['ORDEM_COMPRA'] == ordem_compra_nf
        ].copy()
        if not oc_items.empty:
            if 'QUANTIDADE_ENTREGUE' not in oc_items.columns:
                oc_items['QUANTIDADE_ENTREGUE'] = 0.0
            oc_items['SALDO_PENDENTE'] = oc_items['QUANTIDADE'] - oc_items['QUANTIDADE_ENTREGUE']
            st.session_state.oc_items_for_nf = oc_items
        else:
            st.session_state.oc_items_for_nf = pd.DataFrame(columns=['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE', 'VALOR_ITEM'])
        
        st.session_state.last_oc_selected = ordem_compra_nf

    st.markdown("---")
    
    with st.form("formulario_nota", clear_on_submit=False):
        col1_form, col2_form, col3_form = st.columns(3)
        with col1_form:
            st.markdown(f"Fornecedor selecionado: {highlight_text(str(fornecedor_selecionado), '#39FF14')}", unsafe_allow_html=True)
            nf_numero = st.text_input("Número da NF*", key="nf_numero_input")

        with col2_form:
            recebedor_options = [
                "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                "OUTROS"
            ]
            recebedor = st.selectbox("Recebedor*", sorted(recebedor_options), key="recebedor_select")
            st.markdown(f"Ordem de Compra selecionada: {highlight_text(str(ordem_compra_nf), '#39FF14')}", unsafe_allow_html=True)

        with col3_form:
            valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00", key="valor_total_nf_input")
            condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"], key="condicao_frete_select")
            valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00", key="valor_frete_input")
        
        doc_nf_links = st.text_area("Links das Notas Fiscais (um por linha)*", placeholder="Cole os links de acesso aqui...", key="doc_nf_links_area")
        
        observacao = st.text_area("Observações", placeholder="Informações adicionais...", key="observacao_area")
        vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30), key="vencimento_nf_input")
        
        st.markdown("---")
        st.subheader("Itens do Pedido")

        if not st.session_state.oc_items_for_nf.empty:
            df_to_edit = st.session_state.oc_items_for_nf[['CODIGO_MATERIAL', 'MATERIAL', 'UN', 'QUANTIDADE', 'QUANTIDADE_ENTREGUE', 'SALDO_PENDENTE']].copy()
            
            edited_items = st.data_editor(
                df_to_edit,
                use_container_width=True,
                hide_index=True,
                num_rows='fixed',
                column_config={
                    "CODIGO_MATERIAL": st.column_config.TextColumn("Código Material", disabled=True),
                    "MATERIAL": st.column_config.TextColumn("Descrição Material", disabled=True),
                    "UN": st.column_config.TextColumn("UN", disabled=True),
                    "QUANTIDADE": st.column_config.NumberColumn("Qtd. Pedida", disabled=True, format="%d"),
                    "QUANTIDADE_ENTREGUE": st.column_config.NumberColumn("Qtd. Recebida*", min_value=0, format="%d"),
                    "SALDO_PENDENTE": st.column_config.NumberColumn("Saldo Pendente", disabled=True, format="%d")
                },
                key="itens_pedido_editor"
            )
        
        else:
            st.info("Selecione uma Ordem de Compra para visualizar os itens.")
            edited_items = pd.DataFrame()

        enviar = st.form_submit_button("✅ Registrar Nota Fiscal")

        if enviar:
            if not ordem_compra_nf or ordem_compra_nf == '':
                st.error("Por favor, selecione uma Ordem de Compra.")
                st.stop()
            
            campos_validos = all([
                fornecedor_selecionado.strip(), nf_numero.strip(),
                valor_total_nf.strip() not in ["", "0,00"], doc_nf_links
            ])
            
            quantidade_recebida_total = edited_items['QUANTIDADE_ENTREGUE'].sum() if not edited_items.empty else 0
            
            if not campos_validos:
                st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
            elif quantidade_recebida_total == 0:
                st.error("⚠️ A 'Quantidade Recebida' não pode ser zero. Por favor, preencha os itens da nota fiscal.")
            else:
                try:
                    valor_total_float = parse_brazil_number(valor_total_nf)
                    valor_frete_float = parse_brazil_number(valor_frete_nf)
                    
                    pedidos_relacionados = st.session_state.df_pedidos[
                        st.session_state.df_pedidos['ORDEM_COMPRA'] == ordem_compra_nf
                    ].copy()
                    
                    valor_oc_total = (pedidos_relacionados['VALOR_ITEM'] * pedidos_relacionados['QUANTIDADE']).sum()
                    divergencia = valor_total_float - valor_oc_total
                    
                    tem_divergencia_valor = abs(divergencia) > 0.01
                    tem_saldo_pendente = edited_items['SALDO_PENDENTE'].sum() > 0

                    brasilia_tz = pytz.timezone('America/Sao_Paulo')
                    agora = datetime.datetime.now(brasilia_tz)
                    
                    doc_nf_string = doc_nf_links.replace('\n', ', ')

                    novo_registro_nf = {
                        "DATA": datetime.date.today(),
                        "RECEBEDOR": recebedor,
                        "FORNECEDOR_NF": fornecedor_selecionado,
                        "NF": nf_numero,
                        "VOLUME": quantidade_recebida_total,
                        "V_TOTAL_NF": valor_total_float,
                        "CONDICAO_FRETE": condicao_frete_nf,
                        "VALOR_FRETE": valor_frete_float,
                        "REGISTRO_ADICIONAL": observacao,
                        "DOC_NF": doc_nf_string,
                        "VENCIMENTO": vencimento_nf,
                        "STATUS": "EM ANDAMENTO",
                        "CONDICAO_PROBLEMA": "N/A",
                        "ORDEM_COMPRA": ordem_compra_nf,
                        "REGISTRO_ENVIO": agora,
                        "REGISTRO_LANCAMENTO": agora
                    }

                    if tem_divergencia_valor or tem_saldo_pendente:
                        confirm_divergence_dialog(novo_registro_nf, edited_items, valor_oc_total, divergencia)
                    else:
                        salvar_nota_fiscal(novo_registro_nf, edited_items)

                except ValueError:
                    st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")
    
    st.markdown("---")
    st.subheader("Últimas Notas Registradas")
    if not st.session_state.df_almoxarifado.empty:
        df_ultimas_nfs = st.session_state.df_almoxarifado[st.session_state.df_almoxarifado['NF'].astype(str) != ''].tail(10).copy()
        
        for col in ['DATA', 'VENCIMENTO', 'REGISTRO_ENVIO', 'REGISTRO_LANCAMENTO']:
            if col in df_ultimas_nfs.columns:
                df_ultimas_nfs[col] = pd.to_datetime(df_ultimas_nfs[col], errors='coerce', dayfirst=True)
        
        df_ultimas_nfs['DATA'] = df_ultimas_nfs['DATA'].dt.strftime('%d/%m/%Y').fillna('')
        df_ultimas_nfs['VENCIMENTO'] = df_ultimas_nfs['VENCIMENTO'].dt.strftime('%d/%m/%Y').fillna('')

        col_map = {
            'DATA': 'Data',
            'FORNECEDOR': 'Fornecedor',
            'NF': 'Número NF',
            'ORDEM_COMPRA': 'Ordem de Compra',
            'VOLUME': 'Volume',
            'V_TOTAL_NF': 'Valor Total NF',
            'STATUS': 'Status Financeiro',
            'DOC_NF': 'Anexo NF',
        }
        
        available_cols = [col for col in col_map.keys() if col in df_ultimas_nfs.columns]
        col_map_filtered = {k: v for k, v in col_map.items() if k in available_cols}
        
        df_ultimas_nfs_display = df_ultimas_nfs[available_cols].rename(columns=col_map_filtered)
        
        def colorir_status_display(status):
            cores = {
                "EM ANDAMENTO": "🟡",
                "NF PROBLEMA": "🔴",
                "CAPTURADO": "🟣",
                "FINALIZADO": "🟢"
            }
            return f"{cores.get(status, '⚪')} {status}"

        def format_doc_nf(links_str):
            if not isinstance(links_str, str) or not links_str.strip():
                return ""
            links = links_str.split(', ')
            html_links = [f'<a href="{link.strip()}" target="_blank" title="Clique para baixar"><img src="https://img.icons8.com/material-outlined/24/null/download--v1.png"/></a>' for link in links if link.strip()]
            return " ".join(html_links)

        if 'Status Financeiro' in df_ultimas_nfs_display.columns:
            df_ultimas_nfs_display['Status Financeiro'] = df_ultimas_nfs_display['Status Financeiro'].apply(colorir_status_display)

        if 'Anexo NF' in df_ultimas_nfs_display.columns:
            df_ultimas_nfs_display['Anexo NF'] = df_ultimas_nfs_display['Anexo NF'].astype(str).apply(format_doc_nf)
            
        st.markdown(
            df_ultimas_nfs_display.to_html(escape=False),
            unsafe_allow_html=True
        )

    else:
        st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")

# --- Funções da Tela do Painel Financeiro ---
def render_financeiro_page():
    """Página do painel financeiro."""
    st.markdown("""
        <div class='header-container'>
            <h1>💰 PAINEL FINANCEIRO</h1>
            <p>Gerenciamento e acompanhamento financeiro de NFs</p>
        </div>
    """, unsafe_allow_html=True)
    
    if 'ultimo_salvamento' not in st.session_state:
        st.session_state.ultimo_salvamento = None
    if 'alteracoes_pendentes' not in st.session_state:
        st.session_state.alteracoes_pendentes = False

    df = st.session_state.df_almoxarifado.copy()

    # Filtros do sidebar (apenas para exibição nesta página)
    with st.sidebar:
        st.subheader("Filtros de Período")
        if 'DATA' in df.columns and not df['DATA'].isnull().all():
            min_date_value = df['DATA'].min() if not df['DATA'].isnull().all() else datetime.date.today()
            max_date_value = df['DATA'].max() if not df['DATA'].isnull().all() else datetime.date.today()
            data_minima = st.date_input("De:", value=min_date_value, key='fin_data_min')
            data_maxima = st.date_input("Até:", value=max_date_value, key='fin_data_max')
        else:
            data_minima = None
            data_maxima = None

        st.subheader("Filtros de Dados")
        filtro_status = ['Todos']
        if 'STATUS' in df.columns and not df.empty:
            status_disponiveis = df['STATUS'].dropna().unique().tolist()
            filtro_status = st.multiselect(
                "Filtrar por Status:",
                options=['Todos'] + sorted(status_disponiveis),
                default=['Todos'],
                key='fin_filtro_status'
            )

        filtro_fornecedor = ['Todos']
        if 'FORNECEDOR' in df.columns and not df.empty:
            fornecedores_disponiveis = df['FORNECEDOR'].dropna().unique().tolist()
            filtro_fornecedor = st.multiselect(
                "Filtrar por Fornecedor:",
                options=['Todos'] + sorted(fornecedores_disponiveis),
                default=['Todos'],
                key='fin_filtro_fornecedor'
            )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Salvar Tudo", use_container_width=True):
            if salvar_dados_financeiro(df):
                st.session_state.ultimo_salvamento = datetime.datetime.now()
                st.session_state.alteracoes_pendentes = False
                st.success("Dados salvos com sucesso!")
                time.sleep(1)
                st.rerun()
    with col2:
        if st.button("🔄 Recarregar", use_container_width=True):
            st.session_state.df_almoxarifado = carregar_dados_almoxarifado()
            st.rerun()
    with col4:
        if st.session_state.ultimo_salvamento:
            st.info(f"Último save: {st.session_state.ultimo_salvamento.strftime('%H:%M:%S')}")
        elif st.session_state.alteracoes_pendentes:
            st.warning("Alterações não salvas")
    
    if not df.empty:
        df_filtrado = df.copy()

        if 'DATA' in df_filtrado.columns and data_minima and data_maxima:
            df_filtrado = df_filtrado[df_filtrado['DATA'].dt.date.between(data_minima, data_maxima)]

        if 'Todos' not in filtro_status:
            df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(filtro_status)]
        if 'Todos' not in filtro_fornecedor:
            df_filtrado = df_filtrado[df_filtrado['FORNECEDOR'].isin(filtro_fornecedor)]
        
        df_display = df_filtrado
        st.markdown("---")
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        total_nfs = len(df_display)
        total_valor = df_display['V_TOTAL_NF'].sum()
        nfs_pendentes = len(df_display[df_display['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])])
        total_juros = df_display['VALOR_JUROS'].sum()
        total_frete = df_display['VALOR_FRETE'].sum()

        def formatar_milhar(valor):
            if abs(valor) >= 1000:
                return f"R$ {valor/1000:,.1f}K".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        c1.metric("📊 Total de NFs", total_nfs)
        c2.metric("💰 Valor NFs", formatar_milhar(total_valor))
        c3.metric("⏳ Pendentes", nfs_pendentes)
        c4.metric("✅ Finalizadas", total_nfs - nfs_pendentes)
        c5.metric("💸 Juros", formatar_milhar(total_juros))
        c6.metric("🚚 Fretes", formatar_milhar(total_frete))

        st.markdown("---")
        st.subheader("📋 Detalhes das Notas Fiscais")

        status_map = {
            'EM ANDAMENTO': '🟡 EM ANDAMENTO',
            'NF PROBLEMA': '🔴 NF PROBLEMA',
            'CAPTURADO': '🟣 CAPTURADO',
            'FINALIZADO': '🟢 FINALIZADO'
        }
        reverse_status_map = {v: k for k, v in status_map.items()}

        df_display['STATUS_VISUAL'] = df_display['STATUS'].map(status_map).fillna('⚪ DESCONHECIDO')
        
        def formatar_vencimento_visual(dias):
            if pd.isna(dias): return "N/A"
            if dias <= 7:
                return f"🔴 {dias}"
            elif dias <= 10:
                return f"🟡 {dias}"
            return str(dias)
        df_display['DIAS_VENCIMENTO_VISUAL'] = df_display['DIAS_VENCIMENTO'].apply(formatar_vencimento_visual)

        def formatar_problema_visual(row):
            if str(row.get('CONDICAO_PROBLEMA')) == 'CHAMADO':
                # Essa parte é apenas demonstrativa para a condição, ajuste conforme sua regra
                data_problema = datetime.date(2025, 9, 29)
                dias_passados = (datetime.date.today() - data_problema).days
                if dias_passados > 5:
                    return f"🔴 {row['CONDICAO_PROBLEMA']}"
            return row['CONDICAO_PROBLEMA']
            
        df_display['PROBLEMA_VISUAL'] = df_display.apply(lambda row: formatar_problema_visual(row), axis=1)

        problema_options = ["N/A", "SEM PEDIDO", "VALOR INCORRETO", "OUTRO", "CHAMADO", "CARTA CORRECAO", "AJUSTE OC", "RECUSA"]

        df_display['REGISTRO_ENVIO'] = pd.to_datetime(df_display['REGISTRO_ENVIO'], errors='coerce')
        df_display['REGISTRO_LANCAMENTO'] = pd.to_datetime(df_display['REGISTRO_LANCAMENTO'], errors='coerce')

        df_display['REGISTRO_ENVIO_VISUAL'] = df_display['REGISTRO_ENVIO'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
        df_display['REGISTRO_LANCAMENTO_VISUAL'] = df_display['REGISTRO_LANCAMENTO'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            column_config={
                "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
                "FORNECEDOR": "Fornecedor",
                "NF": "N° NF",
                "ORDEM_COMPRA": "N° Ordem de Compra",
                "V_TOTAL_NF": st.column_config.NumberColumn("V. Total NF (R$)", format="%.2f", disabled=True),
                "VENCIMENTO": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                "DIAS_VENCIMENTO_VISUAL": st.column_config.Column("Dias Vencimento", disabled=True),
                "STATUS_VISUAL": st.column_config.SelectboxColumn("Status", options=list(status_map.values()), default="🟡 EM ANDAMENTO"),
                "PROBLEMA_VISUAL": st.column_config.SelectboxColumn("Problema", options=problema_options),
                "REGISTRO_ADICIONAL": "Obs.",
                "VALOR_JUROS": st.column_config.NumberColumn("Juros (R$)", format="%.2f"),
                "VALOR_FRETE": st.column_config.NumberColumn("Frete (R$)", format="%.2f"),
                "DOC_NF": st.column_config.LinkColumn("DOC NF", display_text="📥"),
                "RECEBEDOR": "Recebedor",
                "REGISTRO_ENVIO_VISUAL": st.column_config.TextColumn("Reg. Envio (Almox.)", disabled=True),
                "REGISTRO_LANCAMENTO_VISUAL": st.column_config.TextColumn("Reg. Lançamento (Fin.)"), # EDITÁVEL
            },
            column_order=[
                "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO", "DIAS_VENCIMENTO_VISUAL",
                "STATUS_VISUAL", "PROBLEMA_VISUAL", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC_NF", "RECEBEDOR",
                "REGISTRO_ENVIO_VISUAL", "REGISTRO_LANCAMENTO_VISUAL"
            ],
            hide_index=True
        )

        if not edited_df.equals(df_display):
            st.session_state.alteracoes_pendentes = True
            
            updated_df = df.copy()
            
            brasilia_tz = pytz.timezone('America/Sao_Paulo')
            
            for index, row in edited_df.iterrows():
                novo_status_visual = row['STATUS_VISUAL']
                novo_status_data = reverse_status_map.get(novo_status_visual)
                
                if novo_status_data:
                    status_original = updated_df.loc[index, 'STATUS']

                    if novo_status_data == 'FINALIZADO' and status_original != 'FINALIZADO':
                        updated_df.loc[index, 'REGISTRO_LANCAMENTO'] = datetime.datetime.now(brasilia_tz)
                    
                    if novo_status_data == 'CAPTURADO' and status_original != 'CAPTURADO':
                        updated_df.loc[index, 'REGISTRO_LANCAMENTO'] = datetime.datetime.now(brasilia_tz)
                    
                    if novo_status_data == 'CAPTURADO' and status_original != 'CAPTURADO':
                        updated_df.loc[index, 'REGISTRO_ENVIO'] = datetime.datetime.now(brasilia_tz)
                    
                    updated_df.loc[index, 'STATUS'] = novo_status_data
                    updated_df.loc[index, 'CONDICAO_PROBLEMA'] = str(row['PROBLEMA_VISUAL']).replace('🔴 ', '')
                    updated_df.loc[index, 'VALOR_JUROS'] = row['VALOR_JUROS']
                    updated_df.loc[index, 'VALOR_FRETE'] = row['VALOR_FRETE']
                    
            st.session_state.df_almoxarifado = updated_df

            if salvar_dados_financeiro(st.session_state.df_almoxarifado):
                st.session_state.ultimo_salvamento = datetime.datetime.now()
                st.session_state.alteracoes_pendentes = False
                st.success("Alterações salvas com sucesso!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("📝 Nenhuma nota fiscal registrada no sistema. As notas cadastradas no Painel do Almoxarifado aparecerão aqui.")

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # Tela de login
    st.markdown("<h1 style='text-align: center; color: #1C4D86;'>Login - Painéis de Gestão Essencis</h1>", unsafe_allow_html=True)
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.image("http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png", use_container_width=True)
        st.write("")
        
        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="seu.email@essencis.com.br")
            senha = st.text_input("Senha", type="password")
            
            st.write("")
            if st.form_submit_button("Entrar"):
                fazer_login(email, senha)
else:
    # Usuário logado - renderizar a aplicação principal
    if 'df_almoxarifado' not in st.session_state:
        st.session_state.df_almoxarifado = carregar_dados_almoxarifado()
    if 'df_pedidos' not in st.session_state:
        st.session_state.df_pedidos = carregar_dados_pedidos()

    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)

    # Menu do sidebar
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)

        st.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")
        st.title("📌 Menu Principal")

        menu_option = st.radio(
            "Selecione o Painel:",
            ["🏭 Almoxarifado", "💰 Financeiro"]
        )
        
        st.divider()
        if st.button("Logout"):
            st.session_state.logado = False
            st.rerun()
        st.caption("Sistema de Gestão Integrada v1.0")

    # Renderiza a página baseada na seleção do menu
    if menu_option == "🏭 Almoxarifado":
        render_almoxarifado_page()
    elif menu_option == "💰 Financeiro":
        render_financeiro_page()
