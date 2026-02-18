import streamlit as st

st.set_page_config(page_title="Teste", layout="wide")
st.title('✅ Streamlit Funcionando!')
st.write("Se você vê esta página, o Streamlit está OK.")
st.write("O erro anterior era relacionado ao arquivo Excel.")

# Teste simples
df_test = {"Código": [1, 2, 3], "Nome": ["A", "B", "C"]}
import pandas as pd
st.dataframe(pd.DataFrame(df_test), width='stretch')
