import streamlit as st
import pandas as pd

st.set_page_config(page_title="Consulta de Materiais", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    .main { padding: 2rem 1rem; }
    h1 { text-align: center; color: #1f77b4; margin-bottom: 2rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   padding: 1rem; border-radius: 10px; color: white; text-align: center; }
    .search-box { background: #f0f2f6; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; }
    .result-info { background: #e8f4f8; padding: 1rem; border-left: 5px solid #1f77b4; border-radius: 5px; margin: 1rem 0; }
    .pagination-nav { display: flex; gap: 10px; justify-content: center; align-items: center; margin: 2rem 0; }
    button { border-radius: 5px; padding: 0.5rem 1rem; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title('🔍 Consulta de Códigos de Materiais')

try:
    # Carrega o arquivo Excel
    df = pd.read_excel('Database - Códigos Oracle.xlsx')
    
    # Sidebar com informações
    with st.sidebar:
        st.markdown("### 📊 Estatísticas")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Itens", len(df))
        with col2:
            st.metric("Colunas", len(df.columns))
        
        with st.expander("📋 Detalhes do Arquivo"):
            st.write(f"**Colunas:** {', '.join(df.columns)}")
            st.write("**Primeiras linhas:**")
            st.dataframe(df.head(3), use_container_width=True)
    
    # Barra de busca moderna
    with st.container():
        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search = st.text_input('🔎 Pesquise por qualquer informação:', placeholder='Digite código, nome ou descrição...')
        
        with col2:
            search_button = st.button('🔍 Buscar', use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
    
    # Configurações de paginação
    page_size = 30
    total_pages = max(1, (len(filtered) // page_size) + (1 if len(filtered) % page_size > 0 else 0))
    
    # Inicializar session state para página
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Navegação com setas
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button('⬅️ Anterior', use_container_width=True):
            if st.session_state.current_page > 1:
                st.session_state.current_page -= 1
    
    with col2:
        if st.button('Próximo ➡️', use_container_width=True):
            if st.session_state.current_page < total_pages:
                st.session_state.current_page += 1
    
    with col3:
        page_info = st.empty()
    
    with col4:
        if st.button('⏮️ Primeira', use_container_width=True):
            st.session_state.current_page = 1
    
    with col5:
        if st.button('Última ⏭️', use_container_width=True):
            st.session_state.current_page = total_pages
    
    # Validar página atual
    st.session_state.current_page = max(1, min(st.session_state.current_page, total_pages))
    page_info.markdown(f"<div style='text-align: center; font-weight: bold;'>Página {st.session_state.current_page} de {total_pages}</div>", unsafe_allow_html=True)
    
    # Calcular índices
    start = (st.session_state.current_page - 1) * page_size
    end = start + page_size
    
    # Exibir dados
    st.markdown("---")
    if len(filtered) > 0:
        st.dataframe(filtered.iloc[start:end], use_container_width=True, height=600)
    else:
        st.info("🔍 Nenhum resultado encontrado para sua busca.")
    
    # Resumo modern
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><h3>📦 Total</h3><p style='font-size: 1.5rem;'>{len(df):,}</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><h3>✅ Encontrados</h3><p style='font-size: 1.5rem;'>{len(filtered):,}</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><h3>📄 Página</h3><p style='font-size: 1.5rem;'>{st.session_state.current_page}/{total_pages}</p></div>", unsafe_allow_html=True)
    
except FileNotFoundError:
    st.error("❌ Arquivo 'Database - Códigos Oracle.xlsx' não encontrado!")
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
    st.info("💡 Dica: Clique em 'Detalhes do Arquivo' na barra lateral para ver mais informações.")


if __name__ == "__main__":
    print("Este script é uma aplicação Streamlit. Execute com:\n    streamlit run consulta_materiais.py")


if __name__ == "__main__":
    print("Este script é uma aplicação Streamlit. Execute com:\n    streamlit run consulta_materiais.py")