import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Consulta de Materiais", layout="wide")
st.title('🔍 Consulta de Códigos de Materiais')

# Caminho do arquivo
file_path = 'Database - Códigos Oracle.xlsx'

# Verificar se arquivo existe
if not os.path.exists(file_path):
    st.error(f"❌ Arquivo não encontrado: {file_path}")
    st.info("Arquivos disponíveis no diretório:")
    for f in os.listdir('.'):
        st.text(f)
    st.stop()

try:
    # Carregar dados
    df = pd.read_excel(file_path)
    st.success(f"✅ Arquivo carregado com sucesso! Total de linhas: {len(df)}")
    
    # Mostrar colunas
    st.info(f"Colunas encontradas: {list(df.columns)}")
    
    # Barra de busca
    search = st.text_input('🔎 Pesquise por qualquer campo:')
    
    # Filtro
    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = df[mask]
    else:
        filtered = df
    
    # Paginação
    page_size = 10
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = st.number_input('📄 Página:', min_value=1, max_value=total_pages, value=1)
    
    start = (page - 1) * page_size
    end = start + page_size
    
    # Exibir tabela
    st.dataframe(filtered.iloc[start:end], use_container_width=True)
    
    # Resumo
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(df))
    with col2:
        st.metric("Encontrados", len(filtered))
    with col3:
        st.metric("Página", f"{page}/{total_pages}")
    
except Exception as e:
    st.error(f"❌ Erro ao processar arquivo: {str(e)}")
    import traceback
    st.error(traceback.format_exc())