import streamlit as st
import pandas as pd
import datetime
import requests
from PIL import Image
from io import BytesIO

# Configuração da página com layout wide e ícone
st.set_page_config(
    page_title="Sistema de Gestão 360 - Essencis", 
    layout="wide", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# SAP Fiori inspired CSS styling
st.markdown("""
    <style>
    /* Reset and base styling */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
        font-size: 1rem;
        line-height: 1.5;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        margin: 0;
        padding: 0;
    }

    /* SAP Fiori Color Palette */
    :root {
        --sap-blue: #0854a0;
        --sap-light-blue: #427cac;
        --sap-dark-blue: #1c4d86;
        --sap-accent: #00a4ef;
        --sap-success: #107e3e;
        --sap-warning: #e26100;
        --sap-error: #b00;
        --sap-neutral: #6a6d70;
        --sap-background: #fafafa;
        --sap-white: #ffffff;
        --sap-light-gray: #f2f2f2;
        --sap-border: #e5e5e5;
        --shadow-level-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        --shadow-level-2: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
        --shadow-level-3: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Modern Header */
    .modern-header {
        background: linear-gradient(135deg, var(--sap-blue) 0%, var(--sap-dark-blue) 100%);
        padding: 1.5rem 2rem;
        border-radius: 0;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: var(--shadow-level-2);
        color: var(--sap-white);
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1400px;
        margin: 0 auto;
    }

    .header-title {
        font-size: 1.8rem;
        font-weight: 300;
        margin: 0;
        color: var(--sap-white);
    }

    .header-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0.25rem 0 0 0;
        font-weight: 300;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        color: var(--sap-white);
    }

    .user-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--sap-accent);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 1.2rem;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sap-dark-blue) 0%, var(--sap-blue) 100%);
        border-right: 1px solid var(--sap-border);
    }

    [data-testid="stSidebar"] * {
        color: var(--sap-white) !important;
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p {
        color: var(--sap-white) !important;
    }

    /* Module Cards Grid */
    .modules-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
        padding: 0 1rem;
    }

    .module-card {
        background: var(--sap-white);
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: var(--shadow-level-1);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid var(--sap-border);
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .module-card:hover {
        box-shadow: var(--shadow-level-3);
        transform: translateY(-4px);
        border-color: var(--sap-accent);
    }

    .module-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--sap-accent) 0%, var(--sap-blue) 100%);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }

    .module-card:hover::before {
        transform: scaleX(1);
    }

    .module-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        display: block;
        color: var(--sap-blue);
    }

    .module-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--sap-dark-blue);
        margin-bottom: 0.5rem;
    }

    .module-description {
        color: var(--sap-neutral);
        font-size: 0.9rem;
        line-height: 1.4;
        margin-bottom: 1rem;
    }

    .module-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        background: var(--sap-light-gray);
        color: var(--sap-neutral);
    }

    .module-status.active {
        background: var(--sap-success);
        color: var(--sap-white);
    }

    /* Modern Buttons */
    .stButton button {
        background: linear-gradient(135deg, var(--sap-blue) 0%, var(--sap-accent) 100%);
        color: var(--sap-white) !important;
        border: none;
        border-radius: 4px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-level-1);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stButton button:hover {
        box-shadow: var(--shadow-level-2);
        transform: translateY(-1px);
    }

    .stButton button:active {
        transform: translateY(0);
    }

    /* Footer */
    .modern-footer {
        background: var(--sap-white);
        border-top: 1px solid var(--sap-border);
        padding: 1.5rem 2rem;
        margin: 3rem -1rem -1rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
        color: var(--sap-neutral);
    }

    .footer-info {
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .system-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--sap-success);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    /* Loading States */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 2px solid var(--sap-light-gray);
        border-top: 2px solid var(--sap-blue);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .modules-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
            padding: 0 0.5rem;
        }
        
        .modern-header {
            padding: 1rem;
            margin: -1rem -0.5rem 1rem -0.5rem;
        }
        
        .header-content {
            flex-direction: column;
            text-align: center;
            gap: 1rem;
        }
    }

    /* Breadcrumbs */
    .breadcrumbs {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: var(--sap-neutral);
    }

    .breadcrumb-item {
        color: var(--sap-neutral);
        text-decoration: none;
    }

    .breadcrumb-item:hover {
        color: var(--sap-blue);
    }

    .breadcrumb-separator {
        color: var(--sap-border);
    }
    </style>
""", unsafe_allow_html=True)

# Logo loading function
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def render_header():
    """Render modern header with user information"""
    st.markdown("""
        <div class="modern-header">
            <div class="header-content">
                <div>
                    <h1 class="header-title">Sistema de Gestão 360</h1>
                    <p class="header-subtitle">Plataforma Integrada de Gestão Empresarial</p>
                </div>
                <div class="user-info">
                    <div class="user-avatar">ES</div>
                    <div>
                        <div style="font-weight: 500;">Essencis User</div>
                        <div style="font-size: 0.8rem; opacity: 0.8;">Administrador</div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_module_grid():
    """Render responsive grid of available modules"""
    modules = [
        {
            "icon": "🛒",
            "title": "Sistema de Compras",
            "description": "Gestão completa de requisições, pedidos e fornecedores com controle de aprovações.",
            "url": "compras.py",
            "status": "active"
        },
        {
            "icon": "💰",
            "title": "Gestão de Reembolsos",
            "description": "Solicitação e acompanhamento de reembolsos com fluxo de aprovação automatizado.",
            "url": "reembolso.py",
            "status": "active"
        },
        {
            "icon": "📊",
            "title": "Painel Fiscal",
            "description": "Controle financeiro e gestão de notas fiscais com dashboards analíticos avançados.",
            "url": "fiscal.py",
            "status": "active"
        },
        {
            "icon": "🔍",
            "title": "Consultas Avançadas",
            "description": "Sistema de consulta e relatórios com filtros inteligentes e exportação de dados.",
            "url": "consulta.py",
            "status": "active"
        },
        {
            "icon": "📝",
            "title": "Alteração Fiscal",
            "description": "Edição e manutenção de informações fiscais com controle de auditoria.",
            "url": "alteracao_fiscal.py",
            "status": "active"
        },
        {
            "icon": "🏭",
            "title": "Controle de Estoque",
            "description": "Gestão de almoxarifado e controle de notas fiscais de entrada e saída.",
            "url": "estoque_nf.py",
            "status": "active"
        },
        {
            "icon": "📋",
            "title": "Painel de Serviços",
            "description": "Gestão de fornecedores e acompanhamento de prestação de serviços.",
            "url": "painel.py",
            "status": "active"
        },
        {
            "icon": "⚙️",
            "title": "Configurações",
            "description": "Configurações do sistema, usuários e parâmetros de funcionamento.",
            "url": "#",
            "status": "maintenance"
        }
    ]

    # Create the grid
    st.markdown('<div class="modules-grid">', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for i, module in enumerate(modules):
        with cols[i % 3]:
            status_class = "active" if module["status"] == "active" else ""
            status_text = "Ativo" if module["status"] == "active" else "Manutenção"
            
            card_html = f"""
                <div class="module-card" onclick="window.open('{module["url"]}', '_self')">
                    <div class="module-icon">{module["icon"]}</div>
                    <div class="module-title">{module["title"]}</div>
                    <div class="module-description">{module["description"]}</div>
                    <div class="module-status {status_class}">{status_text}</div>
                </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_footer():
    """Render modern footer with system information"""
    now = datetime.datetime.now()
    st.markdown(f"""
        <div class="modern-footer">
            <div class="footer-info">
                <div>© 2024 Essencis - Sistema de Gestão 360</div>
                <div>Versão 2.0.0</div>
                <div>Última atualização: {now.strftime('%d/%m/%Y %H:%M')}</div>
            </div>
            <div class="system-status">
                <div class="status-indicator"></div>
                <div>Sistema Online</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    
    # Render components
    render_header()
    
    # Breadcrumbs
    st.markdown("""
        <div class="breadcrumbs">
            <span class="breadcrumb-item">🏠 Início</span>
            <span class="breadcrumb-separator">›</span>
            <span class="breadcrumb-item">Hub de Módulos</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Welcome section
    st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <h2 style="color: var(--sap-dark-blue); font-weight: 300; margin-bottom: 0.5rem;">
                Bem-vindo ao Sistema de Gestão 360
            </h2>
            <p style="color: var(--sap-neutral); font-size: 1.1rem;">
                Selecione um módulo abaixo para começar
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Module grid
    render_module_grid()
    
    # Sidebar with navigation
    with st.sidebar:
        # Logo space
        st.markdown("""
            <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏢</div>
                <div style="font-weight: 600; font-size: 1.1rem;">ESSENCIS</div>
                <div style="font-size: 0.8rem; opacity: 0.8;">Gestão 360</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🗂️ Navegação Rápida")
        
        quick_nav = st.selectbox(
            "Ir para módulo:",
            ["Selecione...", "💰 Reembolsos", "🛒 Compras", "📊 Fiscal", 
             "🔍 Consultas", "📝 Alterações", "🏭 Estoque", "📋 Serviços"],
            key="quick_nav"
        )
        
        if quick_nav != "Selecione...":
            nav_map = {
                "💰 Reembolsos": "reembolso.py",
                "🛒 Compras": "compras.py",
                "📊 Fiscal": "fiscal.py",
                "🔍 Consultas": "consulta.py",
                "📝 Alterações": "alteracao_fiscal.py",
                "🏭 Estoque": "estoque_nf.py",
                "📋 Serviços": "painel.py"
            }
            if st.button(f"Acessar {quick_nav}", use_container_width=True):
                st.markdown(f'<meta http-equiv="refresh" content="0;url={nav_map[quick_nav]}" />', 
                           unsafe_allow_html=True)
        
        st.markdown("---")
        
        # System info
        st.markdown("### 📊 Status do Sistema")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Módulos", "7", "✅")
        with col2:
            st.metric("Status", "Online", "🟢")
        
        st.markdown("### 🔧 Ações Rápidas")
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()
        
        if st.button("📋 Relatórios", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")
        
        st.markdown("---")
        st.markdown("""
            <div style="text-align: center; font-size: 0.8rem; opacity: 0.7;">
                <div>Sistema Integrado</div>
                <div>v2.0.0</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Footer
    render_footer()

if __name__ == "__main__":
    main()