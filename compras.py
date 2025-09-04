elif menu == "📜 Histórico ":
        st.markdown("""
            <div class='header-container'>
                <h1>📜 HISTÓRICO E EDIÇÃO DE PEDIDOS</h1>
                <p>Gerencie e Edite os Registros Anteriores</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("📜 Histórico de Requisições e Pedidos")
        st.info("Edite os dados diretamente na tabela abaixo. As alterações serão salvas automaticamente.")
        
        col_filter_h1, col_filter_h2, col_filter_h3, col_filter_h4 = st.columns(4)
        
        df_history = st.session_state.df_pedidos.copy()

        df_history['DATA'] = pd.to_datetime(df_history['DATA'], errors='coerce', dayfirst=True)

        df_almox = st.session_state.df_almoxarifado.copy()
        if not df_almox.empty:
            df_history = pd.merge(df_history, df_almox[['ORDEM_COMPRA', 'DOC NF']], on='ORDEM_COMPRA', how='left', suffixes=('', '_almox'))
            df_history['DOC NF'] = df_history['DOC NF_almox'].fillna(df_history['DOC NF'])
            df_history.drop(columns=['DOC NF_almox'], inplace=True, errors='ignore')

        if not df_history['DATA'].isnull().all():
            with col_filter_h1:
                meses_disponiveis = df_history['DATA'].dt.month.unique()
                meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                mes_selecionado_h = st.selectbox("Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x))
            with col_filter_h2:
                anos_disponiveis = df_history['DATA'].dt.year.unique()
                ano_selecionado_h = st.selectbox("Ano", sorted(anos_disponiveis, reverse=True))
            
            df_history = df_history[(df_history['DATA'].dt.month == mes_selecionado_h) & (df_history['DATA'].dt.year == ano_selecionado_h)]
        else:
            mes_selecionado_h = None
            ano_selecionado_h = None

        with col_filter_h3:
            solicitantes_disponiveis = ['Todos'] + df_history['SOLICITANTE'].unique().tolist()
            solicitante_selecionado_h = st.selectbox("Solicitante", solicitantes_disponiveis)
        with col_filter_h4:
            req_filter = st.text_input("N° Requisição")

        if solicitante_selecionado_h != 'Todos':
            df_history = df_history[df_history['SOLICITANTE'] == solicitante_selecionado_h]
        if req_filter:
            df_history = df_history[df_history['REQUISICAO'].str.contains(req_filter, case=False, na=False)]

        if df_history.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            st.stop()
        
        df_display = df_history.copy()
        
        def formatar_status_display(status):
            if status == 'ENTREGUE':
                return '🟢 ENTREGUE'
            elif status == 'PENDENTE':
                return '🟡 PENDENTE'
            else:
                return status
        
        df_display['STATUS_PEDIDO'] = df_display['STATUS_PEDIDO'].apply(formatar_status_display)
        
        # --- CORREÇÃO AQUI ---
        # A coluna 'Anexo NF' agora contém os links.
        # Criamos uma nova coluna para o texto de exibição, com o ícone ou 'N/A'.
        df_display['Anexo Display'] = df_display['DOC NF'].apply(lambda x: "📥" if pd.notna(x) and x != "" else "N/A")
        
        edited_history_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=False,
            key='history_editor',
            column_config={
                "STATUS_PEDIDO": st.column_config.SelectboxColumn("Status", options=['🟢 ENTREGUE', '🟡 PENDENTE', 'EM ANDAMENTO', '']),
                "DATA": st.column_config.DateColumn("Data Requisição"),
                "SOLICITANTE": "Solicitante",
                "DEPARTAMENTO": "Departamento",
                "FILIAL": "Filial",
                "MATERIAL": "Material",
                "QUANTIDADE": "Quantidade",
                "TIPO_PEDIDO": st.column_config.SelectboxColumn("Tipo de Pedido", options=["LOCAL", "EMERGENCIAL", "PROGRAMADO"]),
                "REQUISICAO": "N° Requisição",
                "FORNECEDOR": st.column_config.TextColumn("Fornecedor"),
                "ORDEM_COMPRA": st.column_config.TextColumn("Ordem de Compra"),
                "VALOR_ITEM": st.column_config.NumberColumn("Valor do Item", format="%.2f"),
                "VALOR_RENEGOCIADO": st.column_config.NumberColumn("Valor Renegociado", format="%.2f"),
                "DATA_APROVACAO": st.column_config.DateColumn("Data Aprovação"),
                "CONDICAO_FRETE": st.column_config.SelectboxColumn("Condição de Frete", options=["", "CIF", "FOB"]),
                "DATA_ENTREGA": st.column_config.DateColumn("Data Entrega"),
                "DIAS_ATRASO": "Dias Atraso",
                "DIAS_EMISSAO": "Dias Emissão",
                "DOC NF": st.column_config.LinkColumn(
                    "Anexo NF", 
                    help="Clique para visualizar o anexo",
                    # O display_text deve ser uma string, não o nome de uma coluna.
                    # Mas para links, o LinkColumn entende o nome da coluna com os URLs
                    # e o texto de exibição separadamente.
                    # A coluna que contém o texto de exibição é 'Anexo Display'.
                    display_text="Anexo Display"
                )
            },
            column_order=[
                "STATUS_PEDIDO", "REQUISICAO", "SOLICITANTE", "DEPARTAMENTO", "FILIAL", "MATERIAL", "QUANTIDADE",
                "FORNECEDOR", "ORDEM_COMPRA", "VALOR_ITEM", "VALOR_RENEGOCIADO", "DATA", "DATA_APROVACAO",
                "CONDICAO_FRETE", "DATA_ENTREGA", "DIAS_ATRASO", "DIAS_EMISSAO", "DOC NF"
            ]
        )

        if not edited_history_df.equals(df_display):
            st.info("Salvando alterações...")
            
            edited_history_df['STATUS_PEDIDO'] = edited_history_df['STATUS_PEDIDO'].map({
                '🟢 ENTREGUE': 'ENTREGUE',
                '🟡 PENDENTE': 'PENDENTE',
                'EM ANDAMENTO': 'EM ANDAMENTO',
                '': ''
            }).fillna(edited_history_df['STATUS_PEDIDO'])
            
            for index, row in edited_history_df.iterrows():
                # A coluna "DOC NF" deve ser lida da fonte original para evitar perdas
                cols_to_update = [col for col in edited_history_df.columns if col not in ['DOC NF', 'Anexo Display']]
                
                for col in cols_to_update:
                    if col in st.session_state.df_pedidos.columns and col in edited_history_df.columns:
                        st.session_state.df_pedidos.loc[index, col] = edited_history_df.loc[index, col]

                if pd.notna(st.session_state.df_pedidos.loc[index, 'DATA_APROVACAO']) and pd.notna(st.session_state.df_pedidos.loc[index, 'DATA']):
                    dias_emissao = (st.session_state.df_pedidos.loc[index, 'DATA_APROVACAO'] - st.session_state.df_pedidos.loc[index, 'DATA']).days
                    st.session_state.df_pedidos.loc[index, 'DIAS_EMISSAO'] = dias_emissao
                else:
                    st.session_state.df_pedidos.loc[index, 'DIAS_EMISSAO'] = 0

                if pd.notna(st.session_state.df_pedidos.loc[index, 'DATA_ENTREGA']) and pd.notna(st.session_state.df_pedidos.loc[index, 'DATA_APROVACAO']):
                    data_limite = st.session_state.df_pedidos.loc[index, 'DATA_APROVACAO'] + pd.Timedelta(days=15)
                    if st.session_state.df_pedidos.loc[index, 'DATA_ENTREGA'] > data_limite:
                        dias_atraso = (st.session_state.df_pedidos.loc[index, 'DATA_ENTREGA'] - data_limite).days
                        st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = dias_atraso
                    else:
                        st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = 0
                else:
                    st.session_state.df_pedidos.loc[index, 'DIAS_ATRASO'] = 0
            
            salvar_dados_pedidos(st.session_state.df_pedidos)
            st.success("Histórico atualizado com sucesso!")
            st.rerun()

    elif menu == "👤 Cadastro ":
        st.markdown("""
            <div class='header-container'>
                <h1>👤 CADASTRO DE SOLICITANTES</h1>
                <p>Adicione novos Solicitantes ao Sistema</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("➕ Cadastro de Solicitante")
        st.info("Cadastre os solicitantes para que eles possam ser selecionados nas requisições.")
        
        with st.form("form_solicitante"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome = st.text_input("Nome do Solicitante")
            with col2:
                departamento = st.text_input("Departamento")
            with col3:
                filial = st.text_input("Filial")
            email = st.text_input("E-mail")
            
            if st.form_submit_button("Cadastrar"):
                if nome and departamento and filial and email:
                    novo_solicitante = pd.DataFrame([{
                        "NOME": nome,
                        "DEPARTAMENTO": departamento,
                        "EMAIL": email,
                        "FILIAL": filial
                    }])
                    st.session_state.df_solicitantes = pd.concat([st.session_state.df_solicitantes, novo_solicitante], ignore_index=True)
                    salvar_dados_solicitantes(st.session_state.df_solicitantes)
                    st.success(f"Solicitante '{nome}' cadastrado com sucesso!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos para cadastrar o solicitante.")

    elif menu == "📊 Dashboards ":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 DASHBOARD DE DESEMPENHO</h1>
                <p>Análise de Prazos e Custos de Pedidos</p>
            </div>
        """, unsafe_allow_html=True)

        st.header("📊 Análise de Desempenho de Entregas")
        
        if st.session_state.df_pedidos.empty:
            st.info("Nenhum pedido registrado para análise.")
            st.stop()

        df_analise = st.session_state.df_pedidos.copy()
        df_analise['DATA'] = pd.to_datetime(df_analise['DATA'], errors='coerce', dayfirst=True)
        
        st.subheader("Filtros de Período")
        col_filtro1, col_filtro2 = st.columns(2)
        
        if not df_analise['DATA'].isnull().all():
            meses_disponiveis = df_analise['DATA'].dt.month.unique()
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            mes_selecionado = col_filtro1.multiselect("Selecione o Mês", sorted(meses_disponiveis), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis))
        else:
            mes_selecionado = []
        
        if not df_analise['DATA'].isnull().all():
            anos_disponiveis = df_analise['DATA'].dt.year.unique()
            ano_selecionado = col_filtro2.selectbox("Selecione o Ano", sorted(anos_disponiveis, reverse=True))
        else:
            ano_selecionado = None

        if mes_selecionado and ano_selecionado:
            df_filtrado_dash = df_analise[(df_analise['DATA'].dt.month.isin(mes_selecionado)) & (df_analise['DATA'].dt.year == ano_selecionado)]
        else:
            df_filtrado_dash = pd.DataFrame()
        
        if df_filtrado_dash.empty:
            st.warning("Nenhum dado disponível para o período selecionado.")
            st.stop()

        st.subheader("Visão Geral")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_pedidos = len(df_filtrado_dash)
            st.markdown(f"### {total_pedidos}")
            st.markdown("Total de Pedidos")
        with col2:
            pedidos_pendentes = len(df_filtrado_dash[df_filtrado_dash['STATUS_PEDIDO'] == 'PENDENTE'])
            st.markdown(f"### {pedidos_pendentes}")
            st.markdown("Pedidos Pendentes")
        with col3:
            valor_total = df_filtrado_dash['VALOR_ITEM'].sum()
            st.markdown(f"### R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown("Valor Total dos Itens")
        with col4:
            media_atraso = df_filtrado_dash['DIAS_ATRASO'].mean() if not df_filtrado_dash.empty else 0
            st.markdown(f"### {media_atraso:.1f}")
            st.markdown("Média de Dias de Atraso")

        st.subheader("Análise de Pedidos com Atraso de Entrega")
        pedidos_atrasados = df_filtrado_dash[df_filtrado_dash['DIAS_ATRASO'] > 0]
        
        if not pedidos_atrasados.empty:
            fig_atraso = px.bar(
                pedidos_atrasados.groupby('FORNECEDOR')['DIAS_ATRASO'].sum().reset_index().nlargest(10, 'DIAS_ATRASO'),
                x='FORNECEDOR',
                y='DIAS_ATRASO',
                title='Top 10 Fornecedores com Mais Dias de Atraso de Entrega',
                labels={'DIAS_ATRASO': 'Total de Dias de Atraso', 'FORNECEDOR': 'Fornecedor'}
            )
            st.plotly_chart(fig_atraso, use_container_width=True)
        else:
            st.info("Nenhum pedido com atraso de entrega registrado no período.")

        st.subheader("Custo Total por Departamento")
        pedidos_com_custo = df_filtrado_dash[df_filtrado_dash['DEPARTAMENTO'].notna() & (df_filtrado_dash['VALOR_ITEM'] > 0)]
        
        if not pedidos_com_custo.empty:
            custo_por_departamento = pedidos_com_custo.groupby('DEPARTAMENTO')['VALOR_ITEM'].sum().sort_values(ascending=False).reset_index()
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
        else:
            st.info("Nenhum pedido com valor e departamento registrados no período para esta análise.")
        
        st.subheader("Evolução Mensal de Pedidos e Entregas")
        
        df_com_data_aprovacao = df_filtrado_dash.dropna(subset=['DATA_APROVACAO'])
        if not df_com_data_aprovacao.empty:
            df_com_data_aprovacao['MES_APROVACAO'] = df_com_data_aprovacao['DATA_APROVACAO'].dt.to_period('M').astype(str)
            mensal = df_com_data_aprovacao.groupby('MES_APROVACAO').agg(
                pedidos=('REQUISICAO', 'count'),
                entregues=('STATUS_PEDIDO', lambda x: (x == 'ENTREGUE').sum())
            ).reset_index()
            
            fig_evolucao = go.Figure()
            fig_evolucao.add_trace(go.Bar(x=mensal['MES_APROVACAO'], y=mensal['pedidos'], name='Pedidos Aprovados'))
            fig_evolucao.add_trace(go.Bar(x=mensal['MES_APROVACAO'], y=mensal['entregues'], name='Entregas Realizadas'))
            fig_evolucao.update_layout(
                title_text='Volume de Pedidos Aprovados vs. Entregas Realizadas por Mês',
                xaxis_title="Mês/Ano",
                yaxis_title="Quantidade de Pedidos"
            )
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("Não há pedidos com data de aprovação registrada no período para a análise de evolução mensal.")

        st.subheader("Ranking de Tempo de Entrega")
        df_entregues = df_filtrado_dash[df_filtrado_dash['STATUS_PEDIDO'] == 'ENTREGUE'].copy()
        
        if not df_entregues.empty:
            df_entregues['TEMPO_ENTREGA'] = (df_entregues['DATA_ENTREGA'] - df_entregues['DATA_APROVACAO']).dt.days

            ranking_fornecedores = df_entregues.groupby('FORNECEDOR')['TEMPO_ENTREGA'].mean().sort_values().reset_index()
            fig_ranking = px.bar(
                ranking_fornecedores,
                x='FORNECEDOR',
                y='TEMPO_ENTREGA',
                title='Tempo Médio de Entrega por Fornecedor (dias)',
                labels={'TEMPO_ENTREGA': 'Tempo Médio (dias)', 'FORNECEDOR': 'Fornecedor'}
            )
            st.plotly_chart(fig_ranking, use_container_width=True)
        else:
            st.info("Não há pedidos entregues no período para criar o ranking.")

    elif menu == "📊 Performance ":
        st.markdown("""
            <div class='header-container'>
                <h1>📊 PERFORMANCE DE NEGOCIAÇÃO LOCAL</h1>
                <p>Análise de Economia em Pedidos Locais</p>
            </div>
        """, unsafe_allow_html=True)
        st.header("📊 Análise de Performance de Negociações Locais")

        df_performance = st.session_state.df_pedidos.copy()
        df_performance_local = df_performance[df_performance['TIPO_PEDIDO'] == 'LOCAL'].copy()
        
        df_performance_local['DATA'] = pd.to_datetime(df_performance_local['DATA'], errors='coerce', dayfirst=True)
        
        st.markdown("---")
        st.subheader("Filtros de Período")
        col_filtro_p1, col_filtro_p2 = st.columns(2)
        
        mes_selecionado_p = []
        ano_selecionado_p = None
        if not df_performance_local['DATA'].isnull().all():
            meses_disponiveis_p = df_performance_local['DATA'].dt.month.unique()
            meses_nomes = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            mes_selecionado_p = col_filtro_p1.multiselect("Selecione o Mês", sorted(meses_disponiveis_p), format_func=lambda x: meses_nomes.get(x), default=sorted(meses_disponiveis_p))
        
        if not df_performance_local['DATA'].isnull().all():
            anos_disponiveis_p = df_performance_local['DATA'].dt.year.unique()
            ano_selecionado_p = col_filtro_p2.selectbox("Selecione o Ano", sorted(anos_disponiveis_p, reverse=True))
        else:
            ano_selecionado_p = None

        if mes_selecionado_p and ano_selecionado_p:
            df_performance_local = df_performance_local[(df_performance_local['DATA'].dt.month.isin(mes_selecionado_p)) & (df_performance_local['DATA'].dt.year == ano_selecionado_p)]
        else:
            df_performance_local = pd.DataFrame()
        
        if df_performance_local.empty:
            st.info("Nenhum pedido local com valores de negociação preenchidos para análise.")
            st.stop()
        
        df_performance_local = df_performance_local[df_performance_local['VALOR_ITEM'].notna() & df_performance_local['VALOR_RENEGOCIADO'].notna()]
        df_performance_local = df_performance_local[df_performance_local['VALOR_ITEM'] > 0]

        if df_performance_local.empty:
            st.info("Nenhum pedido local com valores de negociação preenchidos para análise.")
            st.stop()
        
        df_performance_local['ECONOMIA'] = df_performance_local['VALOR_ITEM'] - df_performance_local['VALOR_RENEGOCIADO']
        df_performance_local['PERC_ECONOMIA'] = np.where(df_performance_local['VALOR_ITEM'] > 0, 
                                                         (df_performance_local['VALOR_ITEM'] - df_performance_local['VALOR_RENEGOCIADO']) / df_performance_local['VALOR_ITEM'] * 100, 
                                                         0)

        st.subheader("Visão Geral da Performance")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_pedidos_local = len(df_performance_local)
            st.markdown(f"### {total_pedidos_local}")
            st.markdown("Total de Pedidos Locais")
        with col2:
            media_economia = df_performance_local['PERC_ECONOMIA'].mean()
            st.markdown(f"### {media_economia:.2f}%")
            st.markdown("Média de Economia (%)")
        with col3:
            total_economizado = df_performance_local['ECONOMIA'].sum()
            st.markdown(f"### R$ {total_economizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.markdown("Total Economizado")

        st.markdown("---")
        
        csv_performance = df_performance_local.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Download Dados da Performance",
            data=csv_performance,
            file_name=f"performance_local_{'_'.join([str(m) for m in mes_selecionado_p])}-{ano_selecionado_p}.csv",
            mime="text/csv"
        )

        st.subheader("Curva de Desempenho da Negociação (Média Mensal)")
        df_performance_local['MES_APROVACAO'] = df_performance_local['DATA_APROVACAO'].dt.to_period('M').astype(str)
        
        curva_mensal = df_performance_local.groupby('MES_APROVACAO')['PERC_ECONOMIA'].mean().reset_index()
        
        if not curva_mensal.empty:
            fig_curva = px.line(
                curva_mensal,
                x='MES_APROVACAO',
                y='PERC_ECONOMIA',
                markers=True,
                title="Média de Economia Percentual Mensal",
                labels={'PERC_ECONOMIA': 'Média de Economia (%)', 'MES_APROVACAO': 'Mês de Aprovação'}
            )
            st.plotly_chart(fig_curva, use_container_width=True)
        else:
            st.info("Dados de negociação local insuficientes para gerar a curva de desempenho.")
        
        st.markdown("---")

        st.subheader("Principais Solicitantes de Pedidos Locais")
        ranking_solicitantes = df_performance_local['SOLICITANTE'].value_counts().reset_index()
        ranking_solicitantes.columns = ['Solicitante', 'Total de Pedidos Locais']
        
        if not ranking_solicitantes.empty:
            fig_ranking = px.bar(
                ranking_solicitantes.nlargest(10, 'Total de Pedidos Locais'),
                x='Total de Pedidos Locais',
                y='Solicitante',
                orientation='h',
                title='Top 10 Solicitantes de Compras Locais',
                labels={'Total de Pedidos Locais': 'Número de Pedidos', 'Solicitante': 'Solicitante'}
            )
            st.plotly_chart(fig_ranking, use_container_width=True)
        else:
            st.info("Dados de solicitantes locais insuficientes para gerar o ranking.")
