import streamlit as st
import pandas as pd
import time
import datetime
import requests
from PIL import Image
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =============================================================================
# CONFIGURAÇÃO INICIAL E CSS SAP FIORI
# =============================================================================

st.set_page_config(
    page_title="Sistema de Gestão 360 - Essencis",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# CSS Moderno com Animações SAP Fiori
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
    
    /* Header Principal com Gradiente */
    .main-header {
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
    
    .main-header::before {
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
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        animation: fadeInUp 1s ease-out 0.3s both;
    }
    
    .main-header p {
        font-size: 1.2rem;
        margin: 10px 0 0 0;
        opacity: 0.9;
        animation: fadeInUp 1s ease-out 0.6s both;
    }
    
    /* Cards de Módulos com Animações */
    .module-card {
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
    }
    
    .module-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 35px rgba(0, 85, 165, 0.2);
        border-color: #0055a5;
    }
    
    .module-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 85, 165, 0.1), transparent);
        transition: left 0.5s;
    }
    
    .module-card:hover::before {
        left: 100%;
    }
    
    .card-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
        text-align: center;
        animation: bounce 2s infinite;
    }
    
    .card-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1C4D86;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .card-description {
        color: #666;
        font-size: 0.95rem;
        text-align: center;
        line-height: 1.5;
    }
    
    /* Sidebar Moderna */
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
    
    /* Botões Modernos */
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
            transform: scale(0.8);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {
            transform: translateY(0);
        }
        40% {
            transform: translateY(-10px);
        }
        60% {
            transform: translateY(-5px);
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
    
    /* Cards Grid Responsivo */
    .modules-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    /* Métricas Dashboard */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 4px solid #0055a5;
        animation: fadeInScale 0.8s ease-out;
    }
    
    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 8px;
        padding: 8px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85rem;
    }
    
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    
    /* Loading Spinner */
    .loading-spinner {
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
# FUNÇÕES AUXILIARES
# =============================================================================

def load_logo(url):
    """Carrega logo da URL"""
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def animate_card_entry():
    """Adiciona delay para animação dos cards"""
    time.sleep(0.1)

def show_loading():
    """Mostra spinner de carregamento"""
    return st.markdown('<div class="loading-spinner"></div>', unsafe_allow_html=True)

# =============================================================================
# SISTEMA DE AUTENTICAÇÃO
# =============================================================================

# Usuários demo (em produção usar banco de dados)
USERS_DB = {
    "admin@essencis.com": {
        "password": "admin123",
        "name": "Administrador",
        "role": "admin",
        "modules": ["all"]
    },
    "comprador@essencis.com": {
        "password": "comprador123", 
        "name": "Comprador",
        "role": "buyer",
        "modules": ["compras", "fornecedores", "consulta"]
    },
    "financeiro@essencis.com": {
        "password": "financeiro123",
        "name": "Financeiro", 
        "role": "finance",
        "modules": ["fiscal", "reembolso", "contratos"]
    }
}

def authenticate_user(email, password):
    """Autentica usuário"""
    if email in USERS_DB and USERS_DB[email]["password"] == password:
        return USERS_DB[email]
    return None

def show_login_form():
    """Mostra formulário de login animado"""
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Sistema de Gestão 360</h1>
        <p>Versão Ultra Moderna com Design SAP Fiori</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 20px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1); animation: fadeInScale 1s ease-out;">
            <h2 style="text-align: center; color: #1C4D86; margin-bottom: 2rem;">
                🔐 Acesso ao Sistema
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("📧 E-mail", placeholder="seu@email.com")
            password = st.text_input("🔒 Senha", type="password", placeholder="Sua senha")
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                login_btn = st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True)
            
            if login_btn:
                if email and password:
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"✅ Bem-vindo(a), {user['name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")
        
        # Info de usuários demo
        with st.expander("ℹ️ Usuários de Demonstração"):
            st.info("""
            **Administrador:** admin@essencis.com / admin123
            
            **Comprador:** comprador@essencis.com / comprador123
            
            **Financeiro:** financeiro@essencis.com / financeiro123
            """)

# =============================================================================
# MÓDULOS DO SISTEMA
# =============================================================================

SYSTEM_MODULES = {
    "compras": {
        "title": "Gestão de Compras",
        "icon": "🛒",
        "description": "Sistema completo de compras com aprovações e workflows automatizados",
        "file": "compras.py",
        "category": "Operacional"
    },
    "consulta": {
        "title": "Consulta de Compras", 
        "icon": "🔍",
        "description": "Consulta rápida de pedidos e status para usuários com acesso limitado",
        "file": "consulta.py",
        "category": "Consulta"
    },
    "fornecedores": {
        "title": "Carteira de Fornecedores",
        "icon": "🏪", 
        "description": "Gestão completa da carteira de fornecedores e qualificações",
        "file": "painel.py",
        "category": "Operacional"
    },
    "estoque": {
        "title": "Gestão de Estoque",
        "icon": "📦",
        "description": "Controle de estoque com movimentações e relatórios detalhados", 
        "file": "estoque_nf.py",
        "category": "Operacional"
    },
    "fiscal": {
        "title": "Gestão de Notas Fiscais",
        "icon": "📋",
        "description": "Controle de notas fiscais com status e gestão de pagamentos",
        "file": "fiscal.py", 
        "category": "Financeiro"
    },
    "reembolso": {
        "title": "Sistema de Reembolsos",
        "icon": "💰",
        "description": "Gestão de reembolsos com aprovações e sistema de pagamentos",
        "file": "reembolso.py",
        "category": "Financeiro"
    },
    "contratos": {
        "title": "Gestão de Contratos",
        "icon": "📑", 
        "description": "Controle de contratos com renovações automáticas e alertas",
        "file": "contratos.py",
        "category": "Jurídico"
    },
    "dashboard": {
        "title": "Dashboard Executivo",
        "icon": "📊",
        "description": "Painéis executivos com métricas e indicadores em tempo real",
        "file": "dashboard.py", 
        "category": "Gerencial"
    }
}

def show_module_card(module_key, module_info, delay=0):
    """Mostra card animado de módulo"""
    time.sleep(delay * 0.1)  # Delay para animação escalonada
    
    card_html = f"""
    <div class="module-card" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: '{module_key}'}}, '*')">
        <div class="card-icon">{module_info['icon']}</div>
        <div class="card-title">{module_info['title']}</div>
        <div class="card-description">{module_info['description']}</div>
        <div style="margin-top: 1rem; text-align: center;">
            <span style="background: linear-gradient(135deg, #0055a5, #1C4D86); 
                         color: white; padding: 0.3rem 1rem; border-radius: 20px; 
                         font-size: 0.8rem; font-weight: 500;">
                {module_info['category']}
            </span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def show_dashboard_metrics():
    """Mostra métricas do dashboard principal"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Pedidos Ativos", "42", "↗️ +8")
    with col2:
        st.metric("💰 Valor Mensal", "R$ 125.500", "↗️ +12%")
    with col3:
        st.metric("🏪 Fornecedores", "86", "↗️ +3")
    with col4:
        st.metric("⏱️ Tempo Médio", "4.2 dias", "↘️ -0.8")
    
    # Gráfico de exemplo
    st.markdown("### 📈 Evolução Mensal de Compras")
    
    # Dados fictícios para demonstração
    months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
    values = [85000, 92000, 78000, 125000, 110000, 125500]
    
    fig = px.line(x=months, y=values, title="Volume de Compras (R$)")
    fig.update_traces(line_color='#0055a5', line_width=3)
    fig.update_layout(
        title_font_size=20,
        title_font_color='#1C4D86',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# INTERFACE PRINCIPAL 
# =============================================================================

def main():
    """Função principal da aplicação"""
    
    # Inicialização do estado da sessão
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    
    # Logo URL
    logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
    logo_img = load_logo(logo_url)
    
    # Se não autenticado, mostra login
    if not st.session_state.authenticated:
        show_login_form()
        return
    
    # Interface principal após login
    user = st.session_state.user
    
    # Sidebar com informações do usuário
    with st.sidebar:
        if logo_img:
            st.image(logo_img, use_container_width=True)
        
        st.markdown(f"""
        <div class="user-info">
            <h3>👋 Olá, {user['name']}!</h3>
            <p>🎯 Perfil: {user['role'].title()}</p>
            <p>🕐 {datetime.datetime.now().strftime('%H:%M - %d/%m/%Y')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menu de navegação
        menu_option = st.radio(
            "🧭 Navegação",
            ["🏠 Hub Principal", "📊 Dashboard", "⚙️ Configurações"],
            index=0
        )
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # Conteúdo principal
    if menu_option == "🏠 Hub Principal":
        show_main_hub(user)
    elif menu_option == "📊 Dashboard":
        show_main_dashboard()
    elif menu_option == "⚙️ Configurações":
        show_settings()

def show_main_hub(user):
    """Mostra o hub principal com os módulos"""
    
    # Header principal
    st.markdown(f"""
    <div class="main-header">
        <h1>🏢 Hub de Módulos Empresariais</h1>
        <p>Selecione um módulo para começar, {user['name']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtros de módulos por categoria
    categories = list(set([module['category'] for module in SYSTEM_MODULES.values()]))
    selected_category = st.selectbox("🎯 Filtrar por Categoria", ["Todos"] + categories)
    
    # Grid de módulos
    st.markdown("### 🎯 Módulos Disponíveis")
    
    # Filtrar módulos baseado nas permissões do usuário
    available_modules = {}
    for key, module in SYSTEM_MODULES.items():
        if user['modules'] == ['all'] or key in user['modules']:
            if selected_category == "Todos" or module['category'] == selected_category:
                available_modules[key] = module
    
    # Mostrar cards em grid
    cols = st.columns(3)
    for i, (key, module) in enumerate(available_modules.items()):
        with cols[i % 3]:
            show_module_card(key, module, delay=i)
            
            # Botão para acessar módulo
            if st.button(f"🚀 Acessar {module['title']}", key=f"btn_{key}", use_container_width=True):
                st.info(f"🔄 Carregando módulo {module['title']}...")
                show_loading()
                # Aqui seria o redirecionamento para o módulo específico
                time.sleep(1)
                st.success(f"✅ Módulo {module['title']} carregado com sucesso!")
    
    # Se não há módulos disponíveis
    if not available_modules:
        st.warning("⚠️ Nenhum módulo disponível para seu perfil na categoria selecionada.")

def show_main_dashboard():
    """Mostra dashboard principal"""
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dashboard Executivo</h1>
        <p>Visão geral dos indicadores do sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    show_dashboard_metrics()

def show_settings():
    """Mostra configurações do sistema"""
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ Configurações do Sistema</h1>
        <p>Personalize sua experiência</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("🚧 Configurações em desenvolvimento...")
    
    # Preferências do usuário
    st.subheader("👤 Preferências do Usuário")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("🎨 Tema", ["Claro", "Escuro", "Auto"])
        st.selectbox("🌍 Idioma", ["Português", "English", "Español"])
    
    with col2:
        st.selectbox("📧 Notificações", ["Ativas", "Apenas Urgentes", "Desativadas"])
        st.selectbox("⏰ Fuso Horário", ["GMT-3 (Brasília)", "GMT-2", "GMT+0"])

if __name__ == "__main__":
    main()