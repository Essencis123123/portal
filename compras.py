    elif menu == "📜 Histórico ":
        st.markdown("""
            <div class='header-container'>
                <h1>📜 HISTÓRICO E EDIÇÃO DE PEDIDOS</h1>
                <p>Gerencie e Edite os Registros Anteriores</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.header("📜 Visualização e Edição do Histórico")
        st.info("Edite os dados diretamente na tabela abaixo. As alterações serão salvas automaticamente.")

        df_history = st.session_state.df_pedidos.copy()
        
        for col in ['DATA', 'DATA_APROVACAO', 'DATA_ENTREGA', 'PREVISAO_ENTREGA']:
            if col in df_history.columns:
                df_history[col] = df_history[col].apply(parse_date_input)
        
        # Converte as colunas para numéricas antes de calcular e arredondar
        for col in ['QUANTIDADE', 'VALOR_ITEM', 'QUANTIDADE_ENTREGUE']:
            if col in df_history.columns:
                df_history[col] = pd.to_numeric(df_history[col], errors='coerce').fillna(0)

        df_history['VALOR_TOTAL'] = df_history['QUANTIDADE'] * df_history['VALOR_ITEM']
        df_history['VALOR_TOTAL'] = df_history['VALOR_TOTAL'].round(2)
        
        df_almox = st.session_state.df_almoxarifado.copy()
        if not df_almox.empty and 'ORDEM_COMPRA' in df_almox.columns:
            almox_map = df_almox.set_index('ORDEM_COMPRA')['DOC NF'].to_dict()
            if 'ORDEM_COMPRA' in df_history.columns:
                df_history['DOC NF_from_almox'] = df_history['ORDEM_COMPRA'].map(almox_map)
                df_history['DOC NF'] = df_history['DOC NF_from_almox'].fillna(df_history.get('DOC NF', ''))
                df_history.drop(columns=['DOC NF_from_almox'], inplace=True, errors='ignore')
        
        # Filtros
        st.subheader("Filtros")
        col_filter_row1_1, col_filter_row1_2, col_filter_row1_3, col_filter_row1_4 = st.columns(4)
        col_filter_row2_1, col_filter_row2_2, col_filter_row2_3 = st.columns(3)

        with col_filter_row1_1:
            # Verificar se há datas válidas antes de criar o filtro
            datas_validas = df_history.dropna(subset=['DATA'])
            if not datas_validas.empty:
                meses_disponiveis = sorted(datas_validas['DATA'].dt.month.unique())
                meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                               7: "Jullio", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_selecionado_h = st.selectbox("Mês", ["Todos"] + meses_disponiveis, 
                                               format_func=lambda x: meses_nomes.get(x, "Todos") if x != "Todos" else "Todos")
            else:
                mes_selecionado_h = "Todos"
                st.info("Nenhuma data disponível")

        with col_filter_row1_2:
            if not datas_validas.empty:
                anos_disponiveis = sorted(datas_validas['DATA'].dt.year.unique(), reverse=True)
                ano_selecionado_h = st.selectbox("Ano", ["Todos"] + anos_disponiveis)
            else:
                ano_selecionado_h = "Todos"

        with col_filter_row1_3:
            status_options = ['Todos'] 
            if 'STATUS_PEDIDO' in df_history.columns:
                status_options += df_history['STATUS_PEDIDO'].unique().tolist()
            status_selecionado_h = st.selectbox("Status", status_options)

        with col_filter_row1_4:
            solicitantes_disponiveis = ['Todos']
            if 'SOLICITANTE' in df_history.columns:
                solicitantes_disponiveis += df_history['SOLICITANTE'].unique().tolist()
            solicitante_selecionado_h = st.selectbox("Solicitante", solicitantes_disponiveis)
                
        with col_filter_row2_1:
            req_filter = st.text_input("N° Requisição")
        with col_filter_row2_2:
            oc_filter = st.text_input("N° Ordem de Compra")
        with col_filter_row2_3:
            cod_material_filter = st.text_input("Código Material")
        
        # Aplicar filtros
        df_filtrado = df_history.copy()
        
        # Filtro de data
        if mes_selecionado_h != "Todos" and ano_selecionado_h != "Todos":
            try:
                df_filtrado = df_filtrado[
                    (df_filtrado['DATA'].dt.month == mes_selecionado_h) & 
                    (df_filtrado['DATA'].dt.year == ano_selecionado_h)
                ]
            except:
                pass
        
        # Outros filtros
        if status_selecionado_h != 'Todos' and 'STATUS_PEDIDO' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['STATUS_PEDIDO'] == status_selecionado_h]
        
        if solicitante_selecionado_h != 'Todos' and 'SOLICITANTE' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['SOLICITANTE'] == solicitante_selecionado_h]
        
        if req_filter and 'REQUISICAO' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['REQUISICAO'].str.contains(req_filter, case=False, na=False)]
        
        if oc_filter and 'ORDEM_COMPRA' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['ORDEM_COMPRA'].str.contains(oc_filter, case=False, na=False)]
        
        if cod_material_filter and 'CODIGO_MATERIAL' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['CODIGO_MATERIAL'].str.contains(cod_material_filter, case=False, na=False)]

        if df_filtrado.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados. Mostrando todos os registros.")
            df_filtrado = df_history.copy()
        
        st.info(f"Mostrando {len(df_filtrado)} de {len(df_history)} registros")
        
        df_for_editor = df_filtrado.copy()
        
        def formatar_status_display(status):
            if status == 'ENTREGUE':
                return '🟢 ENTREGUE'
            elif status == 'PENDENTE':
                return '🟡 PENDENTE'
            else:
                return status
        
        if 'STATUS_PEDIDO' in df_for_editor.columns:
            df_for_editor['STATUS_PEDIDO'] = df_for_editor['STATUS_PEDIDO'].apply(formatar_status_display)

        for col in ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'VALOR_TOTAL']:
            if col in df_for_editor.columns:
                df_for_editor[col] = df_for_editor[col].apply(
                    lambda x: f"R$ {float(x):.2f}" if pd.notna(x) and x != '' and float(x) != 0 else ''
                )

        edited_history_df = st.data_editor(
            df_for_editor, 
            use_container_width=True,
            hide_index=True,
            key='history_editor',
            column_config={
                "DATA": st.column_config.DateColumn("Data Requisição", format="DD/MM/YYYY"),
                "SOLICITANTE": st.column_config.TextColumn("Solicitante"),
                "DEPARTAMENTO": st.column_config.TextColumn("Departamento"),
                "FILIAL": st.column_config.TextColumn("Filial"),
                "CODIGO_MATERIAL": st.column_config.TextColumn("Cód. Material"),
                "MATERIAL": st.column_config.TextColumn("Material"),
                "UN": st.column_config.TextColumn("UN"),
                "QUANTIDADE": st.column_config.NumberColumn("Quantidade", format="%d"),
                "TIPO_PEDIDO": st.column_config.SelectboxColumn("Tipo de Pedido", options=["LOCAL", "EMERGENCIAL", "PROGRAMADO"]),
                "REQUISICAO": st.column_config.TextColumn("N° Requisição"),
                "FORNECEDOR": st.column_config.TextColumn("Fornecedor"),
                "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                "VALOR_ITEM": st.column_config.NumberColumn("Valor Unitário (R$)", format="R$ %.2f"),
                "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado (R$)", format="R$ %.2f"),
                "DATA_APROVACAO": st.column_config.DateColumn("Data Aprovação", format="DD/MM/YYYY"),
                "PREVISAO_ENTREGA": st.column_config.DateColumn("Previsão de Entrega", format="DD/MM/YYYY"),
                "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB", "RETIRAR"]),
                "STATUS_PEDIDO": st.column_config.SelectboxColumn("Status", options=['🟢 ENTREGUE', '🟡 PENDENTE', 'EM ANDAMENTO', '']),
                "DATA_ENTREGA": st.column_config.DateColumn("Data Entrega", format="DD/MM/YYYY"),
                "DIAS_ATRASO": st.column_config.NumberColumn("Dias Atraso", format="%d"),
                "DIAS_EMISSAO": st.column_config.NumberColumn("Dias Emissão", format="%d"),
                "DOC NF": st.column_config.TextColumn("Doc NF"),
                "QUANTIDADE_ENTREGUE": st.column_config.NumberColumn("Qtd. Entregue", format="%d"),
                "VALOR_TOTAL": st.column_config.NumberColumn("Valor Total (R$)", format="R$ %.2f")
            },
            column_order=COLUNA_ORDEM_PADRAO + ["VALOR_TOTAL"]
        )

        if not edited_history_df.equals(df_for_editor):
            st.info("Salvando alterações...")
            
            edited_history_df['STATUS_PEDIDO'] = edited_history_df['STATUS_PEDIDO'].map({
                '🟢 ENTREGUE': 'ENTREGUE',
                '🟡 PENDENTE': 'PENDENTE',
                'EM ANDAMENTO': 'EM ANDAMENTO',
                '': ''
            }).fillna(edited_history_df['STATUS_PEDIDO'])

            for col_val in ['VALOR_ITEM', 'VALOR_RENEGOCIADO', 'QUANTIDADE_ENTREGUE', 'VALOR_TOTAL']:
                if col_val in edited_history_df.columns:
                    edited_history_df[col_val] = pd.to_numeric(
                        edited_history_df[col_val].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.strip() 
                        if edited_history_df[col_val].dtype == 'object' else edited_history_df[col_val],
                        errors='coerce'
                    ).fillna(0).round(2)
            
            data_cols_history = ['DATA', 'DATA_APROVACAO', 'PREVISAO_ENTREGA', 'DATA_ENTREGA']
            
            for col in data_cols_history:
                if col in edited_history_df.columns:
                    edited_history_df[col] = edited_history_df[col].apply(parse_date_input)
            
            def calcular_dias_atraso(row):
                if pd.notna(row.get('DATA_ENTREGA')) and pd.notna(row.get('PREVISAO_ENTREGA')):
                    if row['DATA_ENTREGA'] > row['PREVISAO_ENTREGA']:
                        return (row['DATA_ENTREGA'] - row['PREVISAO_ENTREGA']).days
                return 0

            def calcular_dias_emissao(row):
                if pd.notna(row.get('DATA_APROVACAO')) and pd.notna(row.get('DATA')):
                    return (row['DATA_APROVACAO'] - row['DATA']).days
                return 0
                
            edited_history_df['DIAS_ATRASO'] = edited_history_df.apply(calcular_dias_atraso, axis=1)
            edited_history_df['DIAS_EMISSAO'] = edited_history_df.apply(calcular_dias_emissao, axis=1)

            # Atualizar os dados originais
            for index, row in edited_history_df.iterrows():
                for col in COLUNA_ORDEM_PADRAO:
                    if col in row.index:
                        st.session_state.df_pedidos.loc[index, col] = row[col]
            
            salvar_dados_pedidos(st.session_state.df_pedidos)
            st.success("Histórico atualizado com sucesso!")
            st.rerun()

        st.markdown("---")
        st.subheader("💰 Resumo do Custo Total")
        total_historico = df_filtrado['VALOR_TOTAL'].sum() if 'VALOR_TOTAL' in df_filtrado.columns else 0
        st.metric(label="Custo Total no Período Selecionado", value=f"R$ {total_historico:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
