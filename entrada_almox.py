import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import re

st.set_page_config(page_title="Painel Almoxarifado", layout="wide")

# Função para carregar ou criar o banco de dados
import pandas as pd
from pandas.errors import EmptyDataError

def carregar_dados():
    try:
        df = pd.read_csv("dados_almoxarifado.csv")
        # Converter a coluna DATA para datetime
        if 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)
        if 'VENCIMENTO' in df.columns:
            df['VENCIMENTO'] = pd.to_datetime(df['VENCIMENTO'], errors='coerce', dayfirst=True)
        
        # Garantir que colunas do financeiro existam
        for col in ["STATUS_FINANCEIRO", "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL"]:
            if col not in df.columns:
                df[col] = "N/A" if col == "REGISTRO_ADICIONAL" else "EM ANDAMENTO"
                
        return df

    except (FileNotFoundError, EmptyDataError):
        # Arquivo não existe ou está vazio: cria DataFrame com colunas
        return pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
            "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
            "OBSERVAÇÃO", "DOC NF", "VENCIMENTO", "STATUS_FINANCEIRO",
            "CONDICAO_PROBLEMA", "REGISTRO_ADICIONAL"
        ])

def salvar_dados_almoxarifado(df):
    """Salva os dados do almoxarifado"""
    try:
        df_copy = df.copy()
        # Converter datas para formato string
        if 'DATA' in df_copy.columns and pd.api.types.is_datetime64_any_dtype(df_copy['DATA']):
            df_copy['DATA'] = df_copy['DATA'].dt.strftime('%d/%m/%Y')
        if 'VENCIMENTO' in df_copy.columns and pd.api.types.is_datetime64_any_dtype(df_copy['VENCIMENTO']):
            df_copy['VENCIMENTO'] = df_copy['VENCIMENTO'].dt.strftime('%d/%m/%Y')
        
        df_copy.to_csv("dados_almoxarifado.csv", index=False, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False

# ---------------------------
# CONFIGURAÇÕES
# ---------------------------
status_options = ["EM ANDAMENTO", "NF PROBLEMA", "CAPTURADO", "FINALIZADO"]
problema_options = ["N/A", "REGISTRO CHAMADO", "CARTA CORRECAO", "AJUSTE NA ORDEM DE COMPRA", "RECUSA DE NOTA FISCAL"]

# ---------------------------
# INTERFACE PRINCIPAL
# ---------------------------
st.markdown("""
    <div style='background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: white; text-align: center; margin: 0;'>🏭 PAINEL ALMOXARIFADO</h1>
        <p style='color: white; text-align: center; margin: 5px 0 0 0; font-size: 18px;'>Sistema de Controle de Notas Fiscais e Status Financeiro</p>
    </div>
""", unsafe_allow_html=True)

# Carregar dados
df = carregar_dados()


# ---------------------------
# FORMULÁRIO DE REGISTRO - ALMOXARIFADO
# ---------------------------
st.header("📝 Registro de Notas Fiscais - Almoxarifado")

with st.expander("➕ Adicionar Nova Nota Fiscal", expanded=True):
    with st.form("formulario_nota", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data = st.date_input("Data*", datetime.date.today())
            fornecedor = st.text_input("Fornecedor*", placeholder="Nome do fornecedor...")
            nf = st.text_input("Número da NF*")
            
        with col2:
            recebedor = st.selectbox("Recebedor*", [
                "ARLEY GONCALVES DOS SANTOS",
                "EVIANE DAS GRACAS DE ASSIS",
                "ANDRE CASTRO DE SOUZA",
                "ISABELA CAROLINA DE PAURA SOARES",
                "EMERSON ALMEIDA DE ARAUJO",
                "GABRIEL PEREIRA MARTINS",
                "OUTROS"
            ])
            pedido = st.text_input("Número do Pedido*")
            volume = st.number_input("Volume*", min_value=1, value=1)
            
        with col3:
            valor_total_nf = st.text_input("Valor Total NF* (ex: 1234,56)", value="0,00")
            condicao_frete = st.selectbox("Condição de Frete", ["CIF", "FOB"])
            if condicao_frete == "FOB":
                valor_frete = st.text_input("Valor Frete (ex: 123,45)", value="0,00")
            else:
                valor_frete = "0,00"
        
        observacao = st.text_area("Observações", placeholder="Informações adicionais...")
        doc_nf = st.text_input("Link para Documento da NF", placeholder="https://...")
        vencimento = st.date_input("Vencimento da Fatura", datetime.date.today() + datetime.timedelta(days=30))
        
        enviar = st.form_submit_button("✅ Registrar Nota Fiscal")
        
        if enviar:
            # Validação dos campos obrigatórios
            campos_validos = all([
                fornecedor.strip(), nf.strip(), pedido.strip(), 
                valor_total_nf.strip() not in ["", "0,00"]
            ])
            
            if not campos_validos:
                st.error("⚠️ Preencha todos os campos obrigatórios marcados com *")
            else:
                try:
                    # Converter valores monetários
                    valor_total_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                    valor_frete_float = float(valor_frete.replace(".", "").replace(",", ".")) if condicao_frete == "FOB" else 0.0
                    
                    novo_registro = {
                        "DATA": pd.to_datetime(data),
                        "RECEBEDOR": recebedor,
                        "FORNECEDOR": fornecedor,
                        "NF": nf,
                        "PEDIDO": pedido,
                        "VOLUME": volume,
                        "V. TOTAL NF": valor_total_float,
                        "CONDICAO FRETE": condicao_frete,
                        "VALOR FRETE": valor_frete_float,
                        "OBSERVAÇÃO": observacao,
                        "DOC NF": doc_nf,
                        "VENCIMENTO": pd.to_datetime(vencimento),
                        "STATUS_FINANCEIRO": "EM ANDAMENTO",
                        "CONDICAO_PROBLEMA": "N/A",
                        "REGISTRO_ADICIONAL": ""
                    }
                    
                    df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
                    if salvar_dados_almoxarifado(df):
                        st.success("🎉 Nota fiscal registrada com sucesso! Status financeiro: EM ANDAMENTO")
                    else:
                        st.error("❌ Erro ao salvar dados")
                        
                except ValueError:
                    st.error("❌ Erro na conversão de valores. Verifique os formatos numéricos.")

# ---------------------------
# PAINEL DE STATUS FINANCEIRO - VISÃO ALMOXARIFADO
# ---------------------------
st.header("📊 Status do Processo Financeiro")

if not df.empty:
    # Estatísticas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    total_nfs = len(df)
    em_andamento = len(df[df['STATUS_FINANCEIRO'] == 'EM ANDAMENTO'])
    com_problema = len(df[df['STATUS_FINANCEIRO'] == 'NF PROBLEMA'])
    finalizadas = len(df[df['STATUS_FINANCEIRO'] == 'FINALIZADO'])
    
    with col1:
        st.metric("📦 Total de NFs", total_nfs)
    with col2:
        st.metric("🔄 Em Andamento", em_andamento)
    with col3:
        st.metric("⚠️ Com Problema", com_problema)
    with col4:
        st.metric("✅ Finalizadas", finalizadas)
    
    # Filtros
    st.subheader("🔍 Filtros de Consulta")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        status_filtro = st.multiselect(
            "Status Financeiro",
            options=status_options,
            default=["EM ANDAMENTO", "NF PROBLEMA"],
            help="Filtrar por situação no financeiro"
        )
    
    with col_f2:
        # Filtro por data
        datas_disponiveis = sorted(df['DATA'].dropna().unique())
        if len(datas_disponiveis) > 0:
            data_inicio = st.date_input(
                "Data Início",
                value=datas_disponiveis[0],
                min_value=datas_disponiveis[0],
                max_value=datas_disponiveis[-1]
            )
        else:
            data_inicio = st.date_input("Data Início", datetime.date.today())
    
    with col_f3:
        fornecedor_filtro = st.multiselect(
            "Fornecedor",
            options=sorted(df['FORNECEDOR'].dropna().unique()),
            help="Filtrar por fornecedor específico"
        )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if status_filtro:
        df_filtrado = df_filtrado[df_filtrado['STATUS_FINANCEIRO'].isin(status_filtro)]
    if fornecedor_filtro:
        df_filtrado = df_filtrado[df_filtrado['FORNECEDOR'].isin(fornecedor_filtro)]
    
    # Mostrar tabela com status
    st.subheader("📋 Situação das Notas Fiscais")
    
    if not df_filtrado.empty:
        # Função para colorir o status
        def colorir_status(status):
            if status == "FINALIZADO":
                return "background-color: #28a745; color: white; padding: 5px; border-radius: 5px;"
            elif status == "NF PROBLEMA":
                return "background-color: #dc3545; color: white; padding: 5px; border-radius: 5px;"
            elif status == "EM ANDAMENTO":
                return "background-color: #ffc107; color: black; padding: 5px; border-radius: 5px;"
            elif status == "CAPTURADO":
                return "background-color: #17a2b8; color: white; padding: 5px; border-radius: 5px;"
            else:
                return ""
        
        # Preparar dados para exibição
        df_exibir = df_filtrado[[
            'DATA', 'FORNECEDOR', 'NF', 'PEDIDO', 'V. TOTAL NF', 
            'STATUS_FINANCEIRO', 'CONDICAO_PROBLEMA', 'REGISTRO_ADICIONAL', 'VENCIMENTO'
        ]].copy()
        
        # Formatar datas e valores
        df_exibir['DATA'] = pd.to_datetime(df_exibir['DATA']).dt.strftime('%d/%m/%Y')
        df_exibir['VENCIMENTO'] = pd.to_datetime(df_exibir['VENCIMENTO']).dt.strftime('%d/%m/%Y')
        df_exibir['V. TOTAL NF'] = df_exibir['V. TOTAL NF'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        # Aplicar estilos
        styled_df = df_exibir.style.applymap(
            lambda x: colorir_status(x) if x in status_options else "", 
            subset=['STATUS_FINANCEIRO']
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=400
        )
        
        # Download dos dados filtrados
        csv = df_exibir.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="status_financeiro.csv",
            mime="text/csv"
        )
        
    else:
        st.info("ℹ️ Nenhuma nota encontrada com os filtros selecionados.")
    
    # Gráficos de acompanhamento
    st.subheader("📈 Análise do Status Financeiro")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Gráfico de pizza - Distribuição de status
        status_count = df['STATUS_FINANCEIRO'].value_counts().reset_index()
        status_count.columns = ['Status', 'Quantidade']
        
        if not status_count.empty:
            fig_pizza = px.pie(
                status_count, 
                values='Quantidade', 
                names='Status',
                title='Distribuição dos Status Financeiros',
                color='Status',
                color_discrete_map={
                    'FINALIZADO': '#28a745',
                    'EM ANDAMENTO': '#ffc107',
                    'NF PROBLEMA': '#dc3545',
                    'CAPTURADO': '#17a2b8'
                }
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
    
    with col_g2:
        # Gráfico de barras - Top fornecedores com problemas
        problemas_df = df[df['STATUS_FINANCEIRO'] == 'NF PROBLEMA']
        if not problemas_df.empty:
            top_problemas = problemas_df['FORNECEDOR'].value_counts().head(10).reset_index()
            top_problemas.columns = ['Fornecedor', 'Notas com Problema']
            
            fig_barras = px.bar(
                top_problemas,
                x='Notas com Problema',
                y='Fornecedor',
                orientation='h',
                title='Top 10 Fornecedores com Problemas',
                color='Notas com Problema'
            )
            st.plotly_chart(fig_barras, use_container_width=True)
        else:
            st.info("✅ Nenhuma nota com problemas no momento")
    
else:
    st.write("Nenhum dado disponível.")
