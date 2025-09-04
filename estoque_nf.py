import streamlit as st

import pandas as pd

import datetime

import os

import time

import plotly.express as px

from pandas.errors import EmptyDataError

import numpy as np

import requests

from PIL import Image

from io import BytesIO

import smtplib

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart

import gspread

from google.oauth2.service_account import Credentials



# Configuração da página com layout wide

st.set_page_config(page_title="Painel Almoxarifado", layout="wide", page_icon="🏭")



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



# Carregar a imagem do logo a partir da URL

@st.cache_data

def load_logo(url):

    try:

        response = requests.get(url)

        img = Image.open(BytesIO(response.content))

        return img

    except:

        return None



# Funções de carregamento e salvamento de dados para Google Sheets

def carregar_dados_almoxarifado():

    try:

        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        credentials_info = st.secrets["gcp_service_account"]

        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])

        worksheet = spreadsheet.get_worksheet(2)

        

        data = worksheet.get_all_records()

        df = pd.DataFrame(data)



        for col in ['DATA', 'VENCIMENTO']:

            if col in df.columns:

                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

        

        for col in ['V. TOTAL NF', 'VALOR FRETE']:

            if col in df.columns:

                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)



        if 'CONDICAO_PROBLEMA' not in df.columns:

            df['CONDICAO_PROBLEMA'] = ''

        if 'REGISTRO_ADICIONAL' not in df.columns:

            df['REGISTRO_ADICIONAL'] = ''

        if 'ORDEM_COMPRA' not in df.columns:

            df['ORDEM_COMPRA'] = ''

        if 'STATUS_FINANCEIRO' not in df.columns:

            df['STATUS_FINANCEIRO'] = ''



        return df

    except Exception as e:

        st.error(f"Erro ao carregar dados do almoxarifado: {e}")

        return pd.DataFrame(columns=[

            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "VOLUME", "V. TOTAL NF",

            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",

            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",

            "ORDEM_COMPRA"

        ])



def salvar_dados_almoxarifado(df):

    try:

        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        credentials_info = st.secrets["gcp_service_account"]

        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])

        worksheet = spreadsheet.get_worksheet(2)



        df_copy = df.copy()

        for col in ['DATA', 'VENCIMENTO']:

            if col in df_copy.columns:

                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')

        

        data_to_write = [df_copy.columns.values.tolist()] + df_copy.values.tolist()

        worksheet.clear()

        worksheet.update(data_to_write, value_input_option='USER_ENTERED')

        return True

    except Exception as e:

        st.error(f"Erro ao salvar dados do almoxarifado: {e}")

        return False



# Removido o cache para garantir que os dados de pedidos sejam sempre os mais recentes

def carregar_dados_pedidos():

    """Carrega os dados de pedidos do Google Sheets."""

    try:

        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        credentials_info = st.secrets["gcp_service_account"]

        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])

        worksheet = spreadsheet.get_worksheet(0)

        data = worksheet.get_all_records()

        df = pd.DataFrame(data)

        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:

            if col in df.columns:

                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

        return df

    except Exception as e:

        st.error(f"Erro ao carregar dados de pedidos: {e}")

        return pd.DataFrame(columns=["DATA", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE", "TIPO_PEDIDO", "REQUISICAO", "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA_APROVACAO", "CONDICAO_FRETE", "STATUS_PEDIDO", "DATA_ENTREGA"])



def salvar_dados_pedidos(df):

    """Salva os dados de pedidos no Google Sheets."""

    try:

        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        credentials_info = st.secrets["gcp_service_account"]

        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])

        worksheet = spreadsheet.get_worksheet(0)



        df_copy = df.copy()

        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:

            if col in df_copy.columns:

                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')

        

        data_to_write = [df_copy.columns.values.tolist()] + df_copy.values.tolist()

        worksheet.clear()

        worksheet.update(data_to_write, value_input_option='USER_ENTERED')

        return True

    except Exception as e:

        st.error(f"Erro ao salvar dados de pedidos: {e}")

        return False



def carregar_dados_solicitantes():

    try:

        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        credentials_info = st.secrets["gcp_service_account"]

        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(st.secrets["sheet_id"])

        worksheet = spreadsheet.get_worksheet(1)

        data = worksheet.get_all_records()

        df = pd.DataFrame(data)

        return df

    except Exception as e:

        st.error(f"Erro ao carregar dados de solicitantes: {e}")

        return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])



# Funções de E-mail

status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]



# --- LÓGICA DE LOGIN ---

USERS = {

    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},

    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},

    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAURA SOARES"},

    "acsouza@essencis.com.br": {"password": "Essencis01", "name": "ANDRE CASTRO DE SOUZA"},

    "bcampos@essencis.com.br": {"password": "Essencis01", "name": "BARBARA DA SILVA CAMPOS"},

    "earaujo@essencis.com.br": {"password": "Essencis01", "name": "EMERSON ALMEIDA DE ARAUJO"}

}



def fazer_login(email, senha):

    if email in USERS and USERS[email]["password"] == senha:

        st.session_state['logado'] = True

        st.session_state['nome_colaborador'] = USERS[email]["name"]

        st.success(f"Login bem-sucedido! Bem-vindo(a), {st.session_state['nome_colaborador']}.")

        st.rerun()

    else:

        st.error("E-mail ou senha incorretos.")



# Credenciais de e-mail agora vêm de st.secrets

def enviar_email_entrega(solicitante_nome, email_solicitante, numero_requisicao, material):

    try:

        remetente = st.secrets["email"]["remetente"]

        senha = st.secrets["email"]["senha"]

        destinatario = email_solicitante

        corpo_mensagem = f"""

        Olá, {solicitante_nome}.

        Gostaríamos de informar que o material **{material}** da requisição **{numero_requisicao}** se encontra disponível para retirada no almoxarifado.

        Por favor, entre em contato com o setor responsavel para mais informações.

        Atenciosamente, Equipe de Suprimentos

        """

        mensagem = MIMEMultipart()

        mensagem['From'] = remetente

        mensagem['To'] = destinatario

        mensagem['Subject'] = f"Material Entregue - Requisição {numero_requisicao}"

        mensagem.attach(MIMEText(corpo_mensagem, 'plain'))



        servidor_smtp = smtplib.SMTP('smtp.gmail.com', 587)

        servidor_smtp.starttls()

        servidor_smtp.login(remetente, senha)

        texto = mensagem.as_string()

        servidor_smtp.sendmail(remetente, destinatario, texto)

        servidor_smtp.quit()

        st.success(f"E-mail de confirmação enviado para {destinatario}.")

        return True

    except Exception as e:

        st.error(f"❌ Erro ao enviar e-mail: {e}. O problema pode ser na conexão ou credenciais do Gmail.")

        return False



# --- INTERFACE PRINCIPAL ---

if 'logado' not in st.session_state or not st.session_state['logado']:

    st.title("🏭 Login do Almoxarifado")

    with st.form("login_form"):

        email = st.text_input("E-mail")

        senha = st.text_input("Senha", type="password")

        if st.form_submit_button("Entrar"):

            fazer_login(email, senha)

else:

    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"

    logo_img = load_logo(logo_url)

    

    # O carregamento de dados é feito na inicialização do script para evitar cache inconsistente

    df_pedidos = carregar_dados_pedidos()

    df_almoxarifado = carregar_dados_almoxarifado()



    if 'df_pedidos' not in st.session_state:

        st.session_state.df_pedidos = df_pedidos

    if 'df_almoxarifado' not in st.session_state:

        st.session_state.df_almoxarifado = df_almoxarifado

    

    # Carrega dados dos solicitantes de forma separada

    df_solicitantes = carregar_dados_solicitantes()



    if logo_img:

        st.sidebar.image(logo_img, use_container_width=True)

    

    st.sidebar.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")

    st.sidebar.title("Menu de Navegação")

    menu_option = st.sidebar.radio(

        "Selecione a opção:",

        ["📝 Registrar NF", "📊 Dashboard", "🔍 Consultar NFs", "⚙️ Configurações"],

        index=0

    )

    st.sidebar.divider()

    if st.sidebar.button("Logout"):

        st.session_state['logado'] = False

        st.session_state.pop('nome_colaborador', None)

        st.rerun()

    

    if menu_option == "📝 Registrar NF":

        st.markdown("""

            <div class='header-container'>

                <h1>🏭 REGISTRAR NOTA FISCAL</h1>

                <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>

            </div>

        """, unsafe_allow_html=True)

        

        with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):

            with st.form("formulario_nota", clear_on_submit=True):

                col1, col2, col3 = st.columns(3)

                

                with col1:

                    data_recebimento = st.date_input("Data do Recebimento*", datetime.date.today())

                    

                    fornecedores_disponiveis = df_pedidos['FORNECEDOR'].dropna().unique().tolist() if 'FORNECEDOR' in df_pedidos.columns else []

                    fornecedor_nf = st.selectbox("Fornecedor da NF*", options=[''] + sorted(fornecedores_disponiveis))

                    

                    if fornecedor_nf == '':

                        fornecedor_manual = st.text_input("Novo Fornecedor (opcional)", placeholder="Digite o nome se não estiver na lista...")

                    else:

                        fornecedor_manual = ""

                    

                    nf_numero = st.text_input("Número da NF*")

                    

                with col2:

                    recebedor_options = [

                        "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",

                        "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",

                        "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",

                        "OUTROS"

                    ]

                    recebedor = st.selectbox("Recebedor*", sorted(recebedor_options))

                    ordem_compra_nf = st.text_input("N° Ordem de Compra*", help="Número da ordem de compra para vincular a nota")

                    volume_nf = st.number_input("Volume*", min_value=1, value=1)

                    

                with col3:

                    valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")

                    condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"])

                    valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00")

                

                doc_nf_link = st.text_input("Link da Nota Fiscal (URL)", placeholder="Cole o link de acesso aqui...")

                

                observacao = st.text_area("Observações", placeholder="Informações adicionais...")

                vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))

                

                enviar = st.form_submit_button("✅ Registrar Nota Fiscal")

                

                if enviar:

                    nome_final_fornecedor = fornecedor_manual if fornecedor_manual else fornecedor_nf

                    campos_validos = all([

                        nome_final_fornecedor.strip(), nf_numero.strip(), ordem_compra_nf.strip(),

                        valor_total_nf.strip() not in ["", "0,00"]

                    ])

                    

                    if not campos_validos:

                        st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")

                    else:

                        try:

                            valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))

                            valor_frete_float = float(valor_frete_nf.replace(".", "").replace(",", "."))

                            

                            if 'ORDEM_COMPRA' in st.session_state.df_pedidos.columns:

                                df_update_pedidos = st.session_state.df_pedidos[st.session_state.df_pedidos['ORDEM_COMPRA'] == ordem_compra_nf].copy()

                                

                                if not df_update_pedidos.empty:

                                    for original_index in df_update_pedidos.index:

                                        st.session_state.df_pedidos.loc[original_index, 'STATUS_PEDIDO'] = 'ENTREGUE'

                                        st.session_state.df_pedidos.loc[original_index, 'DATA_ENTREGA'] = pd.to_datetime(data_recebimento)

                                

                                salvar_dados_pedidos(st.session_state.df_pedidos)

                            else:

                                st.warning(f"ℹ️ A OC '{ordem_compra_nf}' não foi encontrada nos pedidos. O status não foi atualizado.")

                            

                            novo_registro_nf = {

                                "DATA": pd.to_datetime(data_recebimento),

                                "RECEBEDOR": recebedor,

                                "FORNECEDOR": nome_final_fornecedor,

                                "NF": nf_numero,

                                "VOLUME": volume_nf,

                                "V. TOTAL NF": valor_total_float,

                                "CONDICAO FRETE": condicao_frete_nf,

                                "VALOR FRETE": valor_frete_float,

                                "OBSERVACAO": observacao,

                                "DOC NF": doc_nf_link,

                                "VENCIMENTO": pd.to_datetime(vencimento_nf),

                                "STATUS_FINANCEIRO": "EM ANDAMENTO",

                                "CONDICAO_PROBLEMA": "N/A",

                                "REGISTRO_ADICIONAL": "",

                                "ORDEM_COMPRA": ordem_compra_nf

                            }

                            st.session_state.df_almoxarifado = pd.concat([st.session_state.df_almoxarifado, pd.DataFrame([novo_registro_nf])], ignore_index=True)

                            

                            if salvar_dados_almoxarifado(st.session_state.df_almoxarifado):

                                st.success(f"🎉 Nota fiscal {nf_numero} registrada com sucesso!")

                                if 'NOME' in df_solicitantes.columns and 'EMAIL' in df_solicitantes.columns:

                                    email_solicitante = df_solicitantes[df_solicitantes['NOME'] == recebedor]['EMAIL'].iloc[0] if recebedor in df_solicitantes['NOME'].values else None

                                    if email_solicitante:

                                        material_pedido = st.session_state.df_pedidos[st.session_state.df_pedidos['ORDEM_COMPRA'] == ordem_compra_nf]['MATERIAL'].iloc[0] if not df_update_pedidos.empty and 'MATERIAL' in df_update_pedidos.columns else "N/A"

                                        enviar_email_entrega(recebedor, email_solicitante, ordem_compra_nf, material_pedido)

                                else:

                                    st.warning("Aviso: As colunas 'NOME' ou 'EMAIL' não foram encontradas na planilha de solicitantes. O e-mail não foi enviado.")

                            else:

                                st.error("Erro ao salvar os dados da nota fiscal.")

                        

                            st.balloons()

                            st.rerun()

                        except ValueError:

                            st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")

        

        st.markdown("---")

        st.subheader("Últimas Notas Registradas")

        if not st.session_state.df_almoxarifado.empty:

            df_ultimas_nfs = st.session_state.df_almoxarifado[st.session_state.df_almoxarifado['NF'].astype(str) != ''].tail(10)

            

            st.dataframe(

                df_ultimas_nfs,

                use_container_width=True,

                column_config={

                    "DOC NF": st.column_config.LinkColumn(

                        "DOC NF",

                        help="Clique para abrir a nota fiscal.",

                        display_text="📥 Abrir NF"

                    )

                }

            )

        else:

            st.info("Nenhuma nota fiscal registrada ainda. Registre uma acima.")





    elif menu_option == "📊 Dashboard":

        st.markdown("""

            <div class='header-container'>

                <h1>📊 DASHBOARD ALMOXARIFADO</h1>

                <p>Análise estratégica dos custos por departamento</p>

            </div>

        """, unsafe_allow_html=True)

        

        df = st.session_state.df_almoxarifado

        if not df.empty:

            df_almoxarifado_filtrado = df[df['NF'].astype(str) != '']

            

            col1, col2, col3, col4 = st.columns(4)

            

            total_nfs = len(df_almoxarifado_filtrado)

            em_andamento = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'EM ANDAMENTO'])

            com_problema = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'NF PROBLEMA'])

            finalizadas = len(df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'FINALIZADO'])

            

            with col1: st.metric("📦 Total de NFs", total_nfs)

            with col2: st.metric("🔄 Em Andamento", em_andamento)

            with col3: st.metric("⚠️ Com Problema", com_problema)

            with col4: st.metric("✅ Finalizadas", finalizadas)

            

            st.subheader("📈 Análise do Status Financeiro")

            

            col_g1, col_g2 = st.columns(2)

            

            with col_g1:

                status_count = df_almoxarifado_filtrado['STATUS_FINANCEIRO'].value_counts().reset_index()

                status_count.columns = ['Status', 'Quantidade']

                if not status_count.empty:

                    fig_pizza = px.pie(status_count, values='Quantidade', names='Status', title='Distribuição dos Status Financeiros')

                    st.plotly_chart(fig_pizza, use_container_width=True)

            

            with col_g2:

                problemas_df = df_almoxarifado_filtrado[df_almoxarifado_filtrado['STATUS_FINANCEIRO'] == 'NF PROBLEMA']

                if not problemas_df.empty:

                    top_problemas = problemas_df['FORNECEDOR'].value_counts().head(10).reset_index()

                    top_problemas.columns = ['Fornecedor', 'Notas com Problema']

                    fig_barras = px.bar(top_problemas, x='Notas com Problema', y='Fornecedor', orientation='h', title='Top 10 Fornecedores com Problemas')

                    st.plotly_chart(fig_barras, use_container_width=True)

                else:

                    st.info("✅ Nenhuma nota com problemas no momento")

            

        else:

            st.write("Nenhum dado disponível.")



    elif menu_option == "🔍 Consultar NFs":

        st.markdown("""

            <div class='header-container'>

                <h1>🔍 CONSULTAR NOTAS FISCAIS</h1>

                <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>

            </div>

        """, unsafe_allow_html=True)

        

        df_almox = st.session_state.df_almoxarifado.copy()

        

        df = df_almox.copy()

        

        if not df.empty:

            st.subheader("🔎 Consulta Avançada")

            col1, col2 = st.columns(2)

            

            with col1:

                nf_consulta = st.text_input("Buscar por Número da NF", placeholder="Digite o número da NF...")

                ordem_compra_consulta = st.text_input("Buscar por N° Ordem de Compra", placeholder="Digite o número da OC...")

                fornecedor_consulta = st.selectbox("Filtrar por Fornecedor", options=["Todos"] + sorted(df['FORNECEDOR'].dropna().unique().tolist()))

            

            with col2:

                status_consulta = st.multiselect("Filtrar por Status", options=["Todos"] + status_financeiro_options, default=["Todos"])

                

                if not df['DATA'].isnull().all():

                    data_minima = df['DATA'].min().date() if pd.notna(df['DATA'].min()) else datetime.date.today()

                    data_maxima = df['DATA'].max().date() if pd.notna(df['DATA'].max()) else datetime.date.today()

                else:

                    data_minima = datetime.date.today()

                    data_maxima = datetime.date.today()



                data_inicio_consulta = st.date_input("Data Início", value=data_minima, min_value=data_minima, max_value=data_maxima)

                data_fim_consulta = st.date_input("Data Fim", value=data_maxima, min_value=data_minima, max_value=data_maxima)



            df_consulta = df.copy()

            

            if nf_consulta: df_consulta = df_consulta[df_consulta['NF'].astype(str).str.contains(nf_consulta, case=False)]

            if ordem_compra_consulta: df_consulta = df_consulta[df_consulta['ORDEM_COMPRA'].astype(str).str.contains(ordem_compra_consulta, case=False)]

            if fornecedor_consulta != "Todos": df_consulta = df_consulta[df_consulta['FORNECEDOR'] == fornecedor_consulta]

            if "Todos" not in status_consulta: df_consulta = df_consulta[df_consulta['STATUS_FINANCEIRO'].isin(status_consulta)]

            

            df_consulta = df_consulta[

                (df_consulta['DATA'].dt.date >= data_inicio_consulta) &

                (df_consulta['DATA'].dt.date <= data_fim_consulta)

            ]

            

            st.subheader(f"📋 Resultados da Consulta ({len(df_consulta)} notas encontradas)")

            

            if not df_consulta.empty:

                df_exibir_consulta = df_consulta[[

                    'DATA', 'FORNECEDOR', 'NF', 'ORDEM_COMPRA', 'VOLUME', 'V. TOTAL NF',

                    'STATUS_FINANCEIRO', 'CONDICAO_PROBLEMA', 'OBSERVACAO', 'VENCIMENTO', 'DOC NF', 'VALOR FRETE'

                ]].copy()

                

                df_exibir_consulta['DATA'] = df_exibir_consulta['DATA'].dt.strftime('%d/%m/%Y')

                df_exibir_consulta['VENCIMENTO'] = df_exibir_consulta['VENCIMENTO'].dt.strftime('%d/%m/%Y')

                df_exibir_consulta['V. TOTAL NF'] = df_exibir_consulta['V. TOTAL NF'].apply(

                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                )

                df_exibir_consulta['VALOR FRETE'] = df_exibir_consulta['VALOR FRETE'].apply(

                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                )

                

                st.dataframe(

                    df_exibir_consulta,

                    use_container_width=True,

                    height=400,

                    column_config={

                        "DOC NF": st.column_config.LinkColumn(

                            "DOC NF",

                            help="Clique para abrir a nota fiscal.",

                            display_text="📥 Abrir NF"

                        )

                    }

                )

                

                csv_consulta = df_exibir_consulta.to_csv(index=False, encoding='utf-8')

                st.download_button(

                    label="📥 Download Resultados",

                    data=csv_consulta,

                    file_name="consulta_nfs.csv",

                    mime="text/csv"

                )

            else:

                st.warning("⚠️ Nenhuma nota fiscal encontrada com os filtros aplicados.")

        else:

            st.info("📝 Nenhum dado disponível para consulta.")



    elif menu_option == "⚙️ Configurações":

        st.markdown("""

            <div class='header-container'>

                <h1>⚙️ CONFIGURAÇÕES DO SISTEMA</h1>

                <p>Sistema de Controle de Notas Fiscais e Status Financeiro</p>

            </div>

        """, unsafe_allow_html=True)

        

        df = st.session_state.df_almoxarifado

        

        st.subheader("⚙️ Configurações Gerais")

        col1, col2 = st.columns(2)

        

        with col1:

            st.info("**Informações do Sistema**")

            st.write(f"Total de notas cadastradas: **{len(df)}**")

            st.write(f"Última atualização: **{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}**")

            

            if st.button("🔄 Recarregar Dados"):

                st.session_state.df_pedidos = carregar_dados_pedidos()

                st.session_state.df_almoxarifado = carregar_dados_almoxarifado()

                st.success("Dados recarregados com sucesso!")

                st.rerun()

        

        with col2:

            st.info("**Manutenção**")

            st.write("Versão: 1.0")

            

            csv_backup = df.to_csv(index=False, encoding='utf-8')

            st.download_button(

                label="💾 Fazer Backup",

                data=csv_backup,

                file_name=f"backup_almoxarifado_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",

                mime="text/csv",

                help="Clique para baixar uma cópia de segurança dos dados."

            )



        st.subheader("📋 Log de Atividades")

        if 'log_messages' in st.session_state:

            log_text = "\n".join(st.session_state['log_messages'])

            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)

        else:

            st.info("Nenhum log disponível.")
