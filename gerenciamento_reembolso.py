# --- ÁREA ADMINISTRATIVA ---
elif menu == "Área Administrativa":
    # Verificar se o usuário é administrador
    if st.session_state.current_user['EMAIL'].lower() != "earaujo@essencis.com.br":
        st.warning("Acesso restrito aos administradores.")
        st.stop()
    
    st.header("📊 Área Administrativa - Gestão de Reembolsos")
    
    # Carregar dados
    df_reembolsos = load_reembolsos_data()
    
    if df_reembolsos.empty:
        st.info("Nenhum reembolso encontrado.")
        st.stop()
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "Pendente", "Aprovado", "Pago", "Rejeitado"]
        )
    with col2:
        departamento_filter = st.selectbox(
            "Filtrar por Departamento",
            ["Todos"] + DEPARTAMENTOS
        )
    with col3:
        data_filter = st.date_input(
            "Filtrar por Data",
            value=None,
            help="Deixe em branco para todas as datas"
        )
    
    # Aplicar filtros
    filtered_df = df_reembolsos.copy()
    
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['STATUS'] == status_filter]
    
    if departamento_filter != "Todos":
        filtered_df = filtered_df[filtered_df['DEPARTAMENTO'] == departamento_filter]
    
    if data_filter:
        filtered_df = filtered_df[pd.to_datetime(filtered_df['DATA']) == pd.to_datetime(data_filter)]
    
    # Estatísticas rápidas
    st.subheader("📈 Estatísticas Gerais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(df_reembolsos)
        st.metric("Total de Reembolsos", total)
    
    with col2:
        pendentes = len(df_reembolsos[df_reembolsos['STATUS'] == 'Pendente'])
        st.metric("Pendentes", pendentes)
    
    with col3:
        valor_total = df_reembolsos['VALOR'].sum()
        st.metric("Valor Total", f"R$ {valor_total:,.2f}")
    
    with col4:
        valor_pendente = df_reembolsos[df_reembolsos['STATUS'] == 'Pendente']['VALOR'].sum()
        st.metric("Valor Pendente", f"R$ {valor_pendente:,.2f}")
    
    # Lista de reembolsos
    st.subheader("📋 Lista de Reembolsos")
    
    for index, row in filtered_df.iterrows():
        with st.expander(f"Reembolso #{index+1} - {row['NOME']} - R$ {row['VALOR']:,.2f} - {row['STATUS']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Solicitante:** {row['NOME']}")
                st.write(f"**Email:** {row['EMAIL']}")
                st.write(f"**Departamento:** {row['DEPARTAMENTO']}")
                st.write(f"**Data:** {row['DATA']}")
            
            with col2:
                st.write(f"**Tipo de Despesa:** {row['TIPO_DESPESA']}")
                st.write(f"**Valor:** R$ {row['VALOR']:,.2f}")
                st.write(f"**Status:** {row['STATUS']}")
                st.write(f"**Justificativa:** {row['JUSTIFICATIVA']}")
            
            # Visualizar comprovante
            if pd.notna(row['CAMINHO_RECIBO']) and row['CAMINHO_RECIBO'] != '':
                st.subheader("📎 Comprovante")
                
                try:
                    signed_url = get_signed_url(row['CAMINHO_RECIBO'])
                    if signed_url:
                        # Verificar tipo de arquivo
                        if row['CAMINHO_RECIBO'].lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(signed_url, caption="Comprovante", use_column_width=True)
                        elif row['CAMINHO_RECIBO'].lower().endswith('.pdf'):
                            st.markdown(f"[📄 Baixar PDF]({signed_url})")
                        else:
                            st.markdown(f"[📎 Baixar Arquivo]({signed_url})")
                        
                        st.markdown(f"**Link do comprovante:** [{signed_url}]({signed_url})")
                    else:
                        st.warning("Não foi possível gerar o link do comprovante.")
                except Exception as e:
                    st.error(f"Erro ao carregar comprovante: {e}")
            else:
                st.info("Nenhum comprovante anexado.")
            
            # Controles administrativos
            st.subheader("⚙️ Ações Administrativas")
            
            col_act1, col_act2, col_act3 = st.columns(3)
            
            with col_act1:
                if st.button(f"✅ Aprovar", key=f"approve_{index}"):
                    update_reembolso_status(index, "Aprovado", row['EMAIL'], row['NOME'])
            
            with col_act2:
                if st.button(f"💰 Marcar como Pago", key=f"pay_{index}"):
                    update_reembolso_status(index, "Pago", row['EMAIL'], row['NOME'])
            
            with col_act3:
                if st.button(f"❌ Rejeitar", key=f"reject_{index}"):
                    update_reembolso_status(index, "Rejeitado", row['EMAIL'], row['NOME'])
            
            # Campo para observações
            observacao = st.text_area("Observações (opcional)", key=f"obs_{index}")
            
            if st.button("💾 Salvar Observações", key=f"save_obs_{index}"):
                save_observacao(index, observacao, row['EMAIL'], row['NOME'])

def update_reembolso_status(index, novo_status, email_usuario, nome_usuario):
    """Atualiza o status do reembolso e envia notificação"""
    try:
        sheet = get_reembolsos_sheet()
        if sheet:
            # A planilha começa na linha 2 (linha 1 é cabeçalho)
            row_number = index + 2
            
            # Atualiza o status na planilha
            sheet.update_cell(row_number, 7, novo_status)  # Coluna 7 é STATUS
            
            st.success(f"Status atualizado para '{novo_status}'!")
            
            # Enviar notificação por email
            enviar_notificacao_status(email_usuario, nome_usuario, novo_status)
            
            # Atualizar a página
            st.rerun()
            
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")

def save_observacao(index, observacao, email_usuario, nome_usuario):
    """Salva observações no reembolso"""
    try:
        sheet = get_reembolsos_sheet()
        if sheet and observacao:
            # A planilha começa na linha 2 (linha 1 é cabeçalho)
            row_number = index + 2
            
            # Supondo que a coluna 10 seja para observações
            # Você precisa ajustar conforme sua planilha
            sheet.update_cell(row_number, 10, observacao)
            
            st.success("Observações salvas com sucesso!")
            
            # Enviar email com observações
            enviar_observacao_email(email_usuario, nome_usuario, observacao)
            
    except Exception as e:
        st.error(f"Erro ao salvar observações: {e}")

def enviar_notificacao_status(email_destinatario, nome, novo_status):
    """Envia email de notificação de mudança de status"""
    try:
        if st.session_state.gmail_service and st.session_state.user_email_oauth:
            subject = f"Status do seu reembolso foi atualizado para: {novo_status}"
            
            body = f"""
            <p>Olá, {nome}!</p>
            <p>O status do seu pedido de reembolso foi atualizado.</p>
            <p><b>Novo Status:</b> {novo_status}</p>
            """
            
            if novo_status == "Pago":
                body += """
                <p>✅ <b>Seu reembolso foi processado e pago!</b></p>
                <p>O valor será creditado em sua conta conforme o prazo estabelecido.</p>
                """
            elif novo_status == "Aprovado":
                body += """
                <p>📋 Seu reembolso foi aprovado e está na fila para pagamento.</p>
                <p>Você receberá uma nova notificação quando o pagamento for realizado.</p>
                """
            elif novo_status == "Rejeitado":
                body += """
                <p>❌ Seu reembolso não foi aprovado.</p>
                <p>Entre em contato com o departamento financeiro para mais informações.</p>
                """
            
            body += """
            <p>Acesse a plataforma para mais detalhes.</p>
            <p>Atenciosamente,<br>Departamento Financeiro Essencis</p>
            """
            
            message = create_message(st.session_state.user_email_oauth, email_destinatario, subject, body)
            send_message(st.session_state.gmail_service, 'me', message)
            
    except Exception as e:
        st.error(f"Erro ao enviar notificação: {e}")

def enviar_observacao_email(email_destinatario, nome, observacao):
    """Envia email com observações do administrador"""
    try:
        if st.session_state.gmail_service and st.session_state.user_email_oauth:
            subject = f"Observações sobre seu reembolso - Essencis"
            
            body = f"""
            <p>Olá, {nome}!</p>
            <p>O administrador adicionou uma observação ao seu pedido de reembolso:</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0;">
                <p><b>Observação:</b></p>
                <p>{observacao}</p>
            </div>
            <p>Acesse a plataforma para visualizar seu reembolso completo.</p>
            <p>Atenciosamente,<br>Departamento Financeiro Essencis</p>
            """
            
            message = create_message(st.session_state.user_email_oauth, email_destinatario, subject, body)
            send_message(st.session_state.gmail_service, 'me', message)
            
    except Exception as e:
        st.error(f"Erro ao enviar email com observações: {e}")

# --- ADICIONAR ESTA FUNÇÃO PARA BAIXAR RELATÓRIOS ---
def download_relatorio():
    """Gera e disponibiliza relatório em Excel"""
    try:
        df_reembolsos = load_reembolsos_data()
        
        if not df_reembolsos.empty:
            # Criar um arquivo Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_reembolsos.to_excel(writer, sheet_name='Reembolsos', index=False)
                
                # Formatação
                workbook = writer.book
                worksheet = writer.sheets['Reembolsos']
                
                # Formatar coluna de valores
                money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
                worksheet.set_column('E:E', 15, money_format)  # Coluna E = VALOR
                
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📊 Baixar Relatório Completo (Excel)",
                data=output,
                file_name=f"relatorio_reembolsos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")

# --- ADICIONAR NO FINAL DA ÁREA ADMINISTRATIVA ---
# No final da área administrativa, adicione:
st.divider()
st.subheader("📦 Ferramentas Administrativas")

col_tool1, col_tool2 = st.columns(2)

with col_tool1:
    # Botão para baixar relatório
    download_relatorio()

with col_tool2:
    # Botão para atualizar todos os dados
    if st.button("🔄 Atualizar Dados"):
        st.rerun()

# --- ADICIONAR NOTIFICAÇÕES NA ÁREA DO USUÁRIO ---
# No menu principal do usuário, adicione uma seção de notificações
elif menu == "Notificações":
    st.header("🔔 Minhas Notificações")
    
    user_email = st.session_state.current_user['EMAIL']
    df_reembolsos = load_reembolsos_data()
    
    if not df_reembolsos.empty and 'EMAIL' in df_reembolsos.columns:
        df_usuario = df_reembolsos[df_reembolsos['EMAIL'].str.lower() == user_email.lower()]
        
        if not df_usuario.empty:
            # Mostrar reembolsos com status recentemente alterados
            st.subheader("Últimas Atualizações")
            
            for _, row in df_usuario.iterrows():
                status_color = {
                    "Pendente": "🟡",
                    "Aprovado": "🟢", 
                    "Pago": "✅",
                    "Rejeitado": "🔴"
                }
                
                emoji = status_color.get(row['STATUS'], "⚪")
                
                st.write(f"{emoji} **Reembolso de {row['DATA']}** - {row['STATUS']} - R$ {row['VALOR']:,.2f}")
                st.write(f"*{row['TIPO_DESPESA']}*")
                st.progress(
                    {
                        "Pendente": 0.3,
                        "Aprovado": 0.6, 
                        "Pago": 1.0,
                        "Rejeitado": 0.0
                    }.get(row['STATUS'], 0.0)
                )
                st.divider()
        else:
            st.info("Nenhum reembolso encontrado.")
    else:
        st.warning("Não foi possível carregar os dados.")
