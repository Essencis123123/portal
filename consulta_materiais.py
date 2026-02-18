import streamlit as st
import pandas as pd

st.set_page_config(page_title="Consulta de Materiais", layout="wide")
st.title('🔍 Consulta de Códigos de Materiais')

try:
    # Carrega o arquivo Excel
    df = pd.read_excel('Database - Códigos Oracle.xlsx')
    
    # Barra de busca
    search = st.text_input('Pesquise por Código ou Nome:')
    
    # Filtro de busca
    if search:
        filtered = df[
            (df.iloc[:, 0].astype(str).str.contains(search, case=False)) |
            (df.iloc[:, 1].astype(str).str.contains(search, case=False))
        ]
    else:
        filtered = df
    
    # Paginação
    page_size = 10
    total_pages = (len(filtered) // page_size) + (1 if len(filtered) % page_size > 0 else 0)
    page = st.number_input('Página:', min_value=1, max_value=total_pages, value=1)
    
    start = (page - 1) * page_size
    end = start + page_size
    
    # Exibir dados
    st.dataframe(filtered.iloc[start:end], width='stretch')
    
    # Resumo
    st.write(f"Total: {len(df)} | Encontrados: {len(filtered)} | Página {page} de {total_pages}")
    
except FileNotFoundError:
    st.error("❌ Arquivo 'Database - Códigos Oracle.xlsx' não encontrado!")
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    print("Este script é uma aplicação Streamlit. Execute com:\n    streamlit run consulta_materiais.py")