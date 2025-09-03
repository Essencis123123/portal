import streamlit as st
import pandas as pd
import datetime
import os
import time
import plotly.express as px
from pandas.errors import EmptyDataError
import requests
from PIL import Image
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Painel do Solicitante", layout="wide", page_icon="📝")

# CSS para personalizar o menu lateral e garantir que todo o texto seja branco
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #1C4D86;
    }
    
    /* Regras para garantir que TODO o texto no sidebar seja branco */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }

    /* Estilos para os campos de filtro e botões - texto preto */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stButton button {
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

logo_url = "http://nfeviasolo.com.br/portal2/imagens/Logo%20Essencis%20MG%20-%20branca.png"
logo_img = load_logo(logo_url)

# --- Funções de Carregamento de Dados ---

@st.cache_data
def carregar_dados_pedidos():
    """Carrega os dados de pedidos, garantindo que as colunas de data e status existam."""
    arquivo_csv = "dados_pedidos.csv"
    if os.path.exists(arquivo_csv):
        try:
            df = pd.read_csv(arquivo_csv, dtype={'REQUISICAO': str, 'SOLICITANTE': str, 'DEPARTAMENTO': str, 'STATUS_PEDIDO': str, 'VALOR_ITEM': float})
            
            for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            
            if 'STATUS_PEDIDO' not in df.columns:
                df['STATUS_PEDIDO'] = 'PENDENTE'
            if 'VALOR_ITEM' not in df.columns:
                df['VALOR_ITEM'] = 0.0
            
            return df
        except (FileNotFoundError, EmptyDataError):
            return pd.DataFrame(columns=[
                "DATA", "SOLICITANTE", "DEPARTAMENTO", "REQUISICAO", "MATERIAL",
                "STATUS_PEDIDO", "DATA_APROVACAO", "DATA_ENTREGA", "ORDEM_COMPRA", "VALOR_ITEM"
            ])
    return pd.DataFrame(columns=[
        "DATA", "SOLICITANTE", "DEPARTAMENTO", "REQUISICAO", "MATERIAL",
        "STATUS_PEDIDO", "DATA_APROVACAO", "DATA_ENTREGA", "ORDEM_COMPRA", "VALOR_ITEM"
    ])

# --- INICIALIZAÇÃO E LAYOUT DA PÁGINA ---
df_pedidos = carregar_dados_pedidos()
if not df_pedidos['DATA'].isnull().all():
    df_pedidos['MES'] = df_pedidos['DATA'].dt.month
    df_pedidos['ANO'] = df_pedidos['DATA'].dt.year

with st.sidebar:
    if logo_img:
        st.image(logo_img, use_container_width=True)
    
    st.title("🔎 Painel do Solicitante")
    st.divider()
    
    menu_option = st.sidebar.radio(
        "Selecione a opção:",
        ["📋 Acompanhar Pedidos", "📊 Dashboard de Custos"],
        index=0
    )
    
    st.divider()
    
    if menu_option == "📋 Acompanhar Pedidos":
        st.subheader("Filtros de Pedidos")
        # Filtros de mês e ano para o acompanhamento
        if 'MES' in df_pedidos.columns and 'ANO' in df_pedidos.columns and not df_pedidos.empty:
            meses_disponiveis = sorted(df_pedidos['MES'].dropna().unique())
            anos_disponiveis = sorted(df_pedidos['ANO'].dropna().unique(), reverse=True)
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                           7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            filtro_mes_pedidos = st.selectbox("Selecione o Mês:", ['Todos'] + meses_disponiveis, format_func=lambda x: meses_nomes.get(x) if isinstance(x, int) else x)
            filtro_ano_pedidos = st.selectbox("Selecione o Ano:", ['Todos'] + anos_disponiveis)
        else:
            filtro_mes_pedidos = 'Todos'
            filtro_ano_pedidos = 'Todos'
        
        # Filtros de solicitante, departamento e status
        solicitantes_disponiveis = ['Todos'] + sorted(df_pedidos['SOLICITANTE'].dropna().unique().tolist())
        departamentos_disponiveis = ['Todos'] + sorted(df_pedidos['DEPARTAMENTO'].dropna().unique().tolist())
        status_disponiveis = df_pedidos['STATUS_PEDIDO'].dropna().unique().tolist()
        
        default_status_options = ['PENDENTE', 'ENTREGUE']
        filtered_defaults = [status for status in default_status_options if status in status_disponiveis]

        filtro_solicitante = st.selectbox(
            "Filtrar por Solicitante:",
            options=solicitantes_disponiveis,
            index=0
        )
        filtro_departamento = st.selectbox(
            "Filtrar por Departamento:",
            options=departamentos_disponiveis,
            index=0
        )
        filtro_status = st.multiselect(
            "Filtrar por Status:",
            options=['Todos'] + sorted(status_disponiveis),
            default=filtered_defaults
        )
    
    elif menu_option == "📊 Dashboard de Custos":
        st.subheader("Filtros do Dashboard")
        if 'MES' in df_pedidos.columns and 'ANO' in df_pedidos.columns and not df_pedidos.empty:
            meses_disponiveis = sorted(df_pedidos['MES'].dropna().unique())
            anos_disponiveis = sorted(df_pedidos['ANO'].dropna().unique(), reverse=True)
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
                           7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            
            filtro_mes_dash = st.selectbox("Selecione o Mês:", meses_disponiveis, format_func=lambda x: meses_nomes.get(x), index=len(meses_disponiveis)-1)
            filtro_ano_dash = st.selectbox("Selecione o Ano:", anos_disponiveis)
        else:
            st.info("Nenhum dado com data disponível para filtrar.")


st.markdown("""
    <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: white; text-align: center; margin: 0;'>📝 PAINEL DE ACOMPANHAMENTO DE REQUISIÇÕES</h1>
        <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Visualize o status das requisições de compra da empresa</p>
    </div>
""", unsafe_allow_html=True)

if df_pedidos.empty:
    st.info("Nenhum pedido registrado no sistema.")
    st.stop()

if menu_option == "📋 Acompanhar Pedidos":
    df_filtrado = df_pedidos.copy()

    # Aplicação dos filtros
    if filtro_mes_pedidos != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['MES'] == filtro_mes_pedidos]
    if filtro_ano_pedidos != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['ANO'] == filtro_ano_pedidos]

    if filtro_solicitante != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['SOLICITANTE'] == filtro_solicitante]

    if filtro_departamento != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['DEPARTAMENTO'] == filtro_departamento]

    if filtro_status and 'Todos' not in filtro_status:
        df_filtrado = df_filtrado[df_filtrado['STATUS_PEDIDO'].isin(filtro_status)]
    
    if df_filtrado.empty:
        st.warning("Nenhum pedido encontrado com os filtros aplicados.")
        st.stop()

    # --- Análise e Métricas ---
    col1, col2, col3 = st.columns(3)
    with col1:
        total_pedidos = len(df_filtrado)
        st.metric("Total de Pedidos", total_pedidos)
    with col2:
        pedidos_pendentes = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'PENDENTE'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    with col3:
        pedidos_entregues = len(df_filtrado[df_filtrado['STATUS_PEDIDO'] == 'ENTREGUE'])
        st.metric("Pedidos Entregues", pedidos_entregues)

    st.markdown("---")

    # --- Gráficos de Análise Visual ---
    st.subheader("Análise de Status de Pedidos")
    status_counts = df_filtrado['STATUS_PEDIDO'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    fig_status = px.pie(
        status_counts,
        values='Quantidade',
        names='Status',
        title='Distribuição do Status dos Pedidos',
        color_discrete_map={'PENDENTE': '#ffcc00', 'ENTREGUE': '#009933', 'EM ANDAMENTO': '#3366ff'}
    )
    st.plotly_chart(fig_status, use_container_width=True)
    
    st.markdown("---")

    # --- Tabela de Visualização Detalhada ---
    st.subheader("Detalhes dos Pedidos")
    
    df_tabela = df_filtrado.copy()
    
    def formatar_status(status):
        if status == 'ENTREGUE':
            return '🟢 ENTREGUE'
        elif status == 'PENDENTE':
            return '⚪ PENDENTE'
        else:
            return '🟡 EM ANDAMENTO'

    df_tabela['STATUS'] = df_tabela['STATUS_PEDIDO'].apply(formatar_status)
    df_tabela['DATA REQUISIÇÃO'] = df_tabela['DATA'].dt.strftime('%d/%m/%Y')
    df_tabela['DATA ENTREGA'] = df_tabela['DATA_ENTREGA'].dt.strftime('%d/%m/%Y').replace('NaT', 'N/A')
    
    st.dataframe(
        df_tabela[['DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'MATERIAL', 'QUANTIDADE', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'DATA ENTREGA']],
        use_container_width=True,
        hide_index=True,
        column_order=['DATA REQUISIÇÃO', 'REQUISICAO', 'SOLICITANTE', 'DEPARTAMENTO', 'MATERIAL', 'QUANTIDADE', 'STATUS', 'ORDEM_COMPRA', 'FORNECEDOR', 'DATA ENTREGA'],
        column_config={
            "DATA REQUISIÇÃO": st.column_config.DateColumn("Data Requisição"),
            "REQUISICAO": "N° Requisição",
            "SOLICITANTE": "Solicitante",
            "DEPARTAMENTO": "Departamento",
            "MATERIAL": "Material",
            "QUANTIDADE": "Quantidade",
            "STATUS": "Status",
            "ORDEM_COMPRA": "N° Ordem de Compra",
            "FORNECEDOR": "Fornecedor",
            "DATA ENTREGA": "Data Entrega"
        }
    )
    
    # Botão de download para o CSV
    csv_pedidos = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exportar Tabela para CSV",
        data=csv_pedidos,
        file_name=f"pedidos_filtrados_{datetime.date.today()}.csv",
        mime="text/csv",
        help="Clique para baixar os dados da tabela filtrada."
    )
    
    st.markdown("---")
    st.caption("📝 Painel de Acompanhamento | Última atualização: "
               f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
               f"Total de pedidos: {len(df_pedidos)}")

elif menu_option == "📊 Dashboard de Custos":
    st.markdown("""
        <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
            <h1 style='color: white; text-align: center; margin: 0;'>📊 DASHBOARD DE CUSTOS</h1>
            <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Análise estratégica dos custos por departamento</p>
        </div>
    """, unsafe_allow_html=True)
    
    if 'MES' in df_pedidos.columns and 'ANO' in df_pedidos.columns and not df_pedidos.empty:
        df_filtrado_dash = df_pedidos[
            (df_pedidos['MES'] == filtro_mes_dash) & 
            (df_pedidos['ANO'] == filtro_ano_dash) &
            (df_pedidos['DEPARTAMENTO'].notna()) & 
            (df_pedidos['VALOR_ITEM'].notna()) &
            (df_pedidos['VALOR_ITEM'] > 0)
        ]
        
        if not df_filtrado_dash.empty:
            st.subheader(f"Custo Total por Departamento ({meses_nomes[filtro_mes_dash]}/{filtro_ano_dash})")
            
            custo_por_departamento = df_filtrado_dash.groupby('DEPARTAMENTO')['VALOR_ITEM'].sum().reset_index()
            custo_por_departamento.columns = ['Departamento', 'Custo Total']
            
            fig_custo = px.bar(
                custo_por_departamento,
                x='Custo Total',
                y='Departamento',
                orientation='h',
                title='Custo Total de Pedidos por Departamento',
                labels={'Custo Total': 'Custo Total (R$)', 'Departamento': 'Departamento'},
                text_auto='.2s'
            )
            st.plotly_chart(fig_custo, use_container_width=True)
            
            # Botão de download para o CSV
            csv = custo_por_departamento.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar dados para CSV",
                data=csv,
                file_name=f"custos_por_departamento_{filtro_mes_dash}_{filtro_ano_dash}.csv",
                mime="text/csv",
                help="Clique para baixar os dados do gráfico acima."
            )
        else:
            st.info("Nenhum dado de custo disponível para o período selecionado.")
    else:
        st.info("Não foi possível carregar os dados para o dashboard.")
