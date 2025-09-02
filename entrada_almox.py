import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

st.set_page_config(page_title="Painel Almoxarifado", layout="wide")

# Função para carregar ou criar o banco de dados
def carregar_dados():
    try:
        df = pd.read_csv("dados_almoxarifado.csv")
        if df.empty:
            df = pd.DataFrame(columns=[
                "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
                "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
                "OBSERVAÇÃO", "DOC NF", "VENCIMENTO"
            ])
        if 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)
        if 'VENCIMENTO' in df.columns:
            df['VENCIMENTO'] = pd.to_datetime(df['VENCIMENTO'], errors='coerce', dayfirst=True)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df = pd.DataFrame(columns=[
            "DATA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
            "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
            "OBSERVAÇÃO", "DOC NF", "VENCIMENTO"
        ])
    return df

# Função para salvar os dados
def salvar_dados(df):
    df_copy = df.copy()
    if 'DATA' in df_copy.columns and pd.api.types.is_datetime64_any_dtype(df_copy['DATA']):
        df_copy['DATA'] = df_copy['DATA'].dt.strftime('%d/%m/%Y')
    if 'VENCIMENTO' in df_copy.columns and pd.api.types.is_datetime64_any_dtype(df_copy['VENCIMENTO']):
        df_copy['VENCIMENTO'] = df_copy['VENCIMENTO'].dt.strftime('%d/%m/%Y')
    df_copy.to_csv("dados_almoxarifado.csv", index=False)

df = carregar_dados()

st.title("Registro de Notas Fiscais")

# Preparar lista de fornecedores existentes
fornecedores_list = sorted(df["FORNECEDOR"].dropna().astype(str).unique().tolist()) if not df.empty else []

# Formulário horizontal
with st.form("formulario_nota", clear_on_submit=True):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        data = st.date_input("Data*", datetime.date.today())
    
    with col2:
        fornecedor_input = st.text_input("Fornecedor*", key="fornecedor_input", placeholder="Digite o nome do fornecedor...")
        if fornecedor_input:
            sugestoes = [f for f in fornecedores_list if fornecedor_input.lower() in f.lower()]
            if sugestoes:
                st.write("**Sugestões:**")
                for sugestao in sugestoes[:5]:
                    if st.button(sugestao, key=f"sug_{sugestao}"):
                        st.session_state.fornecedor_input = sugestao
                        st.rerun()
    
    with col3:
        recebedor = st.selectbox("Recebedor*", [
            "ARLEY GONCALVES DOS SANTOS",
            "EVIANE DAS GRACAS DE ASSIS",
            "ANDRE CASTRO DE SOUZA",
            "ISABELA CAROLINA DE PAURA SOARES",
            "EMERSON ALMEIDA DE ARAUJO",
            "GABRIEL PEREIRA MARTINS",
            "OUTROS"
        ])
    
    with col4:
        nf = st.text_input("NF*")
    
    with col5:
        pedido = st.text_input("Pedido*")
    
    with col6:
        volume = st.number_input("Volume*", min_value=1)
    
    col7, col8, col9, col10, col11 = st.columns(5)
    with col7:
        valor_total_nf = st.text_input("V. TOTAL NF* (ex: 1234,56)", value="0,00")
    
    with col8:
        condicao_frete = st.selectbox("Condição de Frete", ["CIF", "FOB"])
    
    with col9:
        if condicao_frete == "CIF":
            valor_frete = "0,00"
            st.text_input("Valor Frete", value=valor_frete, key="valor_frete_cif")
        else:
            valor_frete = st.text_input("Valor Frete (ex: 123,45)", value="0,00", key="valor_frete_fob")
    
    with col10:
        observacao = st.text_input("Observação")
    
    with col11:
        vencimento = st.date_input("Vencimento da Fatura", datetime.date.today())
    
    doc_nf = st.text_input("Link DOC NF")
    
    enviar = st.form_submit_button("Registrar Nota")
    
    if enviar:
        fornecedor_final = fornecedor_input.strip()
        
        campos_obrigatorios = {
            "Fornecedor": fornecedor_final,
            "Recebedor": recebedor,
            "NF": nf.strip(),
            "Pedido": pedido.strip(),
            "Volume": volume > 0,
            "Valor Total NF": valor_total_nf.strip() not in ["", "0,00"]
        }
        
        campos_faltantes = [campo for campo, preenchido in campos_obrigatorios.items() if not preenchido]
        
        if campos_faltantes:
            st.error(f"Campos obrigatórios não preenchidos: {', '.join(campos_faltantes)}")
        else:
            try:
                valor_total_nf_float = float(valor_total_nf.replace(".", "").replace(",", "."))
                valor_frete_float = 0.0 if condicao_frete == "CIF" else float(valor_frete.replace(".", "").replace(",", ".")) if valor_frete else 0.0
                
                novo_registro = {
                    "DATA": pd.to_datetime(data),
                    "RECEBEDOR": recebedor,
                    "FORNECEDOR": fornecedor_final,
                    "NF": nf,
                    "PEDIDO": pedido,
                    "VOLUME": volume,
                    "V. TOTAL NF": valor_total_nf_float,
                    "CONDICAO FRETE": condicao_frete,
                    "VALOR FRETE": valor_frete_float,
                    "OBSERVAÇÃO": observacao,
                    "DOC NF": doc_nf,
                    "VENCIMENTO": pd.to_datetime(vencimento)
                }
                
                df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
                salvar_dados(df)
                st.success("Nota registrada com sucesso!")
            except ValueError:
                st.error("Erro na conversão de valores numéricos. Verifique os formatos.")

# Sidebar: notas do mês
st.sidebar.header("Notas enviadas este mês")
if not df.empty and 'DATA' in df.columns:
    df["DATA_DT"] = pd.to_datetime(df["DATA"], errors='coerce')
    mes_atual = datetime.date.today().month
    ano_atual = datetime.date.today().year
    
    df_mes = df[(df["DATA_DT"].dt.month == mes_atual) & (df["DATA_DT"].dt.year == ano_atual)]
    
    if not df_mes.empty:
        df_mes_exibir = df_mes[["DATA_DT", "NF", "FORNECEDOR", "V. TOTAL NF"]].copy()
        df_mes_exibir["DATA"] = df_mes_exibir["DATA_DT"].dt.strftime('%d/%m/%Y')
        df_mes_exibir = df_mes_exibir[["DATA", "NF", "FORNECEDOR", "V. TOTAL NF"]]
        st.sidebar.dataframe(df_mes_exibir, hide_index=True)
    else:
        st.sidebar.write("Nenhuma nota registrada neste mês.")
else:
    st.sidebar.write("Nenhum dado disponível.")

# Dashboard Top 5
st.subheader("Dashboard Resumido")
if not df.empty and 'DATA_DT' in df.columns:
    df_mes_atual = df[(df["DATA_DT"].dt.month == datetime.date.today().month) & 
                     (df["DATA_DT"].dt.year == datetime.date.today().year)]
    
    if not df_mes_atual.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            top5_nf = df_mes_atual.groupby("FORNECEDOR")["NF"].count().sort_values(ascending=False).head(5).reset_index()
            if not top5_nf.empty:
                fig1 = px.bar(top5_nf, x="NF", y="FORNECEDOR", orientation='h', 
                             title="Top 5 Quantidade de Notas",
                             labels={"NF": "Quantidade", "FORNECEDOR": "Fornecedor"})
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            top5_valor = df_mes_atual.groupby("FORNECEDOR")["V. TOTAL NF"].sum().sort_values(ascending=False).head(5).reset_index()
            if not top5_valor.empty:
                fig2 = px.bar(top5_valor, x="V. TOTAL NF", y="FORNECEDOR", orientation='h',
                             title="Top 5 Valor Total",
                             labels={"V. TOTAL NF": "Valor Total (R$)", "FORNECEDOR": "Fornecedor"})
                st.plotly_chart(fig2, use_container_width=True)

# Histórico detalhado
st.subheader("Histórico de Notas")
if not df.empty and 'DATA_DT' in df.columns:
    meses_disponiveis = sorted(df["DATA_DT"].dt.month.dropna().unique())
    meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junio",
                  7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    if meses_disponiveis:
        mes_selecionado = st.selectbox("Selecione o mês", 
                                      options=meses_disponiveis,
                                      format_func=lambda x: f"{meses_nomes.get(x, x)}")
        
        df_historico = df[df["DATA_DT"].dt.month == mes_selecionado].copy()
        
        if not df_historico.empty:
            df_historico["DATA_FORMATADA"] = df_historico["DATA_DT"].dt.strftime('%d/%m/%Y')
            df_historico_exibir = df_historico[[
                "DATA_FORMATADA", "RECEBEDOR", "FORNECEDOR", "NF", "PEDIDO",
                "VOLUME", "V. TOTAL NF", "CONDICAO FRETE", "VALOR FRETE",
                "OBSERVAÇÃO", "DOC NF", "VENCIMENTO"
            ]].copy()
            
            # Formatar valores monetários
            df_historico_exibir["V. TOTAL NF"] = df_historico_exibir["V. TOTAL NF"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            df_historico_exibir["VALOR FRETE"] = df_historico_exibir["VALOR FRETE"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            
            # Formatar vencimento
            df_historico_exibir["VENCIMENTO"] = pd.to_datetime(df_historico_exibir["VENCIMENTO"], errors='coerce').dt.strftime('%d/%m/%Y')
            
            # Links para documentos
            df_historico_exibir["DOC NF"] = df_historico_exibir["DOC NF"].apply(
                lambda x: f'<a href="{x}" target="_blank">📄 Abrir PDF</a>' 
                if pd.notna(x) and str(x).strip() != "" and str(x).startswith(('http://', 'https://')) 
                else "N/A"
            )
            
            st.write(df_historico_exibir.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.write("Nenhuma nota encontrada para o mês selecionado.")
    else:
        st.write("Nenhum dado disponível para exibir histórico.")
else:
    st.write("Nenhum dado disponível.")
