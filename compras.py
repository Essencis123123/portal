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
import json # Importa a biblioteca json para a correção

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Financeiro - Almoxarifado", layout="wide", page_icon="💼")

# --- CSS Personalizado para o Tema Essencis ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #1C4D86;
        color: white;
    }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
    .stDownloadButton button p { color: white !important; }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span { color: white !important; }

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

    [data-testid="stMetric"] > div {
        background-color: #f0f2f5; color: #1C4D86; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Carregar a imagem do logo a partir da URL
@st.cache_data(show_spinner=False)
def load_logo(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception:
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- FUNÇÕES DE CONEXÃO E CARREGAMENTO DA PLANILHA ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta com o Google Sheets usando os secrets do Streamlit."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Pega as credenciais como string
    creds_string = st.secrets["gcp_service_account"]
    
    # Converte a string JSON para um dicionário Python
    creds_json = json.loads(creds_string)
    
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def _to_datetime(series):
    """Converte para datetime com dayfirst, tolerante a strings, date e NaT."""
    return pd.to_datetime(series, errors="coerce", dayfirst=True)

def carregar_dados() -> pd.DataFrame:
    """
    Carrega os dados da aba 'Almoxarifado' da planilha 'dados_pedido' do Google Sheets
    e prepara para o painel fiscal.
    """
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df = pd.DataFrame(worksheet.get_all_records())

        if df.empty or all(pd.Series(df.columns).isnull()):
            st.warning("A planilha existe, mas está vazia. Adicione dados pelo Painel do Almoxarifado.")
            return pd.DataFrame(columns=[
                "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "STATUS",
                "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE",
                "DOC_NF", "RECEBEDOR", "VENCIMENTO", "DIAS_VENCIMENTO"
            ])

        # Padroniza todas as colunas em uma única etapa para evitar inconsistências
        df.columns = df.columns.str.strip().str.upper().str.replace('.', '').str.replace(' ', '_').str.replace('/', '_')

        # Renomeia com um mapeamento explícito para garantir nomes internos consistentes
        df = df.rename(columns={
            'STATUS_FINANCEIRO': 'STATUS',
            'OBSERVACAO': 'REGISTRO_ADICIONAL',
            'FORNECEDOR_NF': 'FORNECEDOR',
            'V_TOTAL_NF': 'V_TOTAL_NF', # Reafirma para consistência
            'DOC_NF': 'DOC_NF', # Reafirma para consistência
        }, errors='ignore')

        # Remove linhas totalmente vazias, aparar espaços
        df = df.dropna(how='all')
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Garante colunas essenciais
        colunas_necessarias = {
            "DATA": None,
            "FORNECEDOR": "",
            "NF": "",
            "ORDEM_COMPRA": "",
            "V_TOTAL_NF": 0.0,
            "VENCIMENTO": None,
            "STATUS": "EM ANDAMENTO",
            "CONDICAO_PROBLEMA": "N/A",
            "REGISTRO_ADICIONAL": "",
            "VALOR_JUROS": 0.0,
            "VALOR_FRETE": 0.0,
            "DOC_NF": "",
            "RECEBEDOR": ""
        }
        for col, default_val in colunas_necessarias.items():
            if col not in df.columns:
                df[col] = default_val

        # Tipos numéricos
        for c in ["V_TOTAL_NF", "VALOR_JUROS", "VALOR_FRETE"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        # Datas
        df["DATA"] = _to_datetime(df["DATA"])
        df["VENCIMENTO"] = _to_datetime(df["VENCIMENTO"])

        # DIAS_VENCIMENTO (robusto)
        ref = pd.Timestamp.today().normalize()
        df["DIAS_VENCIMENTO"] = (df["VENCIMENTO"] - ref).dt.days.fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha. Verifique nome/aba/credenciais. Detalhe: {e}")
        return pd.DataFrame(columns=[
            "DATA","FORNECEDOR","NF","ORDEM_COMPRA","V_TOTAL_NF","STATUS",
            "CONDICAO_PROBLEMA","REGISTRO_ADICIONAL","VALOR_JUROS","VALOR_FRETE",
            "DOC_NF","RECEBEDOR","VENCIMENTO","DIAS_VENCIMENTO"
        ])

def salvar_dados(df: pd.DataFrame) -> bool:
    """Salva o DataFrame na aba 'Almoxarifado' do Google Sheets."""
    try:
        client = get_gspread_client()
        sheet = client.open("dados_pedido")
        worksheet = sheet.worksheet("Almoxarifado")

        df_to_save = df.copy()

        # Garante tipos antes de formatar
        df_to_save["DATA"] = _to_datetime(df_to_save["DATA"])
        df_to_save["VENCIMENTO"] = _to_datetime(df_to_save["VENCIMENTO"])

        # Mapeia para nomes da planilha
        df_to_save = df_to_save.rename(columns={
            "STATUS": "STATUS_FINANCEIRO",
            "REGISTRO_ADICIONAL": "OBSERVACAO",
            "V_TOTAL_NF": "V. TOTAL NF",
            "DOC_NF": "DOC NF",
            "FORNECEDOR": "FORNECEDOR_NF"
        })

        # Formata datas como string dd/mm/yyyy
        if "DATA" in df_to_save.columns:
            df_to_save["DATA"] = df_to_save["DATA"].dt.strftime("%d/%m/%Y")
        if "VENCIMENTO" in df_to_save.columns:
            df_to_save["VENCIMENTO"] = df_to_save["VENCIMENTO"].dt.strftime("%d/%m/%Y")

        # Remove colunas de cálculo antes de salvar
        df_to_save = df_to_save.drop(columns=["DIAS_VENCIMENTO"], errors="ignore")

        # Escreve a partir de A1 (não limpa sobra; seguro contra perdas)
        set_with_dataframe(worksheet, df_to_save, include_index=False, resize=True)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados na planilha: {e}")
        return False

# --- Lógica de Login (UNIFICADA) ---
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
        time.sleep(1)
        st.rerun()
    else:
        st.error("E-mail ou senha incorretos.")

# --- INICIALIZAÇÃO E LAYOUT DA PÁGINA ---
if 'logado' not in st.session_state or not st.session_state.logado:
    st.title("Login - Painel de Notas Fiscais")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            fazer_login(email, senha)
else:
    if 'df' not in st.session_state:
        st.session_state.df = carregar_dados()

    if 'ultimo_salvamento' not in st.session_state:
        st.session_state.ultimo_salvamento = None
    if 'alteracoes_pendentes' not in st.session_state:
        st.session_state.alteracoes_pendentes = False

    df = st.session_state.df

    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)

        st.write(f"**Bem-vindo, {st.session_state.get('nome_colaborador', 'Colaborador')}!**")
        st.title("💼 Menu Financeiro")

        menu = st.radio(
            "📌 Navegação",
            ["📋 Visualização de NFs", "💰 Gestão de Juros", "📊 Dashboards Financeiros", "⚙️ Configurações"]
        )

        st.divider()
        st.subheader("📊 Resumo Rápido")

        if not df.empty:
            total_nfs = len(df)
            total_valor = df['V_TOTAL_NF'].sum()
            nfs_pendentes = len(df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])])
            total_juros = df['VALOR_JUROS'].sum()
            total_frete = df['VALOR_FRETE'].sum()

            st.markdown(f"**Total de NFs:** **{total_nfs}**")
            st.markdown(f"**Valor Total:** **R$ {total_valor:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown(f"**Pendentes:** **{nfs_pendentes}**")
            st.markdown(f"**Finalizadas:** **{total_nfs - nfs_pendentes}**")
            st.markdown(f"**Juros:** **R$ {total_juros:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown(f"**Fretes:** **R$ {total_frete:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
        else:
            st.info("Nenhum dado disponível")

        st.divider()
        if st.button("Logout"):
            st.session_state.logado = False
            st.rerun()

        st.caption("Sistema Financeiro Completo v1.0")

    # Cabeçalhos por menu
    headers = {
        "📋 Visualização de NFs": ("📋 VISUALIZAÇÃO DE NOTAS FISCAIS", "Gerenciamento e acompanhamento financeiro de NFs"),
        "💰 Gestão de Juros": ("💰 GESTÃO DE JUROS E MULTAS", "Calcule e gerencie juros para notas em atraso"),
        "📊 Dashboards Financeiros": ("📊 DASHBOARDS FINANCEIROS COMPLETOS", "Análise estratégica de custos e eficiências"),
        "⚙️ Configurações": ("⚙️ CONFIGURAÇÕES DO SISTEMA", "Parâmetros e manutenção de dados"),
    }
    titulo, subtitulo = headers.get(menu)
    st.markdown(f"""
        <div class='header-container'>
            <h1>{titulo}</h1>
            <p>{subtitulo}</p>
        </div>
    """, unsafe_allow_html=True)

    if menu == "📋 Visualização de NFs":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("💾 Salvar Tudo", use_container_width=True):
                if salvar_dados(df):
                    st.session_state.ultimo_salvamento = datetime.datetime.now()
                    st.session_state.alteracoes_pendentes = False
                    st.success("Dados salvos com sucesso!")
                    time.sleep(1)
                    st.rerun()
        with col2:
            if st.button("🔄 Recarregar", use_container_width=True):
                st.session_state.df = carregar_dados()
                st.rerun()
        with col4:
            if st.session_state.ultimo_salvamento:
                st.info(f"Último save: {st.session_state.ultimo_salvamento.strftime('%H:%M:%S')}")
            elif st.session_state.alteracoes_pendentes:
                st.warning("Alterações não salvas")

        if not df.empty:
            st.markdown("---")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("📊 Total de NFs", len(df))
            c2.metric("💰 Valor NFs", f"R$ {df['V_TOTAL_NF'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c3.metric("⏳ Pendentes", len(df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])]))
            c4.metric("✅ Finalizadas", len(df[df['STATUS'] == 'FINALIZADO']))
            c5.metric("💸 Juros", f"R$ {df['VALOR_JUROS'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c6.metric("🚚 Fretes", f"R$ {df['VALOR_FRETE'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            st.markdown("---")
            st.subheader("📋 Detalhes das Notas Fiscais")

            status_options = ["EM ANDAMENTO", "FINALIZADO", "NF PROBLEMA"]
            problema_options = ["N/A", "SEM PEDIDO", "VALOR INCORRETO", "OUTRO"]

            df_display = df.copy()

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
                    "DIAS_VENCIMENTO": st.column_config.NumberColumn("Dias Vencimento", disabled=True),
                    "STATUS": st.column_config.SelectboxColumn("Status", options=status_options),
                    "CONDICAO_PROBLEMA": st.column_config.SelectboxColumn("Problema", options=problema_options),
                    "REGISTRO_ADICIONAL": "Obs.",
                    "VALOR_JUROS": st.column_config.NumberColumn("Juros (R$)", format="%.2f"),
                    "VALOR_FRETE": st.column_config.NumberColumn("Frete (R$)", format="%.2f"),
                    "DOC_NF": st.column_config.LinkColumn("DOC NF", display_text="📥"),
                    "RECEBEDOR": "Recebedor",
                },
                column_order=[
                    "DATA", "FORNECEDOR", "NF", "ORDEM_COMPRA", "V_TOTAL_NF", "VENCIMENTO", "DIAS_VENCIMENTO",
                    "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC_NF", "RECEBEDOR"
                ],
                hide_index=True
            )

            # Se houve alteração, salva automaticamente de forma segura
            if not edited_df.equals(df_display):
                st.session_state.alteracoes_pendentes = True

                # Normaliza tipos antes de salvar
                edited_df["DATA"] = _to_datetime(edited_df["DATA"])
                edited_df["VENCIMENTO"] = _to_datetime(edited_df["VENCIMENTO"])
                for c in ["V_TOTAL_NF", "VALOR_JUROS", "VALOR_FRETE"]:
                    edited_df[c] = pd.to_numeric(edited_df[c], errors="coerce").fillna(0.0)
                # Recalcula dias
                ref = pd.Timestamp.today().normalize()
                edited_df["DIAS_VENCIMENTO"] = (edited_df["VENCIMENTO"] - ref).dt.days.fillna(0).astype(int)

                st.session_state.df = edited_df.copy()

                if salvar_dados(st.session_state.df):
                    st.session_state.ultimo_salvamento = datetime.datetime.now()
                    st.session_state.alteracoes_pendentes = False
                    st.success("Alterações salvas com sucesso!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("📝 Nenhuma nota fiscal registrada no sistema. As notas cadastradas no Painel do Almoxarifado aparecerão aqui.")

    elif menu == "💰 Gestão de Juros":
        st.header("💰 Gestão de Juros e Multas")

        if not df.empty:
            nfs_com_problema = df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])]
            if not nfs_com_problema.empty:
                st.subheader("Notas com Possibilidade de Juros")

                for idx, row in nfs_com_problema.iterrows():
                    valor_nf_str = f"R$ {row['V_TOTAL_NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    title = f"NF {row['NF']} - {row['FORNECEDOR']} - {valor_nf_str}"
                    with st.expander(title):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            venc = row['VENCIMENTO'].strftime('%d/%m/%Y') if pd.notna(row['VENCIMENTO']) else 'N/A'
                            st.info(f"**Vencimento:** {venc}")
                            default_atraso = int(max(0, -int(row.get('DIAS_VENCIMENTO', 0))))
                            dias_atraso = st.number_input("Dias em Atraso", min_value=0, value=default_atraso, key=f"dias_{idx}")

                        with col2:
                            st.info(f"**Valor Original:** {valor_nf_str}")
                            taxa_juros = st.number_input("Taxa de Juros (%)", min_value=0.0, max_value=100.0, value=1.0, step=0.1, key=f"taxa_{idx}")

                        with col3:
                            valor_juros = (row['V_TOTAL_NF'] * (taxa_juros / 100.0)) * dias_atraso
                            st.metric("Valor de Juros", f"R$ {valor_juros:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            if st.button("Aplicar Juros", key=f"apply_{idx}"):
                                df.at[idx, 'VALOR_JUROS'] = float(valor_juros)
                                st.session_state.alteracoes_pendentes = True
                                st.success("Juros aplicados com sucesso!")
                                time.sleep(1)
                                st.rerun()

                st.subheader("📈 Resumo de Juros Aplicados")
                if "DATA" in df.columns:
                    base = df.copy()
                    base["DATA"] = _to_datetime(base["DATA"])
                    juros_por_mes = base.groupby(base['DATA'].dt.to_period('M'))['VALOR_JUROS'].sum().reset_index()
                    juros_por_mes['DATA'] = juros_por_mes['DATA'].dt.to_timestamp()

                    if not juros_por_mes.empty:
                        fig_juros = px.bar(
                            juros_por_mes, x='DATA', y='VALOR_JUROS',
                            title='Evolução dos Juros Mensais',
                            labels={'VALOR_JUROS': 'Valor de Juros (R$)', 'DATA': 'Mês'}
                        )
                        st.plotly_chart(fig_juros, use_container_width=True)

                juros_por_fornecedor = df.groupby('FORNECEDOR')['VALOR_JUROS'].sum().nlargest(10).reset_index()
                if not juros_por_fornecedor.empty:
                    fig_fornecedor = px.pie(
                        juros_por_fornecedor, values='VALOR_JUROS', names='FORNECEDOR',
                        title='Distribuição de Juros por Fornecedor (Top 10)'
                    )
                    st.plotly_chart(fig_fornecedor, use_container_width=True)
            else:
                st.info("Nenhuma nota fiscal para calcular juros.")
        else:
            st.info("Nenhum dado disponível.")

    elif menu == "📊 Dashboards Financeiros":
        st.header("📊 Dashboards Financeiros Completos")

        if not df.empty:
            df["DATA"] = _to_datetime(df["DATA"])

            df['MES_ANO'] = df['DATA'].dt.to_period('M')
            df['ANO'] = df['DATA'].dt.year
            df['MES'] = df['DATA'].dt.month

            dados_mensais = df.groupby('MES_ANO').agg({
                'V_TOTAL_NF': 'sum',
                'VALOR_FRETE': 'sum',
                'VALOR_JUROS': 'sum',
                'NF': 'count'
            }).reset_index()
            dados_mensais['MES_ANO'] = dados_mensais['MES_ANO'].dt.to_timestamp()

            anos = sorted(df['ANO'].dropna().unique())
            if len(anos) >= 2:
                st.subheader("📅 Comparativo Anual")

                comparativo_anual = df.groupby('ANO').agg({
                    'V_TOTAL_NF': 'sum',
                    'VALOR_FRETE': 'sum',
                    'VALOR_JUROS': 'sum',
                    'NF': 'count'
                }).reset_index()

                fig_comparativo = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Valor Total', 'Custo com Fretes', 'Juros Pagos', 'Quantidade de NFs')
                )

                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['V_TOTAL_NF'], name='Valor Total'), row=1, col=1)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_FRETE'], name='Fretes'), row=1, col=2)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_JUROS'], name='Juros'), row=2, col=1)
                fig_comparativo.add_trace(go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['NF'], name='Qtd NFs'), row=2, col=2)

                fig_comparativo.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_comparativo, use_container_width=True)

            st.subheader("🚚 Análise de Fretes")
            col1, col2 = st.columns(2)

            with col1:
                if 'CONDICAO_FRETE' in df.columns:
                    frete_tipo = df.groupby('CONDICAO_FRETE')['VALOR_FRETE'].sum().reset_index()
                    if not frete_tipo.empty:
                        fig_frete_tipo = px.pie(
                            frete_tipo, values='VALOR_FRETE', names='CONDICAO_FRETE',
                            title='Distribuição por Tipo de Frete'
                        )
                        st.plotly_chart(fig_frete_tipo, use_container_width=True)

            with col2:
                if not dados_mensais.empty:
                    fig_frete_evolucao = px.line(
                        dados_mensais, x='MES_ANO', y='VALOR_FRETE',
                        title='Evolução Mensal dos Gastos com Frete',
                        labels={'VALOR_FRETE': 'Valor do Frete (R$)', 'MES_ANO': 'Mês'}
                    )
                    st.plotly_chart(fig_frete_evolucao, use_container_width=True)

            st.subheader("💸 Análise de Custos")
            custos_totais = pd.DataFrame({
                'Tipo': ['Valor NFs', 'Fretes', 'Juros'],
                'Valor': [df['V_TOTAL_NF'].sum(), df['VALOR_FRETE'].sum(), df['VALOR_JUROS'].sum()]
            })

            fig_custos = px.bar(custos_totais, x='Tipo', y='Valor', title='Distribuição Total de Custos', color='Tipo')
            st.plotly_chart(fig_custos, use_container_width=True)

            st.subheader("📈 Métricas de Eficiência")
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)

            with col_met1:
                custo_total = df['V_TOTAL_NF'].sum() + df['VALOR_FRETE'].sum() + df['VALOR_JUROS'].sum()
                st.metric("Custo Total", f"R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            with col_met2:
                vt = df['V_TOTAL_NF'].sum()
                perc_frete = (df['VALOR_FRETE'].sum() / vt * 100) if vt > 0 else 0
                st.metric("% Frete/NF", f"{perc_frete:.2f}%")

            with col_met3:
                vt = df['V_TOTAL_NF'].sum()
                perc_juros = (df['VALOR_JUROS'].sum() / vt * 100) if vt > 0 else 0
                st.metric("% Juros/NF", f"{perc_juros:.2f}%")

            with col_met4:
                nfs_com_juros = int((df['VALOR_JUROS'] > 0).sum())
                st.metric("NFs com Juros", f"{nfs_com_juros}")
        else:
            st.info("Nenhum dado disponível.")

    elif menu == "⚙️ Configurações":
        st.header("⚙️ Configurações do Sistema")

        st.subheader("Manutenção de Dados")
        if st.button("🔄 Forçar Recarregamento de Dados"):
            st.session_state.df = carregar_dados()
            st.success("Cache limpo e dados recarregados com sucesso!")
            st.rerun()

        st.subheader("Exportação de Dados")
        if not df.empty:
            csv = df.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="dados_financeiros_completos.csv",
                mime="text/csv"
            )
        else:
            st.info("Não há dados para exportar.")

        st.subheader("Limpeza de Dados")
        st.warning("Aviso: Esta ação não pode ser desfeita e irá limpar o histórico de notas fiscais.")
        if st.button("🧹 Limpar Dados do Almoxarifado"):
            df_vazio = pd.DataFrame(columns=df.columns)
            if salvar_dados(df_vazio):
                st.session_state.df = df_vazio
                st.success("Dados do almoxarifado limpos com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao tentar limpar os dados.")

        st.subheader("Log de Atividades")
        if 'log_messages' in st.session_state:
            log_text = "\n".join(st.session_state['log_messages'])
            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)
        else:
            st.info("Nenhum log disponível.")
