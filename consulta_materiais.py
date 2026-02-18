import streamlit as st
import pandas as pd

st.set_page_config(page_title="Consulta de Materiais", layout="wide")
st.title('🔍 Consulta de Códigos de Materiais')

try:
    # Carrega o arquivo Excel
    df = pd.read_excel('Database - Códigos Oracle.xlsx')
    
    # Mostrar informações do arquivo (debug)
    with st.expander("ℹ️ Informações do arquivo"):
        st.write(f"**Total de linhas:** {len(df)}")
        st.write(f"**Colunas:** {list(df.columns)}")
        st.write(f"**Tipos:** {df.dtypes.to_dict()}")
    
    # Barra de busca
    search = st.text_input('🔎 Pesquise por qualquer campo:')
    
    # Filtro de busca - busca em TODOS os campos
    if search:
        try:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            filtered = df[mask]
        except Exception as search_error:
            st.warning(f"⚠️ Erro na busca: {str(search_error)}")
            filtered = df
    else:
        filtered = df
    
    # Paginação
    page_size = 10
    total_pages = max(1, (len(filtered) // page_size) + (1 if len(filtered) % page_size > 0 else 0))
    
    if total_pages > 1:
        page = st.number_input('Página:', min_value=1, max_value=total_pages, value=1)
    else:
        page = 1
    
    start = (page - 1) * page_size
    end = start + page_size
    
    # Exibir dados
    if len(filtered) > 0:
        st.dataframe(filtered.iloc[start:end], width='stretch')
    else:
        st.info("Nenhum resultado encontrado.")
    
    # Resumo
    st.write(f"**Total:** {len(df)} | **Encontrados:** {len(filtered)} | **Página {page} de {total_pages}**")
    
except FileNotFoundError:
    st.error("❌ Arquivo 'Database - Códigos Oracle.xlsx' não encontrado!")
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
    st.info("💡 Dica: Clique em 'ℹ️ Informações do arquivo' acima para ver detalhes.")


if __name__ == "__main__":
    print("Este script é uma aplicação Streamlit. Execute com:\n    streamlit run consulta_materiais.py")