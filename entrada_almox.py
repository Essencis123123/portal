import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from pandas.errors import EmptyDataError
import numpy as np
import os
import requests
from PIL import Image
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Almoxarifado", layout="wide", page_icon="🏭")

# CSS para personalizar o menu lateral e garantir que todo o texto seja branco
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #1C4D86;
    }
    
    /* Regras para garantir que TODO o texto no sidebar seja branco */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j p, 
    [data-testid="stSidebar"] .st-emotion-cache-1ky8k0j {
        color: white !important;
    }
    
    /* Estilos para o radio button, garantindo que o texto dele também seja branco */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span {
        color: white !important;
    }
    
    /* Estilo para deixar a letra dos botões preta */
    [data-testid="stSidebar"] .stButton button p {
        color: black !important;
    }

    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 80%;
        border-radius: 10px;
        padding: 10px 0;
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

# Funções de carregamento e salvamento de dados
@st.cache_data
def carregar_dados_almoxarifado():
    try:
        df = pd.read_csv("dados_pedidos.csv")
        
        dtype_dict = {'FORNECEDOR': str, 'ORDEM_COMPRA': str, 'MATERIAL': str, 'RECEBEDOR': str,
                      'OBSERVACAO': str, 'DOC NF': str, 'CONDICAO_FRETE': str, 'REQUISICAO': str,
                      'SOLICITANTE': str, 'DEPARTAMENTO': str, 'FILIAL': str, 'NF': str}
        for col in dtype_dict:
            if col in df.columns:
                df[col] = df[col].astype(dtype_dict[col])
        
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'VENCIMENTO']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        if 'NF' not in df.columns: df['NF'] = ''
        if 'STATUS_FINANCEIRO' not in df.columns: df['STATUS_FINANCEIRO'] = "N/A"
        if 'CONDICAO_PROBLEMA' not in df.columns: df['CONDICAO_PROBLEMA'] = "N/A"
        if 'REGISTRO_ADICIONAL' not in df.columns: df['REGISTRO_ADICIONAL'] = ""
        if 'V. TOTAL NF' not in df.columns: df['V. TOTAL NF'] = 0.0
        if 'OBSERVACAO' not in df.columns: df['OBSERVACAO'] = ""
        if 'VENCIMENTO' not in df.columns: df['VENCIMENTO'] = pd.NaT
        if 'STATUS_PEDIDO' not in df.columns: df['STATUS_PEDIDO'] = "PENDENTE"
        if 'DATA_ENTREGA' not in df.columns: df['DATA_ENTREGA'] = pd.NaT
        if 'VALOR_RENEGOCIADO' not in df.columns: df['VALOR_RENEGOCIADO'] = 0.0
        if 'PEDIDO' not in df.columns: df['PEDIDO'] = ''
        if 'VOLUME' not in df.columns: df['VOLUME'] = 0
        if 'VALOR_FRETE' not in df.columns: df['VALOR_FRETE'] = 0.0
        if 'DOC NF' not in df.columns: df['DOC NF'] = ''
        if 'CONDICAO FRETE' not in df.columns: df['CONDICAO FRETE'] = ''

        return df
    except (FileNotFoundError, EmptyDataError):
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "VOLUME", "V. TOTAL NF",
            "CONDICAO FRETE", "VALOR FRETE", "OBSERVACAO", "DOC NF", "VENCIMENTO",
            "STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",
            "REQUISICAO", "MATERIAL", "QUANTIDADE", "FILIAL", "DEPARTAMENTO",
            "SOLICITANTE", "ORDEM_COMPRA", "VALOR_ITEM", "DATA_APROVACAO", "TIPO_PEDIDO",
            "STATUS_PEDIDO", "DATA_ENTREGA", "VALOR_RENEGOCIADO"
        ])

def salvar_dados_almoxarifado(df):
    try:
        df_copy = df.copy()
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'VENCIMENTO']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
        df_copy.to_csv("dados_pedidos.csv", index=False, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False

@st.cache_data
def carregar_dados_solicitantes():
    try:
        df = pd.read_csv("dados_solicitantes.csv", dtype={'NOME': str, 'DEPARTAMENTO': str, 'EMAIL': str, 'FILIAL': str})
        return df
    except (FileNotFoundError, EmptyDataError):
        return pd.DataFrame(columns=["NOME", "DEPARTAMENTO", "EMAIL", "FILIAL"])

# --- Configurações e Funções de E-mail ---
status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]
logo_url = "https://media.licdn.com/dms/image/v2/C560BAQHJFSN_XUibJw/company-logo_200_200/company-logo_200_200/0/1675703958506/essencismg_logo?e=2147483647&v=beta&t=ZNEo5jZJnySYCy2VbJdq1AMvUVreiPP0V3sK4Ku1nX0"
logo_img = load_logo(logo_url)

# Adiciona uma lista de log na sessão
if 'log_messages' not in st.session_state:
    st.session_state['log_messages'] = []

def adicionar_log(mensagem):
    """Adiciona uma mensagem de log à lista da sessão e a imprime no terminal."""
    st.session_state['log_messages'].append(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensagem}")
    print(st.session_state['log_messages'][-1])

# Credenciais fixas da conta do Gmail para envio de e-mails
GMAIL_EMAIL = "suprimentosessencis@gmail.com"
GMAIL_APP_PASSWORD = "wvap juiz axkf xqcw"

def enviar_email_entrega(solicitante_nome, email_solicitante, numero_requisicao, material):
    remetente = GMAIL_EMAIL
    senha = GMAIL_APP_PASSWORD
    destinatario = email_solicitante

    adicionar_log(f"Tentando enviar e-mail para: {destinatario}...")
    
    corpo_mensagem = f"""
    Olá, {solicitante_nome}.

    Gostaríamos de informar que o material **{material}** da requisição **{numero_requisicao}** se encontra disponível para retirada no almoxarifado.

    Por favor, entre em contato com o setor responsavel para mais informações.

    Atenciosamente,
    Equipe de Suprimentos
    """
    mensagem = MIMEMultipart()
    mensagem['From'] = remetente
    mensagem['To'] = destinatario
    mensagem['Subject'] = f"Material Entregue - Requisição {numero_requisicao}"
    mensagem.attach(MIMEText(corpo_mensagem, 'plain'))
    
    try:
        servidor_smtp = smtplib.SMTP('smtp.gmail.com', 587)
        servidor_smtp.starttls()
        servidor_smtp.login(remetente, senha)
        texto = mensagem.as_string()
        servidor_smtp.sendmail(remetente, destinatario, texto)
        servidor_smtp.quit()
        adicionar_log(f"E-mail de confirmação enviado para {destinatario}.")
        return True
    except Exception as e:
        adicionar_log(f"Erro ao enviar e-mail: {e}.")
        st.error(f"❌ Erro ao enviar e-mail: {e}. O problema pode ser na conexão ou credenciais do Gmail.")
        return False

# --- LÓGICA DE LOGIN ---
# Dicionário de usuários com nome completo e senha
USERS = {
    "eassis@essencis.com.br": {"password": "Essencis01", "name": "EVIANE DAS GRACAS DE ASSIS"},
    "agsantos@essencis.com.br": {"password": "Essencis01", "name": "ARLEY GONCALVES DOS SANTOS"},
    "isoares@essencis.com.br": {"password": "Essencis01", "name": "ISABELA CAROLINA DE PAULA SOARES"},
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

# --- INTERFACE PRINCIPAL ---
if 'logado' not in st.session_state or not st.session_state['logado']:
    st.title("🏭 Login do Almoxarifado")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    logo_img = load_logo("https://media.licdn.com/dms/image/v2/C560BAQHJFSN_XUibJw/company-logo_200_200/company-logo_200_200/0/1675703958506/essencismg_logo?e=2147483647&v=beta&t=ZNEo5jZJnySYCy2VbJdq1AMvUVreiPP0V3sK4Ku1nX0")
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
    
    df_pedidos = carregar_dados_almoxarifado()
    df_solicitantes = carregar_dados_solicitantes()

    if menu_option == "📝 Registrar NF":
        st.markdown("""
            <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
                <h1 style='color: white; text-align: center; margin: 0;'>🏭 REGISTRAR NOTA FISCAL</h1>
                <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
            with st.form("formulario_nota", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    data_recebimento = st.date_input("Data do Recebimento*", datetime.date.today())
                    fornecedor_nf = st.text_input("Fornecedor da NF*", placeholder="Nome do fornecedor...")
                    nf_numero = st.text_input("Número da NF*")
                    
                with col2:
                    recebedor = st.selectbox("Recebedor*", [
                        "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                        "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                        "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                        "OUTROS"
                    ])
                    ordem_compra_nf = st.text_input("N° Ordem de Compra*", help="Número da ordem de compra para vincular a nota")
                    volume_nf = st.number_input("Volume*", min_value=1, value=1)
                    
                with col3:
                    valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")
                    condicao_frete_nf = st.selectbox("Condição de Frete", ["CIF", "FOB"])
                    valor_frete_nf = st.text_input("Valor Frete (ex: 123,45)", value="0,00") if condicao_frete_nf == "FOB" else "0,00"
                
                # ADIÇÃO DO NOVO CAMPO DE LINK
                doc_nf_link = st.text_input("Link da Nota Fiscal (URL)", placeholder="Cole o link de acesso aqui...")
                
                observacao = st.text_area("Observações", placeholder="Informações adicionais...")
                vencimento_nf = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))
                
                enviar = st.form_submit_button("✅ Registrar Nota Fiscal")
                
                if enviar:
                    campos_validos = all([
                        fornecedor_nf.strip(), nf_numero.strip(), ordem_compra_nf.strip(), 
                        valor_total_nf.strip() not in ["", "0,00"]
                    ])
                    
                    if not campos_validos:
                        st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                    else:
                        st.session_state['log_messages'] = []
                        adicionar_log("Formulário validado. Iniciando registro da nota fiscal.")
                        
                        try:
                            valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                            valor_frete_float = float(valor_frete_nf.replace(".", "").replace(",", "."))
                            
                            df_pedidos_orig = carregar_dados_almoxarifado()
                            
                            df_update = df_pedidos_orig[df_pedidos_orig['ORDEM_COMPRA'] == ordem_compra_nf].copy()
                            
                            if not df_update.empty:
                                for original_index in df_update.index:
                                    df_pedidos_orig.loc[original_index, 'STATUS_PEDIDO'] = 'ENTREGUE'
                                    df_pedidos_orig.loc[original_index, 'DATA_ENTREGA'] = pd.to_datetime(data_recebimento)
                                    df_pedidos_orig.loc[original_index, 'STATUS_FINANCEIRO'] = 'EM ANDAMENTO'
                                    df_pedidos_orig.loc[original_index, 'NF'] = nf_numero
                                    df_pedidos_orig.loc[original_index, 'V. TOTAL NF'] = valor_total_float
                                    df_pedidos_orig.loc[original_index, 'CONDICAO_FRETE'] = condicao_frete_nf
                                    df_pedidos_orig.loc[original_index, 'VALOR_FRETE'] = valor_frete_float
                                    df_pedidos_orig.loc[original_index, 'OBSERVACAO'] = observacao
                                    df_pedidos_orig.loc[original_index, 'VENCIMENTO'] = pd.to_datetime(vencimento_nf)
                                    df_pedidos_orig.loc[original_index, 'RECEBEDOR'] = recebedor
                                    # ATUALIZAÇÃO DO CAMPO LINK
                                    df_pedidos_orig.loc[original_index, 'DOC NF'] = doc_nf_link

                                solicitante_nome = df_update.iloc[0]['SOLICITANTE']
                                adicionar_log(f"Buscando e-mail para o solicitante '{solicitante_nome}'.")
                                if pd.notna(solicitante_nome) and solicitante_nome != '':
                                    df_solicitantes_orig = carregar_dados_solicitantes()
                                    email_solicitante_df = df_solicitantes_orig[df_solicitantes_orig['NOME'].str.contains(solicitante_nome, case=False, na=False)]
                                    if not email_solicitante_df.empty:
                                        enviar_email_entrega(solicitante_nome, email_solicitante_df.iloc[0]['EMAIL'], df_update.iloc[0]['REQUISICAO'], df_update.iloc[0]['MATERIAL'])
                                    else:
                                        st.warning(f"O e-mail para o solicitante '{solicitante_nome}' não foi encontrado na base de dados. O e-mail não foi enviado.")
                                        adicionar_log(f"Aviso: E-mail não encontrado para '{solicitante_nome}'.")
                                else:
                                    st.warning("O nome do solicitante não foi preenchido no pedido de compra. E-mail de notificação não enviado.")
                                    adicionar_log("Aviso: Nome do solicitante não preenchido no pedido de compra.")
                                
                                salvar_dados_almoxarifado(df_pedidos_orig)
                                st.success(f"🎉 Nota fiscal registrada! O pedido com a OC '{ordem_compra_nf}' foi atualizado como ENTREGUE no painel do comprador.")
                            else:
                                novo_registro = {
                                    "DATA": pd.to_datetime(data_recebimento),
                                    "RECEBEDOR": recebedor,
                                    "FORNECEDOR": fornecedor_nf,
                                    "NF": nf_numero,
                                    "REQUISICAO": np.nan,
                                    "VOLUME": volume_nf,
                                    "V. TOTAL NF": valor_total_float,
                                    "CONDICAO_FRETE": condicao_frete_nf,
                                    "VALOR_FRETE": valor_frete_float,
                                    "OBSERVACAO": observacao,
                                    "DOC NF": doc_nf_link, # SALVANDO O NOVO CAMPO
                                    "VENCIMENTO": pd.to_datetime(vencimento_nf),
                                    "STATUS_FINANCEIRO": "EM ANDAMENTO",
                                    "STATUS_PEDIDO": "PENDENTE",
                                    "DATA_ENTREGA": pd.NaT,
                                    "ORDEM_COMPRA": ordem_compra_nf,
                                    "VALOR_ITEM": 0.0,
                                    "VALOR_RENEGOCIADO": 0.0
                                }
                                df_pedidos_orig = pd.concat([df_pedidos_orig, pd.DataFrame([novo_registro])], ignore_index=True)
                                salvar_dados_almoxarifado(df_pedidos_orig)
                                st.warning(f"ℹ️ Nota fiscal registrada. A OC '{ordem_compra_nf}' não foi encontrada para atualização automática. Os dados foram salvos como um novo registro.")
                                adicionar_log(f"Aviso: OC '{ordem_compra_nf}' não encontrada, nota registrada como novo registro.")
                        
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
                        
                        except ValueError:
                            st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")
                            adicionar_log("Erro: Falha na conversão de valores numéricos do formulário.")

    elif menu_option == "📊 Dashboard":
        df = carregar_dados_almoxarifado()

        st.markdown("""
            <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
                <h1 style='color: white; text-align: center; margin: 0;'>🏭 DASHBOARD ALMOXARIFADO</h1>
                <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
            </div>
        """, unsafe_allow_html=True)
        
        if not df.empty:
            df_almoxarifado = df.copy()
            
            col1, col2, col3, col4 = st.columns(4)
            df_almoxarifado_filtrado = df_almoxarifado[df_almoxarifado['NF'].astype(str) != '']
            
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
        df = carregar_dados_almoxarifado()

        st.markdown("""
            <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
                <h1 style='color: white; text-align: center; margin: 0;'>🏭 CONSULTAR NOTAS FISCAIS</h1>
                <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
            </div>
        """, unsafe_allow_html=True)
        
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
                    'DATA', 'FORNECEDOR', 'NF', 'ORDEM_COMPRA', 'REQUISICAO', 'V. TOTAL NF', 
                    'STATUS_FINANCEIRO', 'CONDICAO_PROBLEMA', 'OBSERVACAO', 'VENCIMENTO', 'DOC NF' # INCLUINDO DOC NF NA VISUALIZAÇÃO
                ]].copy()
                
                df_exibir_consulta['DATA'] = df_exibir_consulta['DATA'].dt.strftime('%d/%m/%Y')
                df_exibir_consulta['VENCIMENTO'] = df_exibir_consulta['VENCIMENTO'].dt.strftime('%d/%m/%Y')
                df_exibir_consulta['V. TOTAL NF'] = df_exibir_consulta['V. TOTAL NF'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                
                st.dataframe(df_exibir_consulta, use_container_width=True, height=400)
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
        df = carregar_dados_almoxarifado()

        st.markdown("""
            <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
                <h1 style='color: white; text-align: center; margin: 0;'>🏭 CONFIGURAÇÕES DO SISTEMA</h1>
                <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.subheader("⚙️ Configurações Gerais")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Informações do Sistema**")
            st.write(f"Total de notas cadastradas: **{len(df)}**")
            st.write(f"Última atualização: **{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}**")
            
            if st.button("🔄 Recarregar Dados"):
                st.cache_data.clear()
                st.success("Dados recarregados com sucesso!")
                st.rerun()
        
        with col2:
            st.info("**Manutenção**")
            st.write("Versão: 1.0")
            
            if st.button("💾 Fazer Backup"):
                try:
                    backup_filename = f"backup_almoxarifado_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(backup_filename, index=False, encoding='utf-8')
                    st.success(f"Backup realizado com sucesso: {backup_filename}")
                except Exception as e:
                    st.error(f"Erro ao fazer backup: {e}")

        st.subheader("📋 Log de Atividades")
        if 'log_messages' in st.session_state:
            log_text = "\n".join(st.session_state['log_messages'])
            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)
        else:
            st.info("Nenhum log disponível.")
