import streamlit as st
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

# =============================================================================
# SISTEMA DE NOTIFICAÇÕES
# =============================================================================

class NotificationSystem:
    """Sistema de notificações para o portal"""
    
    def __init__(self):
        self.notification_types = {
            'info': {'icon': 'ℹ️', 'color': '#0055a5'},
            'success': {'icon': '✅', 'color': '#4CAF50'},
            'warning': {'icon': '⚠️', 'color': '#FF9800'},
            'error': {'icon': '❌', 'color': '#f44336'},
            'new': {'icon': '🆕', 'color': '#9C27B0'}
        }
    
    def add_notification(self, message, type='info', persistent=False):
        """Adiciona uma notificação"""
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        
        notification = {
            'id': len(st.session_state.notifications),
            'message': message,
            'type': type,
            'timestamp': datetime.datetime.now(),
            'persistent': persistent,
            'read': False
        }
        
        st.session_state.notifications.append(notification)
    
    def show_notifications(self, limit=5):
        """Mostra notificações no sidebar"""
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        
        unread_count = len([n for n in st.session_state.notifications if not n['read']])
        
        if unread_count > 0:
            st.sidebar.markdown(f"### 🔔 Notificações ({unread_count})")
        else:
            st.sidebar.markdown("### 🔕 Notificações")
        
        # Mostrar últimas notificações
        recent_notifications = st.session_state.notifications[-limit:]
        
        for notification in reversed(recent_notifications):
            self._render_notification(notification)
    
    def _render_notification(self, notification):
        """Renderiza uma notificação individual"""
        type_info = self.notification_types.get(notification['type'], self.notification_types['info'])
        
        # Status de lida/não lida
        read_status = "📖" if notification['read'] else "📬"
        
        # Tempo relativo
        time_diff = datetime.datetime.now() - notification['timestamp']
        if time_diff.days > 0:
            time_str = f"{time_diff.days}d atrás"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600}h atrás"
        elif time_diff.seconds > 60:
            time_str = f"{time_diff.seconds // 60}m atrás"
        else:
            time_str = "agora"
        
        # Card da notificação
        st.sidebar.markdown(f"""
        <div style="
            background: {'rgba(255,255,255,0.1)' if not notification['read'] else 'rgba(255,255,255,0.05)'};
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            border-left: 3px solid {type_info['color']};
        ">
            <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                <span style="font-size: 1.1rem; margin-right: 0.5rem;">{type_info['icon']}</span>
                <span style="font-size: 0.75rem; opacity: 0.7;">{time_str}</span>
                <span style="margin-left: auto;">{read_status}</span>
            </div>
            <div style="font-size: 0.85rem; line-height: 1.3;">
                {notification['message']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Marcar como lida quando visualizada
        if not notification['read']:
            notification['read'] = True
    
    def clear_notifications(self):
        """Limpa todas as notificações"""
        st.session_state.notifications = []
    
    def send_email_notification(self, to_email, subject, message, smtp_config=None):
        """Envia notificação por email"""
        if not smtp_config:
            # Configuração padrão (deve ser configurada em produção)
            smtp_config = {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email': 'sistema@essencis.com',
                'password': 'senha_app'  # Em produção, usar variáveis de ambiente
            }
        
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = smtp_config['email']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Corpo do email em HTML
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f7fa; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #1C4D86; margin: 0;">🏢 Sistema Essencis</h1>
                        <div style="height: 3px; background: linear-gradient(135deg, #0055a5, #1C4D86); margin: 10px 0;"></div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="color: #1C4D86; margin-top: 0;">{subject}</h2>
                        <div style="color: #666; line-height: 1.6;">
                            {message}
                        </div>
                    </div>
                    
                    <div style="text-align: center; font-size: 0.9rem; color: #888; margin-top: 30px;">
                        <p>Esta é uma mensagem automática do Sistema de Gestão Essencis.</p>
                        <p>Data: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Enviar email
            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            server.starttls()
            server.login(smtp_config['email'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            return False

# Instância global do sistema de notificações
notification_system = NotificationSystem()

# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

def notify_info(message, persistent=False):
    """Adiciona notificação de informação"""
    notification_system.add_notification(message, 'info', persistent)

def notify_success(message, persistent=False):
    """Adiciona notificação de sucesso"""
    notification_system.add_notification(message, 'success', persistent)

def notify_warning(message, persistent=False):
    """Adiciona notificação de aviso"""
    notification_system.add_notification(message, 'warning', persistent)

def notify_error(message, persistent=False):
    """Adiciona notificação de erro"""
    notification_system.add_notification(message, 'error', persistent)

def notify_new(message, persistent=False):
    """Adiciona notificação de novidade"""
    notification_system.add_notification(message, 'new', persistent)

def show_notifications_sidebar():
    """Mostra notificações na sidebar"""
    notification_system.show_notifications()

def clear_all_notifications():
    """Limpa todas as notificações"""
    notification_system.clear_notifications()

# =============================================================================
# NOTIFICAÇÕES ESPECÍFICAS DO SISTEMA
# =============================================================================

def notify_new_purchase_order(order_number, requester):
    """Notifica sobre novo pedido de compra"""
    message = f"Novo pedido de compra #{order_number} criado por {requester}"
    notify_new(message, persistent=True)

def notify_purchase_approved(order_number, approver):
    """Notifica sobre pedido aprovado"""
    message = f"Pedido #{order_number} foi aprovado por {approver}"
    notify_success(message)

def notify_invoice_due_soon(invoice_number, days_until_due):
    """Notifica sobre nota fiscal próxima do vencimento"""
    message = f"NF #{invoice_number} vence em {days_until_due} dias"
    notify_warning(message, persistent=True)

def notify_invoice_overdue(invoice_number, days_overdue):
    """Notifica sobre nota fiscal vencida"""
    message = f"NF #{invoice_number} está vencida há {days_overdue} dias"
    notify_error(message, persistent=True)

def notify_low_stock(material_name, current_stock, min_stock):
    """Notifica sobre estoque baixo"""
    message = f"Estoque baixo: {material_name} ({current_stock} unidades, mínimo: {min_stock})"
    notify_warning(message, persistent=True)

def notify_reimbursement_request(requester_name, amount):
    """Notifica sobre solicitação de reembolso"""
    message = f"Nova solicitação de reembolso de {requester_name}: R$ {amount:,.2f}"
    notify_new(message, persistent=True)

def notify_contract_renewal_due(contract_number, days_until_renewal):
    """Notifica sobre renovação de contrato próxima"""
    message = f"Contrato #{contract_number} deve ser renovado em {days_until_renewal} dias"
    notify_warning(message, persistent=True)

# =============================================================================
# SISTEMA DE ALERTAS AUTOMÁTICOS
# =============================================================================

def check_and_create_alerts():
    """Verifica condições e cria alertas automáticos"""
    from database_setup import execute_query
    
    try:
        # Verificar notas fiscais próximas do vencimento
        invoices_due_soon = execute_query("""
            SELECT numero_nf, data_vencimento, 
                   (julianday(data_vencimento) - julianday('now')) as days_until_due
            FROM notas_fiscais 
            WHERE status = 'Pendente' 
            AND (julianday(data_vencimento) - julianday('now')) BETWEEN 0 AND 7
        """)
        
        for _, invoice in invoices_due_soon.iterrows():
            days = int(invoice['days_until_due'])
            if days >= 0:
                notify_invoice_due_soon(invoice['numero_nf'], days)
            else:
                notify_invoice_overdue(invoice['numero_nf'], abs(days))
        
        # Verificar estoque baixo
        low_stock_items = execute_query("""
            SELECT descricao, estoque_atual, estoque_minimo
            FROM materiais 
            WHERE ativo = 1 
            AND estoque_atual <= estoque_minimo 
            AND estoque_minimo > 0
        """)
        
        for _, item in low_stock_items.iterrows():
            notify_low_stock(
                item['descricao'], 
                item['estoque_atual'], 
                item['estoque_minimo']
            )
        
        # Verificar contratos próximos da renovação
        contracts_due = execute_query("""
            SELECT numero_contrato, data_renovacao,
                   (julianday(data_renovacao) - julianday('now')) as days_until_renewal
            FROM contratos 
            WHERE status = 'Ativo' 
            AND (julianday(data_renovacao) - julianday('now')) BETWEEN 0 AND 30
        """)
        
        for _, contract in contracts_due.iterrows():
            days = int(contract['days_until_renewal'])
            if days >= 0:
                notify_contract_renewal_due(contract['numero_contrato'], days)
        
    except Exception as e:
        notify_error(f"Erro ao verificar alertas automáticos: {str(e)}")

# =============================================================================
# COMPONENTE DE NOTIFICAÇÕES PARA STREAMLIT
# =============================================================================

def create_notification_toast(message, type='info', duration=3000):
    """Cria um toast de notificação com JavaScript"""
    type_info = notification_system.notification_types.get(type, notification_system.notification_types['info'])
    
    toast_html = f"""
    <div id="toast-{datetime.datetime.now().timestamp()}" style="
        position: fixed;
        top: 20px;
        right: 20px;
        background: {type_info['color']};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999;
        max-width: 300px;
        animation: slideInRight 0.3s ease-out;
        font-family: 'Montserrat', sans-serif;
    ">
        <div style="display: flex; align-items: center;">
            <span style="font-size: 1.2rem; margin-right: 10px;">{type_info['icon']}</span>
            <span style="flex: 1;">{message}</span>
        </div>
    </div>
    
    <style>
    @keyframes slideInRight {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}
    </style>
    
    <script>
    setTimeout(function() {{
        var toast = document.getElementById('toast-{datetime.datetime.now().timestamp()}');
        if (toast) {{
            toast.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(function() {{
                toast.remove();
            }}, 300);
        }}
    }}, {duration});
    </script>
    """
    
    st.markdown(toast_html, unsafe_allow_html=True)

# Exemplo de uso das notificações
if __name__ == "__main__":
    # Demonstração do sistema de notificações
    print("🔔 Sistema de Notificações do Portal")
    
    # Adicionar algumas notificações de exemplo
    notify_info("Sistema iniciado com sucesso")
    notify_success("Dados carregados")
    notify_warning("Verificar configurações de email")
    notify_new("Nova funcionalidade disponível")
    
    print(f"📬 {len(st.session_state.get('notifications', []))} notificações criadas")