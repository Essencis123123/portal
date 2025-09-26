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
import numpy as np

# =============================================================================
# CONFIGURAÇÃO INICIAL E CSS SAP FIORI MODERNO
# =============================================================================

st.set_page_config(
    page_title="Gestão de Notas Fiscais - SAP Fiori Style", 
    layout="wide", 
    page_icon="📋",
    initial_sidebar_state="expanded"
)

# CSS Moderno SAP Fiori para Fiscal
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações globais */
    * {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        font-size: 1rem;
    }
    
    /* Header Principal SAP Fiori */
    .fiscal-header {
        background: linear-gradient(135deg, #0055a5 0%, #1C4D86 50%, #003d7a 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 85, 165, 0.3);
        text-align: center;
        color: white;
        position: relative;
        overflow: hidden;
        animation: slideInDown 0.8s ease-out;
    }
    
    .fiscal-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        transform: rotate(45deg);
        animation: shine 3s infinite;
    }
    
    .fiscal-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        animation: fadeInUp 1s ease-out 0.3s both;
    }
    
    .fiscal-header p {
        font-size: 1.1rem;
        margin: 10px 0 0 0;
        opacity: 0.9;
        animation: fadeInUp 1s ease-out 0.6s both;
    }
    
    /* Cards de Funcionalidades SAP Fiori */
    .feature-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        position: relative;
        overflow: hidden;
        border: 1px solid #e8eaed;
        animation: fadeInScale 0.6s ease-out;
        border-left: 4px solid #0055a5;
    }
    
    .feature-card:hover {
        transform: translateY(-5px) scale(1.01);
        box-shadow: 0 12px 28px rgba(0, 85, 165, 0.15);
        border-color: #0055a5;
    }
    
    .feature-card h3 {
        color: #1C4D86;
        font-weight: 600;
        margin-bottom: 0.5rem;
        font-size: 1.2rem;
    }
    
    .feature-card p {
        color: #666;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: 0;
    }
    
    /* Sidebar Moderno */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1C4D86 0%, #0f2e4d 100%);
        border-right: 3px solid #0055a5;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .user-info {
        background: rgba(255,255,255,0.1);
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    /* Botões SAP Fiori */
    .stButton button {
        background: linear-gradient(135deg, #0055a5 0%, #1C4D86 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 85, 165, 0.3);
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 85, 165, 0.4);
        background: linear-gradient(135deg, #0066c7 0%, #2158a0 100%);
    }
    
    /* Tabelas Modernas */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        animation: fadeInUp 0.8s ease-out;
    }
    
    /* Métricas Cards */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 4px solid #0055a5;
        animation: fadeInScale 0.8s ease-out;
        transition: all 0.3s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    
    /* Inputs Modernos */
    .stSelectbox, .stDateInput, .stTextInput, .stTextArea {
        border-radius: 8px;
    }
    
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 2px solid #e8eaed;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #0055a5;
        box-shadow: 0 0 0 3px rgba(0, 85, 165, 0.1);
    }
    
    /* Animações */
    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInScale {
        from {
            opacity: 0;
            transform: scale(0.9);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    @keyframes shine {
        0% {
            transform: translateX(-100%) rotate(45deg);
        }
        100% {
            transform: translateX(100%) rotate(45deg);
        }
    }
    
    /* Status badges */
    .status-pago {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-pendente {
        background: linear-gradient(135deg, #FF9800, #F57C00);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-vencido {
        background: linear-gradient(135deg, #f44336, #d32f2f);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
    }
    
    /* Loading spinner */
    .loading-fiscal {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #0055a5;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DADOS E FUNÇÕES AUXILIARES
# =============================================================================

# Usuários demo para fiscal
FISCAL_USERS = {
    "admin@essencis.com": {
        "password": "admin123",
        "name": "Administrador",
        "role": "admin"
    },
    "financeiro@essencis.com": {
        "password": "financeiro123",
        "name": "Financeiro",
        "role": "finance"
    }
}

def load_logo(url):
    """Carrega logo da URL"""
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def authenticate_fiscal_user(email, password):
    """Autentica usuário do módulo fiscal"""
    if email in FISCAL_USERS and FISCAL_USERS[email]["password"] == password:
        return FISCAL_USERS[email]
    return None

def generate_sample_fiscal_data():
    """Gera dados de exemplo para demonstração"""
    np.random.seed(42)
    
    fornecedores = [
        "Fornecedor A Ltda", "Empresa B S.A.", "Comércio C Eireli",
        "Indústria D S.A.", "Serviços E Ltda", "Distribuidora F",
        "Tecnologia G", "Soluções H", "Produtos I", "Materiais J"
    ]
    
    data = []
    for i in range(100):
        data.append({
            'NF_NUMERO': f"NF-{1000 + i}",
            'FORNECEDOR': np.random.choice(fornecedores),
            'DATA': pd.Timestamp.now() - pd.Timedelta(days=np.random.randint(0, 365)),
            'VENCIMENTO': pd.Timestamp.now() + pd.Timedelta(days=np.random.randint(-30, 90)),
            'VALOR': np.random.uniform(500, 50000),
            'STATUS': np.random.choice(['Pago', 'Pendente', 'Vencido'], p=[0.6, 0.3, 0.1]),
            'CATEGORIA': np.random.choice(['Material', 'Serviço', 'Equipamento', 'Software']),
            'OBSERVACOES': f"Observação da NF {1000 + i}"
        })
    
    df = pd.DataFrame(data)
    df['DIAS_VENCIMENTO'] = (df['VENCIMENTO'] - pd.Timestamp.now()).dt.days
    
    return df

def show_fiscal_login():
    """Mostra tela de login do módulo fiscal"""
    st.markdown("""
    <div class="fiscal-header">
        <h1>📋 Gestão de Notas Fiscais</h1>
        <p>Sistema Moderno com Design SAP Fiori</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 20px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1); animation: fadeInScale 1s ease-out;">
            <h2 style="text-align: center; color: #1C4D86; margin-bottom: 2rem;">
                🔐 Acesso ao Módulo Fiscal
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("fiscal_login_form", clear_on_submit=False):
            email = st.text_input("📧 E-mail", placeholder="seu@email.com")
            password = st.text_input("🔒 Senha", type="password", placeholder="Sua senha")
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                login_btn = st.form_submit_button("🚀 Acessar Módulo", use_container_width=True)
            
            if login_btn:
                if email and password:
                    user = authenticate_fiscal_user(email, password)
                    if user:
                        st.session_state.fiscal_authenticated = True
                        st.session_state.fiscal_user = user
                        st.success(f"✅ Bem-vindo(a) ao módulo fiscal, {user['name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")

def show_fiscal_dashboard(df):
    """Mostra dashboard fiscal com métricas"""
    col1, col2, col3, col4 = st.columns(4)
    
    total_nfs = len(df)
    valor_total = df['VALOR'].sum()
    nfs_pendentes = len(df[df['STATUS'] == 'Pendente'])
    nfs_vencidas = len(df[df['STATUS'] == 'Vencido'])
    
    with col1:
        st.metric("📋 Total de NFs", total_nfs, f"↗️ {total_nfs}")
    with col2:
        st.metric("💰 Valor Total", f"R$ {valor_total:,.2f}", "↗️ 15%")
    with col3:
        st.metric("⏳ Pendentes", nfs_pendentes, f"{'↗️' if nfs_pendentes > 0 else '✅'} {nfs_pendentes}")
    with col4:
        st.metric("🚨 Vencidas", nfs_vencidas, f"{'🔴' if nfs_vencidas > 0 else '✅'} {nfs_vencidas}")

def format_status(status):
    """Formata status com cores"""
    if status == 'Pago':
        return f'<span class="status-pago">✅ {status}</span>'
    elif status == 'Pendente':
        return f'<span class="status-pendente">⏳ {status}</span>'
    else:
        return f'<span class="status-vencido">🚨 {status}</span>'

def show_fiscal_analytics(df):
    """Mostra análises fiscais com gráficos"""
    st.markdown("### 📊 Análises Fiscais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de status
        status_counts = df['STATUS'].value_counts()
        fig1 = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="📋 Distribuição por Status",
            color_discrete_map={
                'Pago': '#4CAF50',
                'Pendente': '#FF9800', 
                'Vencido': '#f44336'
            }
        )
        fig1.update_layout(
            title_font_size=16,
            title_font_color='#1C4D86',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Gráfico de valores por fornecedor
        fornecedor_valores = df.groupby('FORNECEDOR')['VALOR'].sum().sort_values(ascending=False).head(5)
        fig2 = px.bar(
            x=fornecedor_valores.values,
            y=fornecedor_valores.index,
            orientation='h',
            title="💰 Top 5 Fornecedores por Valor",
            color=fornecedor_valores.values,
            color_continuous_scale='Blues'
        )
        fig2.update_layout(
            title_font_size=16,
            title_font_color='#1C4D86',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)

# =============================================================================
# INTERFACE PRINCIPAL DO MÓDULO FISCAL
# =============================================================================

def main():
    """Função principal do módulo fiscal"""
    
    # Inicialização do estado
    if "fiscal_authenticated" not in st.session_state:
        st.session_state.fiscal_authenticated = False
    if "fiscal_user" not in st.session_state:
        st.session_state.fiscal_user = None
    if "fiscal_df" not in st.session_state:
        st.session_state.fiscal_df = generate_sample_fiscal_data()
    
    # Logo
    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)
    
    # Se não autenticado, mostra login
    if not st.session_state.fiscal_authenticated:
        show_fiscal_login()
        return
    
    # Interface principal após login
    user = st.session_state.fiscal_user
    df = st.session_state.fiscal_df
    
    # Sidebar
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        
        st.markdown(f"""
        <div class="user-info">
            <h3>👋 Olá, {user['name']}!</h3>
            <p>🎯 Módulo: Fiscal</p>
            <p>🕐 {datetime.datetime.now().strftime('%H:%M - %d/%m/%Y')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menu de navegação
        menu_option = st.radio(
            "🧭 Navegação Fiscal",
            ["📋 Lançamentos", "💰 Gestão de Juros", "📊 Analytics", "⚙️ Configurações"],
            index=0
        )
        
        st.markdown("---")
        
        # Filtros
        st.subheader("🎯 Filtros")
        status_filter = st.multiselect(
            "Status", 
            options=df['STATUS'].unique(), 
            default=df['STATUS'].unique()
        )
        
        fornecedor_filter = st.selectbox(
            "Fornecedor",
            options=['Todos'] + list(df['FORNECEDOR'].unique())
        )
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.fiscal_authenticated = False
            st.session_state.fiscal_user = None
            st.rerun()
    
    # Header principal
    st.markdown(f"""
    <div class="fiscal-header">
        <h1>📋 Gestão de Notas Fiscais</h1>
        <p>Módulo Fiscal com Tecnologia SAP Fiori - {user['name']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Aplicar filtros
    df_filtered = df[df['STATUS'].isin(status_filter)]
    if fornecedor_filter != 'Todos':
        df_filtered = df_filtered[df_filtered['FORNECEDOR'] == fornecedor_filter]
    
    # Conteúdo baseado no menu
    if menu_option == "📋 Lançamentos":
        show_fiscal_dashboard(df_filtered)
        
        st.markdown("---")
        st.markdown("### 📄 Notas Fiscais")
        
        # Preparar dados para exibição
        df_display = df_filtered.copy()
        df_display['STATUS_FORMATTED'] = df_display['STATUS'].apply(format_status)
        df_display['VALOR_FORMATTED'] = df_display['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
        df_display['DATA_FORMATTED'] = df_display['DATA'].dt.strftime('%d/%m/%Y')
        df_display['VENCIMENTO_FORMATTED'] = df_display['VENCIMENTO'].dt.strftime('%d/%m/%Y')
        
        # Mostrar tabela
        cols_to_show = ['NF_NUMERO', 'FORNECEDOR', 'DATA_FORMATTED', 'VENCIMENTO_FORMATTED', 'VALOR_FORMATTED', 'STATUS', 'CATEGORIA']
        st.dataframe(
            df_display[cols_to_show].rename(columns={
                'NF_NUMERO': 'Número NF',
                'FORNECEDOR': 'Fornecedor', 
                'DATA_FORMATTED': 'Data',
                'VENCIMENTO_FORMATTED': 'Vencimento',
                'VALOR_FORMATTED': 'Valor',
                'STATUS': 'Status',
                'CATEGORIA': 'Categoria'
            }),
            use_container_width=True,
            height=400
        )
        
    elif menu_option == "💰 Gestão de Juros":
        st.markdown("### 💰 Gestão de Juros e Multas")
        
        # Cards de funcionalidades
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>🧮 Calculadora de Juros</h3>
                <p>Calcule juros e multas automaticamente para notas em atraso com base nas regras configuradas.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Exemplo de cálculo
            st.subheader("Configurações de Juros")
            taxa_juros = st.number_input("Taxa de Juros (%)", value=2.0, step=0.1)
            multa = st.number_input("Multa (%)", value=10.0, step=0.1)
            
            if st.button("💹 Calcular Juros", use_container_width=True):
                nfs_vencidas = df_filtered[df_filtered['STATUS'] == 'Vencido']
                if not nfs_vencidas.empty:
                    st.success(f"✅ Calculado juros para {len(nfs_vencidas)} notas vencidas!")
                else:
                    st.info("ℹ️ Nenhuma nota vencida encontrada.")
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>📊 Relatório de Atrasos</h3>
                <p>Visualize relatórios detalhados de notas em atraso e projeções de pagamento.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Gráfico de vencimentos
            vencimentos = df_filtered.groupby('STATUS')['VALOR'].sum()
            fig = px.bar(
                x=vencimentos.index,
                y=vencimentos.values,
                title="💰 Valores por Status",
                color=vencimentos.values,
                color_continuous_scale='Reds'
            )
            fig.update_layout(
                title_font_size=16,
                title_font_color='#1C4D86',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
    elif menu_option == "📊 Analytics":
        show_fiscal_analytics(df_filtered)
        
        # Timeline de vencimentos
        st.markdown("### ⏰ Timeline de Vencimentos")
        
        # Preparar dados para timeline
        df_timeline = df_filtered.copy()
        df_timeline['MES_VENCIMENTO'] = df_timeline['VENCIMENTO'].dt.to_period('M').astype(str)
        timeline_data = df_timeline.groupby(['MES_VENCIMENTO', 'STATUS']).agg({
            'VALOR': 'sum',
            'NF_NUMERO': 'count'
        }).reset_index()
        
        fig_timeline = px.bar(
            timeline_data,
            x='MES_VENCIMENTO',
            y='VALOR',
            color='STATUS',
            title="📅 Vencimientos por Mês",
            color_discrete_map={
                'Pago': '#4CAF50',
                'Pendente': '#FF9800',
                'Vencido': '#f44336'
            }
        )
        fig_timeline.update_layout(
            title_font_size=18,
            title_font_color='#1C4D86',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
    elif menu_option == "⚙️ Configurações":
        st.markdown("### ⚙️ Configurações do Módulo Fiscal")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>🎨 Personalização</h3>
                <p>Configure as preferências visuais e funcionais do módulo fiscal.</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.selectbox("🎨 Tema", ["SAP Fiori (Padrão)", "Claro", "Escuro"])
            st.selectbox("📧 Notificações", ["Ativas", "Apenas Urgentes", "Desativadas"])
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>💾 Dados</h3>
                <p>Gerencie importação, exportação e backup dos dados fiscais.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📤 Exportar Dados", use_container_width=True):
                st.success("✅ Dados exportados com sucesso!")
            
            if st.button("🔄 Sincronizar", use_container_width=True):
                with st.spinner("Sincronizando..."):
                    time.sleep(2)
                st.success("✅ Sincronização concluída!")

if __name__ == "__main__":
    main()