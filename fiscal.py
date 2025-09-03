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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Financeiro - Almoxarifado", layout="wide", page_icon="💼")

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
        st.error("Erro ao carregar a imagem do logo")
        return None

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

def carregar_dados():
    """Carrega os dados do arquivo CSV ou cria um novo se não existir"""
    arquivo_csv = "dados_pedidos.csv"
    
    if os.path.exists(arquivo_csv):
        try:
            df = pd.read_csv(arquivo_csv)
            # Converter colunas de data
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)
            if 'VENCIMENTO' in df.columns:
                df['VENCIMENTO'] = pd.to_datetime(df['VENCIMENTO'], errors='coerce', dayfirst=True)
            else:
                df['VENCIMENTO'] = pd.NaT
            
            # Garantir que colunas importantes existam
            colunas_necessarias = {
                "STATUS": "EM ANDAMENTO",
                "CONDICAO_PROBLEMA": "N/A",
                "REGISTRO_ADICIONAL": "",
                "VALOR_JUROS": 0.0,
                "DIAS_ATRASO": 0,
                "VALOR_FRETE": 0.0,
                "DOC NF": ""
            }
            
            for col, default_val in colunas_necessarias.items():
                if col not in df.columns:
                    df[col] = default_val
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {e}")
            return criar_dataframe_vazio()
    else:
        return criar_dataframe_vazio()

def criar_dataframe_vazio():
    """Cria um DataFrame vazio com a estrutura correta"""
    return pd.DataFrame(columns=[
        "DATA", "FORNECEDOR", "NF", "PEDIDO", "VOLUME", "V. TOTAL NF",
        "VENCIMENTO", "DOC NF", "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL",
        "VALOR_JUROS", "DIAS_ATRASO", "VALOR_FRETE"
    ])

def salvar_dados(df):
    """Salva o DataFrame no arquivo CSV"""
    try:
        df_to_save = df.copy()
        df_to_save['DATA'] = df_to_save['DATA'].dt.strftime('%d/%m/%Y')
        if 'VENCIMENTO' in df_to_save.columns:
            df_to_save['VENCIMENTO'] = df_to_save['VENCIMENTO'].dt.strftime('%d/%m/%Y')
            
        df_to_save.to_csv("dados_pedidos.csv", index=False, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
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
        time.sleep(1) # Dá tempo para o usuário ver a mensagem antes de recarregar
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
            [
                "📋 Visualização de NFs",
                "💰 Gestão de Juros",
                "📊 Dashboards Financeiros",
                "⚙️ Configurações"
            ]
        )
        
        st.divider()
        st.subheader("📊 Resumo Rápido")
        
        if not df.empty:
            total_nfs = len(df)
            total_valor = df['V. TOTAL NF'].sum() if 'V. TOTAL NF' in df.columns else 0
            nfs_pendentes = len(df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])]) if 'STATUS' in df.columns else 0
            total_juros = df['VALOR_JUROS'].sum() if 'VALOR_JUROS' in df.columns else 0
            total_frete = df['VALOR_FRETE'].sum() if 'VALOR_FRETE' in df.columns else 0
            
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

    # Adiciona o cabeçalho temático dependendo da opção do menu
    if menu == "📋 Visualização de NFs":
        st.markdown("""
            <div class='header-container'>
                <h1>📋 VISUALIZAÇÃO DE NOTAS FISCAIS</h1>
                <p>Gerenciamento e acompanhamento financeiro de NFs</p>
            </div>
        """, unsafe_allow_html=True)
    elif menu == "💰 Gestão de Juros":
        st.markdown("""
            <div class='header-container'>
                <h1>💰 GESTÃO DE JUROS E MULTAS</h1>
                <p>Calcule e gerencie juros para notas em atraso</p>
            </div>
        """, unsafe_allow_html=True)
    elif menu == "📊 Dashboards Financeiros":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 DASHBOARDS FINANCEIROS COMPLETOS</h1>
                <p>Análise estratégica de custos e eficiências</p>
            </div>
        """, unsafe_allow_html=True)
    elif menu == "⚙️ Configurações":
        st.markdown("""
            <div class='header-container'>
                <h1>⚙️ CONFIGURAÇÕES DO SISTEMA</h1>
                <p>Parâmetros e manutenção de dados</p>
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
        with col3:
            # Botão "Nova NF" removido para focar na visualização de notas já existentes.
            pass
        with col4:
            if st.session_state.ultimo_salvamento:
                st.info(f"Último save: {st.session_state.ultimo_salvamento.strftime('%H:%M:%S')}")
            elif st.session_state.alteracoes_pendentes:
                st.warning("Alterações não salvas")

        if not df.empty:
            st.markdown("---")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("📊 Total de NFs", len(df))
            with col2:
                st.metric("💰 Valor NFs", f"R$ {df['V. TOTAL NF'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            with col3:
                st.metric("⏳ Pendentes", len(df[df['STATUS'].isin(['EM ANDAMENTO', 'NF PROBLEMA'])]))
            with col4:
                st.metric("✅ Finalizadas", len(df[df['STATUS'] == 'FINALIZADO']))
            with col5:
                st.metric("💸 Juros", f"R$ {df['VALOR_JUROS'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            with col6:
                st.metric("🚚 Fretes", f"R$ {df['VALOR_FRETE'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            # --- Visualização da Tabela de Notas Fiscais ---
            st.markdown("---")
            st.subheader("📋 Detalhes das Notas Fiscais")

            def formatar_vencimento(venc):
                try:
                    if pd.isna(venc):
                        return "N/A"
                    venc_date = pd.to_datetime(venc).date()
                    dias = (venc_date - datetime.date.today()).days
                    if dias < 0:
                        return f"🔴 {venc_date.strftime('%d/%m/%Y')}"
                    elif dias <= 10:
                        return f"🟡 {venc_date.strftime('%d/%m/%Y')}"
                    else:
                        return f"🟢 {venc_date.strftime('%d/%m/%Y')}"
                except:
                    return "N/A"

            # Opções para os Selectboxes
            status_options = ["EM ANDAMENTO", "FINALIZADO", "NF PROBLEMA"]
            problema_options = ["N/A", "SEM PEDIDO", "VALOR INCORRETO", "OUTRO"]
            
            df_display = df.copy()

            edited_df = st.data_editor(
                df_display[[
                    "DATA", "FORNECEDOR", "NF", "PEDIDO", "V. TOTAL NF", "VENCIMENTO",
                    "STATUS", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "VALOR_JUROS", "VALOR_FRETE", "DOC NF"
                ]],
                use_container_width=True,
                column_config={
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
                    "FORNECEDOR": "Fornecedor",
                    "NF": "N° NF",
                    "PEDIDO": "N° Pedido",
                    "V. TOTAL NF": st.column_config.NumberColumn("V. Total NF (R$)", format="%.2f", disabled=True),
                    "VENCIMENTO": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                    "STATUS": st.column_config.SelectboxColumn("Status", options=status_options),
                    "CONDICAO_PROBLEMA": st.column_config.SelectboxColumn("Problema", options=problema_options),
                    "REGISTRO_ADICIONAL": "Obs.",
                    "VALOR_JUROS": st.column_config.NumberColumn("Juros (R$)", format="%.2f", disabled=True),
                    "VALOR_FRETE": st.column_config.NumberColumn("Frete (R$)", format="%.2f", disabled=True),
                    "DOC NF": st.column_config.LinkColumn("DOC NF", display_text="📥")
                }
            )

            # Lógica de atualização e salvamento
            if not edited_df.equals(df_display):
                st.session_state.df.update(edited_df)
                st.session_state.alteracoes_pendentes = True
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
            nfs_com_problema = df[df['STATUS'].isin(['NF PROBLEMA', 'EM ANDAMENTO'])]
            
            if not nfs_com_problema.empty:
                st.subheader("Notas com Possibilidade de Juros")
                
                for idx, row in nfs_com_problema.iterrows():
                    with st.expander(f"NF {row['NF']} - {row['FORNECEDOR']} - R$ {row['V. TOTAL NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.info(f"**Vencimento:** {row['VENCIMENTO'].strftime('%d/%m/%Y') if pd.notna(row['VENCIMENTO']) else 'N/A'}")
                            dias_atraso = st.number_input(
                                "Dias em Atraso",
                                min_value=0,
                                value=int(row['DIAS_ATRASO']),
                                key=f"dias_{idx}"
                            )
                        
                        with col2:
                            st.info(f"**Valor Original:** R$ {row['V. TOTAL NF']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            taxa_juros = st.number_input(
                                "Taxa de Juros (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=1.0,
                                step=0.1,
                                key=f"taxa_{idx}"
                            )
                        
                        with col3:
                            valor_juros = (row['V. TOTAL NF'] * taxa_juros / 100) * dias_atraso
                            st.metric("Valor de Juros", f"R$ {valor_juros:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        
                        with col4:
                            if st.button("Aplicar Juros", key=f"apply_{idx}"):
                                df.at[idx, 'VALOR_JUROS'] = valor_juros
                                df.at[idx, 'DIAS_ATRASO'] = dias_atraso
                                st.session_state.alteracoes_pendentes = True
                                st.success("Juros aplicados com sucesso!")
                                time.sleep(1)
                                st.rerun()
                
                st.subheader("📈 Resumo de Juros Aplicados")
                juros_por_mes = df.groupby(df['DATA'].dt.to_period('M'))['VALOR_JUROS'].sum().reset_index()
                juros_por_mes['DATA'] = juros_por_mes['DATA'].dt.to_timestamp()
                
                if not juros_por_mes.empty:
                    fig_juros = px.bar(
                        juros_por_mes,
                        x='DATA',
                        y='VALOR_JUROS',
                        title='Evolução dos Juros Mensais',
                        labels={'VALOR_JUROS': 'Valor de Juros (R$)', 'DATA': 'Mês'}
                    )
                    st.plotly_chart(fig_juros, use_container_width=True)
                
                juros_por_fornecedor = df.groupby('FORNECEDOR')['VALOR_JUROS'].sum().nlargest(10).reset_index()
                if not juros_por_fornecedor.empty:
                    fig_fornecedor = px.pie(
                        juros_por_fornecedor,
                        values='VALOR_JUROS',
                        names='FORNECEDOR',
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
            df['MES_ANO'] = df['DATA'].dt.to_period('M')
            df['ANO'] = df['DATA'].dt.year
            df['MES'] = df['DATA'].dt.month
            
            dados_mensais = df.groupby('MES_ANO').agg({
                'V. TOTAL NF': 'sum',
                'VALOR_FRETE': 'sum',
                'VALOR_JUROS': 'sum',
                'NF': 'count'
            }).reset_index()
            dados_mensais['MES_ANO'] = dados_mensais['MES_ANO'].dt.to_timestamp()
            
            anos = sorted(df['ANO'].unique())
            if len(anos) >= 2:
                st.subheader("📅 Comparativo Anual")
                
                comparativo_anual = df.groupby('ANO').agg({
                    'V. TOTAL NF': 'sum',
                    'VALOR_FRETE': 'sum',
                    'VALOR_JUROS': 'sum',
                    'NF': 'count'
                }).reset_index()
                
                fig_comparativo = make_subplots(rows=2, cols=2, subplot_titles=('Valor Total', 'Custo com Fretes', 'Juros Pagos', 'Quantidade de NFs'))
                
                fig_comparativo.add_trace(
                    go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['V. TOTAL NF'], name='Valor Total'),
                    row=1, col=1
                )
                
                fig_comparativo.add_trace(
                    go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_FRETE'], name='Fretes'),
                    row=1, col=2
                )
                
                fig_comparativo.add_trace(
                    go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['VALOR_JUROS'], name='Juros'),
                    row=2, col=1
                )
                
                fig_comparativo.add_trace(
                    go.Bar(x=comparativo_anual['ANO'], y=comparativo_anual['NF'], name='Qtd NFs'),
                    row=2, col=2
                )
                
                fig_comparativo.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_comparativo, use_container_width=True)
            
            st.subheader("🚚 Análise de Fretes")
            col1, col2 = st.columns(2)
            
            with col1:
                if 'CONDICAO_FRETE' in df.columns:
                    frete_tipo = df.groupby('CONDICAO_FRETE')['VALOR_FRETE'].sum().reset_index()
                    if not frete_tipo.empty:
                        fig_frete_tipo = px.pie(
                            frete_tipo,
                            values='VALOR_FRETE',
                            names='CONDICAO_FRETE',
                            title='Distribuição por Tipo de Frete'
                        )
                        st.plotly_chart(fig_frete_tipo, use_container_width=True)
            
            with col2:
                if not dados_mensais.empty:
                    fig_frete_evolucao = px.line(
                        dados_mensais,
                        x='MES_ANO',
                        y='VALOR_FRETE',
                        title='Evolução Mensal dos Gastos com Frete',
                        labels={'VALOR_FRETE': 'Valor do Frete (R$)', 'MES_ANO': 'Mês'}
                    )
                    st.plotly_chart(fig_frete_evolucao, use_container_width=True)
            
            st.subheader("💸 Análise de Custos")
            custos_totais = pd.DataFrame({
                'Tipo': ['Valor NFs', 'Fretes', 'Juros'],
                'Valor': [df['V. TOTAL NF'].sum(), df['VALOR_FRETE'].sum(), df['VALOR_JUROS'].sum()]
            })
            
            fig_custos = px.bar(
                custos_totais,
                x='Tipo',
                y='Valor',
                title='Distribuição Total de Custos',
                color='Tipo'
            )
            st.plotly_chart(fig_custos, use_container_width=True)
            
            st.subheader("📈 Métricas de Eficiência")
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            
            with col_met1:
                custo_total = df['V. TOTAL NF'].sum() + df['VALOR_FRETE'].sum() + df['VALOR_JUROS'].sum()
                st.metric("Custo Total", f"R$ {custo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            with col_met2:
                perc_frete = (df['VALOR_FRETE'].sum() / df['V. TOTAL NF'].sum() * 100) if df['V. TOTAL NF'].sum() > 0 else 0
                st.metric("% Frete/NF", f"{perc_frete:.2f}%")
            
            with col_met3:
                perc_juros = (df['VALOR_JUROS'].sum() / df['V. TOTAL NF'].sum() * 100) if df['V. TOTAL NF'].sum() > 0 else 0
                st.metric("% Juros/NF", f"{perc_juros:.2f}%")
            
            with col_met4:
                nfs_com_juros = len(df[df['VALOR_JUROS'] > 0])
                st.metric("NFs com Juros", f"{nfs_com_juros}")
        
        else:
            st.info("Nenhuma nota fiscal para calcular juros.")

    elif menu == "⚙️ Configurações":
        st.header("⚙️ Configurações do Sistema")
        
        st.subheader("Parâmetros de Juros")
        taxa_padrao = st.number_input("Taxa de Juros Padrão (% ao dia)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        dias_carencia = st.number_input("Dias de Carência para Juros", min_value=0, value=5)
        
        st.subheader("Exportação de Dados")
        csv = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name="dados_financeiros_completos.csv",
            mime="text/csv"
        )
        
        st.subheader("Limpeza de Dados")
        if st.button("🧹 Limpar Dados de Teste"):
            st.warning("Esta ação não pode ser desfeita!")
            if st.button("Confirmar Limpeza"):
                df_limpo = df[df['V. TOTAL NF'] > 0]
                st.session_state.df = df_limpo
                salvar_dados(df_limpo)
                st.success("Dados limpos com sucesso!")
                st.rerun()
        
        st.subheader("Log de Atividades")
        if 'log_messages' in st.session_state:
            log_text = "\n".join(st.session_state['log_messages'])
            st.text_area("Log de Atividades", value=log_text, height=300, disabled=True)
        else:
            st.info("Nenhum log disponível.")
