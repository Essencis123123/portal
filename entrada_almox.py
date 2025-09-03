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

# Configuração da página com layout wide
st.set_page_config(page_title="Painel Almoxarifado", layout="wide", page_icon="🏭")

# CSS para personalizar o menu lateral
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #1C4D86;
    }
    [data-testid="stSidebar"] .stRadio > div {
        background-color: #1C4D86;
        color: white;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: white;
    }
    [data-testid="stSidebar"] .stMultiSelect label, 
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .stInfo {
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

# Função para carregar ou criar o banco de dados
@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv("dados_pedidos.csv")
        
        # Garantir que colunas de texto sejam lidas como string para evitar erros de tipo
        dtype_dict = {'FORNECEDOR': str, 'ORDEM_COMPRA': str, 'MATERIAL': str, 'RECEBEDOR': str,
                      'OBSERVAÇÃO': str, 'DOC NF': str, 'CONDICAO_FRETE': str}
        for col in dtype_dict:
            if col in df.columns:
                df[col] = df[col].astype(dtype_dict[col])

        # Converter colunas de data
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'VENCIMENTO']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
        
        # Garantir que colunas existam para o Almoxarifado e o Financeiro
        if 'NF' not in df.columns: df['NF'] = ''
        if 'STATUS_FINANCEIRO' not in df.columns: df['STATUS_FINANCEIRO'] = "N/A"
        if 'CONDICAO_PROBLEMA' not in df.columns: df['CONDICAO_PROBLEMA'] = "N/A"
        if 'REGISTRO_ADICIONAL' not in df.columns: df['REGISTRO_ADICIONAL'] = ""
        if 'V. TOTAL NF' not in df.columns: df['V. TOTAL NF'] = 0.0
        if 'OBSERVAÇÃO' not in df.columns: df['OBSERVAÇÃO'] = ""
        if 'VENCIMENTO' not in df.columns: df['VENCIMENTO'] = pd.NaT

        return df

    except (FileNotFoundError, EmptyDataError):
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO", "VOLUME",
            "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE", "OBSERVAÇÃO",
            "DOC NF", "VENCIMENTO", "STATUS_FINANCEIRO",
            "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL", "STATUS_PEDIDO", "DATA_ENTREGA",
            "REQUISICAO", "MATERIAL", "QUANTIDADE", "FILIAL", "DEPARTAMENTO", "SOLICITANTE",
            "ORDEM_COMPRA", "VALOR_ITEM", "DATA_APROVACAO", "TIPO_PEDIDO"
        ])

def salvar_dados(df):
    """Salva o DataFrame no arquivo CSV, lidando com datas nulas."""
    df_to_save = df.copy()
    for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'VENCIMENTO']:
        if col in df_to_save.columns:
            df_to_save[col] = df_to_save[col].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
            )
    df_to_save.to_csv("dados_pedidos.csv", index=False, encoding='utf-8')

# ---------------------------
# CONFIGURAÇÕES
# ---------------------------
status_financeiro_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]
problema_options = ["N/A", "REGISTRO CHAMADO", "CARTA CORRECAO", "AJUSTE NA ORDEM DE COMPRA", "RECUSA DE NOTA FISCAL"]
logo_url = "https://media.licdn.com/dms/image/v2/C560BAQHJFSN_XUibJw/company-logo_200_200/company-logo_200_200/0/1675703958506/essencismg_logo?e=2147483647&v=beta&t=ZNEo5jZJnySYCy2VbJdq1AMvUVreiPP0V3sK4Ku1nX0"
logo_img = load_logo(logo_url)

# --- Menu Lateral ---
with st.sidebar:
    if logo_img:
        st.image(logo_img, use_container_width=True)
    st.title("Menu de Navegação")
    menu_option = st.radio(
        "Selecione a opção:",
        ["📝 Registrar NF", "📊 Dashboard", "🔍 Consultar NFs", "⚙️ Configurações"],
        index=0
    )
    st.divider()
    st.info("Sistema de Controle de Notas Fiscais - Versão 1.0")

# --- Carregar dados (após a inicialização da página) ---
df = carregar_dados()

# ---------------------------
# INTERFACE PRINCIPAL BASEADA NA SELEÇÃO DO MENU
# ---------------------------
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
                data = st.date_input("Data*", datetime.date.today())
                fornecedor = st.text_input("Fornecedor*", placeholder="Nome do fornecedor...")
                nf = st.text_input("Número da NF*")
                
            with col2:
                recebedor = st.selectbox("Recebedor*", [
                    "ARLEY GONCALVES DOS SANTOS", "EVIANE DAS GRACAS DE ASSIS",
                    "ANDRE CASTRO DE SOUZA", "ISABELA CAROLINA DE PAURA SOARES",
                    "EMERSON ALMEIDA DE ARAUJO", "GABRIEL PEREIRA MARTINS",
                    "OUTROS"
                ])
                # --- CORREÇÃO AQUI: CAMPO PARA ORDEM DE COMPRA ---
                ordem_compra = st.text_input("N° Ordem de Compra*", help="Número da ordem de compra para vincular a nota")
                volume = st.number_input("Volume*", min_value=1, value=1)
                
            with col3:
                valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")
                condicao_frete = st.selectbox("Condição de Frete", ["CIF", "FOB"])
                valor_frete = st.text_input("Valor Frete (ex: 123,45)", value="0,00") if condicao_frete == "FOB" else "0,00"
            
            observacao = st.text_area("Observações", placeholder="Informações adicionais...")
            doc_nf = st.text_input("Link para Documento da NF", placeholder="https://...")
            vencimento = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))
            
            enviar = st.form_submit_button("✅ Registrar Nota Fiscal")
            
            if enviar:
                campos_validos = all([
                    fornecedor.strip(), nf.strip(), ordem_compra.strip(), 
                    valor_total_nf.strip() not in ["", "0,00"]
                ])
                
                if not campos_validos:
                    st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
                else:
                    try:
                        valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                        valor_frete_float = float(valor_frete.replace(".", "").replace(",", "."))
                        
                        df_pedidos_orig = carregar_dados()
                        
                        # --- CORREÇÃO AQUI: BUSCA PELA ORDEM DE COMPRA ---
                        df_update = df_pedidos_orig[df_pedidos_orig['ORDEM_COMPRA'] == ordem_compra].copy()
                        
                        if not df_update.empty:
                            for original_index in df_update.index:
                                df_pedidos_orig.loc[original_index, 'STATUS_PEDIDO'] = 'ENTREGUE'
                                df_pedidos_orig.loc[original_index, 'DATA_ENTREGA'] = pd.to_datetime(data)
                                df_pedidos_orig.loc[original_index, 'STATUS_FINANCEIRO'] = 'EM ANDAMENTO'
                                df_pedidos_orig.loc[original_index, 'NF'] = nf
                                df_pedidos_orig.loc[original_index, 'V. TOTAL NF'] = valor_total_float
                            
                            salvar_dados(df_pedidos_orig)
                            st.success(f"🎉 Nota fiscal registrada! O pedido com a OC '{ordem_compra}' foi atualizado como ENTREGUE no painel do comprador.")
                        else:
                            novo_registro = {
                                "DATA": pd.to_datetime(data),
                                "RECEBEDOR": recebedor,
                                "FORNECEDOR": fornecedor,
                                "NF": nf,
                                "REQUISICAO": np.nan, # Requisição não existe neste contexto
                                "VOLUME": volume,
                                "V. TOTAL NF": valor_total_float,
                                "CONDICAO_FRETE": condicao_frete,
                                "VALOR_FRETE": valor_frete_float,
                                "OBSERVAÇÃO": observacao,
                                "DOC NF": doc_nf,
                                "VENCIMENTO": pd.to_datetime(vencimento),
                                "STATUS_FINANCEIRO": "EM ANDAMENTO",
                                "STATUS_PEDIDO": "PENDENTE",
                                "DATA_ENTREGA": pd.NaT,
                                "ORDEM_COMPRA": ordem_compra, # Novo registro com a OC informada
                            }
                            df_pedidos_orig = pd.concat([df_pedidos_orig, pd.DataFrame([novo_registro])], ignore_index=True)
                            salvar_dados(df_pedidos_orig)
                            st.warning(f"ℹ️ Nota fiscal registrada. A OC '{ordem_compra}' não foi encontrada para atualização automática. Os dados foram salvos como um novo registro.")
                        
                        st.success("Nota fiscal registrada e dados salvos com sucesso!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    
                    except ValueError:
                        st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")

elif menu_option == "📊 Dashboard":
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
            # --- CORREÇÃO AQUI: BUSCA POR ORDEM DE COMPRA ---
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
        # --- CORREÇÃO AQUI: FILTRO POR ORDEM DE COMPRA ---
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
                'STATUS_FINANCEIRO', 'CONDICAO_PROBLEMA', 'OBSERVAÇÃO', 'VENCIMENTO'
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
