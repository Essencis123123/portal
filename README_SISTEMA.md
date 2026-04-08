# Sistema de Gestão 360 - Versão Ultra Moderna com Animações SAP Fiori

## 🏢 Visão Geral

Este é um sistema completo de gestão empresarial com interface ultra moderna inspirada no SAP Fiori, desenvolvido em Python com Streamlit. O sistema oferece uma experiência visual premium com animações suaves e design responsivo.

![Dashboard](https://github.com/user-attachments/assets/7ac1aa1c-70d8-408a-ba4f-1eca633d19b7)

## 🎯 Principais Funcionalidades

### 🔐 Sistema de Autenticação
- **Login seguro** com diferentes níveis de acesso
- **Controle de permissões** baseado em perfis de usuário
- **Sessões seguras** com timeout automático

### 🏠 Hub Central Moderno
- **Cards animados** com entrada suave tipo SAP Fiori
- **Layout responsivo** com grid adaptável
- **Navegação intuitiva** com sidebar escura
- **Filtros por categoria** de módulos

### 📊 Módulos Disponíveis

#### 1. **🛒 Gestão de Compras**
- Sistema completo de pedidos de compra
- Workflow de aprovações automatizado
- Controle de status e prazos
- Integração com fornecedores

#### 2. **🔍 Consulta de Compras**
- Consulta rápida de pedidos
- Acesso limitado para usuários específicos
- Filtros avançados por período e status

#### 3. **🏪 Carteira de Fornecedores**
- Gestão completa de fornecedores
- Cadastro e qualificação
- Histórico de compras e avaliações

#### 4. **📦 Gestão de Estoque**
- Controle de movimentações
- Alertas de estoque baixo
- Relatórios de entrada e saída

#### 5. **📋 Gestão de Notas Fiscais**
- Controle de NFs recebidas
- Gestão de vencimentos e pagamentos
- Cálculo automático de juros e multas

#### 6. **💰 Sistema de Reembolsos**
- Solicitação de reembolsos online
- Workflow de aprovação
- Controle de pagamentos

#### 7. **📑 Gestão de Contratos**
- Controle de vigência de contratos
- Alertas de renovação
- Gestão de aditivos e alterações

#### 8. **📊 Dashboard Executivo**
- Métricas em tempo real
- Gráficos interativos com Plotly
- KPIs e indicadores de performance

## 🎨 Características Visuais

### Design SAP Fiori
- **Paleta de cores moderna**: Azuis (#0055a5, #1C4D86) com gradientes
- **Tipografia**: Montserrat para melhor legibilidade
- **Espaçamentos consistentes** seguindo guidelines de UX

### Animações CSS3
- **Fade-in/fade-out** para modais e widgets
- **Slide-in** para headers e cards
- **Hover effects** com transformações suaves
- **Loading spinners** animados
- **Bounce effects** para ícones

### Componentes Modernos
- **Cards responsivos** com sombras e bordas arredondadas
- **Botões com gradientes** e estados visuais
- **Tabelas ultra modernas** com headers estilizados
- **Inputs com bordas arredondadas** e efeitos de foco
- **Sidebar escura** com informações do usuário

## 🗄️ Banco de Dados SQLite

### Estrutura Completa
O sistema inclui um banco de dados SQLite com 11 tabelas principais:

- **usuarios**: Controle de acesso e permissões
- **modulos**: Definição dos módulos do sistema
- **permissoes**: Controle de acesso por módulo
- **fornecedores**: Cadastro completo de fornecedores
- **materiais**: Catálogo de produtos e materiais
- **pedidos_compra**: Gestão de pedidos de compra
- **itens_pedido**: Itens detalhados dos pedidos
- **notas_fiscais**: Controle de notas fiscais
- **movimentacoes_estoque**: Histórico de movimentações
- **contratos**: Gestão de contratos
- **reembolsos**: Sistema de reembolsos
- **logs_auditoria**: Trilha de auditoria completa

### Dados Iniciais
- **5 usuários demo** com diferentes perfis
- **8 módulos** pré-configurados
- **3 fornecedores** de exemplo
- **5 materiais** para demonstração

## 🔔 Sistema de Notificações

### Tipos de Notificações
- **Info** (ℹ️): Informações gerais
- **Sucesso** (✅): Operações bem-sucedidas
- **Aviso** (⚠️): Alertas importantes
- **Erro** (❌): Problemas que requerem atenção
- **Novidade** (🆕): Novas funcionalidades

### Alertas Automáticos
- **Notas fiscais** próximas do vencimento
- **Estoque baixo** em materiais
- **Contratos** próximos da renovação
- **Reembolsos** pendentes de aprovação

### Notificações por Email
- Templates HTML responsivos
- Envio automático via SMTP
- Configuração flexível de servidor

## 🚀 Como Executar

### Pré-requisitos
```bash
pip install -r requirements.txt
```

### Executar o Hub Principal
```bash
streamlit run hub_principal.py
```

### Executar Módulos Individuais
```bash
# Módulo Fiscal Modernizado
streamlit run fiscal_moderno.py

# Outros módulos originais
streamlit run compras.py
streamlit run fiscal.py
streamlit run reembolso.py
```

### Configurar Banco de Dados
```bash
python database_setup.py
```

## 👥 Usuários de Demonstração

### Administrador
- **Email**: admin@essencis.com
- **Senha**: admin123
- **Acesso**: Todos os módulos

### Comprador
- **Email**: comprador@essencis.com
- **Senha**: comprador123
- **Acesso**: Compras, Fornecedores, Consulta

### Financeiro
- **Email**: financeiro@essencis.com
- **Senha**: financeiro123
- **Acesso**: Fiscal, Reembolsos, Contratos

## 🛠️ Tecnologias Utilizadas

### Frontend
- **Streamlit**: Framework principal da interface
- **CSS3**: Animações e estilos SAP Fiori
- **JavaScript**: Interações dinâmicas
- **Plotly**: Gráficos interativos

### Backend
- **Python 3.8+**: Linguagem principal
- **SQLite**: Banco de dados local
- **Pandas**: Manipulação de dados
- **Requests**: Integração com APIs

### Bibliotecas Principais
```
streamlit==1.50.0
pandas==2.3.2
plotly==6.3.0
pillow==11.3.0
requests==2.31.0
sqlite3 (built-in)
```

## 📁 Estrutura do Projeto

```
portal/
├── hub_principal.py           # Hub central com SAP Fiori
├── fiscal_moderno.py         # Módulo fiscal modernizado
├── database_setup.py         # Configuração do banco
├── notificacoes.py          # Sistema de notificações
├── compras.py               # Módulo de compras original
├── fiscal.py                # Módulo fiscal original  
├── reembolso.py             # Módulo de reembolsos
├── painel.py                # Painel de fornecedores
├── consulta.py              # Consulta de compras
├── estoque_nf.py            # Gestão de estoque
├── gerenciamento_reembolso.py # Gestão de reembolsos
├── requirements.txt         # Dependências
├── gestao_empresarial.db    # Banco SQLite (gerado)
└── .streamlit/
    └── secrets.toml         # Configurações secretas
```

## 🎯 Características Técnicas

### Performance
- **Caching inteligente** com @st.cache_resource
- **Conexões otimizadas** ao banco de dados
- **Componentes lazy-loaded** para melhor responsividade

### Segurança
- **Autenticação baseada em sessão**
- **Controle de acesso por módulo**
- **Logs de auditoria** para todas as operações
- **Sanitização de inputs** contra SQL injection

### Responsividade
- **Design mobile-first** adaptável
- **Grid flexível** para diferentes telas
- **Componentes escaláveis** com CSS Grid

## 🔮 Próximas Funcionalidades

### Em Desenvolvimento
- [ ] **Integração com ERP** existente
- [ ] **API RESTful** para integrações
- [ ] **Relatórios avançados** em PDF
- [ ] **Dashboard de BI** com mais métricas
- [ ] **Módulo de RH** com gestão de funcionários
- [ ] **Sistema de backup** automático
- [ ] **Integração com WhatsApp** para notificações
- [ ] **App mobile** com React Native

### Melhorias Planejadas
- [ ] **Dark mode** completo
- [ ] **Temas personalizáveis** pelo usuário
- [ ] **Widgets configuráveis** no dashboard
- [ ] **Exportação para Excel** avançada
- [ ] **Integração com Google Sheets**
- [ ] **Assinatura digital** de documentos

## 🤝 Contribuições

Este projeto está em desenvolvimento ativo. Para contribuir:

1. Fork do repositório
2. Criar branch para feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit das mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para branch (`git push origin feature/nova-funcionalidade`)
5. Criar Pull Request

## 📞 Suporte

Para suporte técnico ou dúvidas sobre o sistema:

- **Email**: suporte@essencis.com
- **Documentação**: Consulte este README
- **Issues**: Use o sistema de issues do GitHub

## 📝 Licença

Este projeto é proprietário da Essencis e está sob licença comercial.

---

**Desenvolvido com ❤️ pela equipe Essencis usando tecnologia de ponta para gestão empresarial moderna.**