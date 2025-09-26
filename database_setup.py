import sqlite3
import pandas as pd
import datetime
import os

# =============================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS SQLITE
# =============================================================================

def create_database():
    """Cria banco de dados SQLite com todas as tabelas necessárias"""
    
    # Nome do banco de dados
    db_name = "gestao_empresarial.db"
    
    # Conectar ao banco
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            perfil TEXT NOT NULL,
            departamento TEXT,
            ativo BOOLEAN DEFAULT 1,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            ultimo_acesso DATETIME
        )
    ''')
    
    # Tabela de Módulos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS modulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            icone TEXT,
            categoria TEXT,
            ativo BOOLEAN DEFAULT 1,
            ordem INTEGER DEFAULT 0
        )
    ''')
    
    # Tabela de Permissões
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            modulo_id INTEGER,
            permissao TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (modulo_id) REFERENCES modulos (id)
        )
    ''')
    
    # Tabela de Fornecedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT NOT NULL,
            nome_fantasia TEXT,
            cnpj TEXT UNIQUE,
            inscricao_estadual TEXT,
            endereco TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            telefone TEXT,
            email TEXT,
            contato_nome TEXT,
            status TEXT DEFAULT 'Ativo',
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
            observacoes TEXT
        )
    ''')
    
    # Tabela de Materiais/Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            unidade_medida TEXT,
            categoria TEXT,
            subcategoria TEXT,
            valor_unitario DECIMAL(15,2),
            estoque_minimo INTEGER DEFAULT 0,
            estoque_atual INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT 1,
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Pedidos de Compra
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_pedido TEXT UNIQUE NOT NULL,
            fornecedor_id INTEGER,
            solicitante TEXT,
            departamento TEXT,
            filial TEXT,
            data_pedido DATETIME,
            data_aprovacao DATETIME,
            data_entrega DATETIME,
            previsao_entrega DATETIME,
            status TEXT DEFAULT 'Pendente',
            valor_total DECIMAL(15,2),
            observacoes TEXT,
            aprovado_por TEXT,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id)
        )
    ''')
    
    # Tabela de Itens do Pedido
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            material_id INTEGER,
            quantidade DECIMAL(15,3),
            valor_unitario DECIMAL(15,2),
            valor_total DECIMAL(15,2),
            quantidade_entregue DECIMAL(15,3) DEFAULT 0,
            FOREIGN KEY (pedido_id) REFERENCES pedidos_compra (id),
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')
    
    # Tabela de Notas Fiscais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_nf TEXT NOT NULL,
            serie TEXT,
            fornecedor_id INTEGER,
            pedido_id INTEGER,
            data_emissao DATETIME,
            data_vencimento DATETIME,
            valor_total DECIMAL(15,2),
            valor_icms DECIMAL(15,2),
            valor_ipi DECIMAL(15,2),
            valor_iss DECIMAL(15,2),
            status TEXT DEFAULT 'Pendente',
            chave_acesso TEXT,
            observacoes TEXT,
            data_pagamento DATETIME,
            juros DECIMAL(15,2) DEFAULT 0,
            multa DECIMAL(15,2) DEFAULT 0,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id),
            FOREIGN KEY (pedido_id) REFERENCES pedidos_compra (id)
        )
    ''')
    
    # Tabela de Movimentações de Estoque
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER,
            tipo_movimentacao TEXT, -- 'Entrada', 'Saída', 'Ajuste'
            quantidade DECIMAL(15,3),
            valor_unitario DECIMAL(15,2),
            data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            documento_origem TEXT,
            usuario_responsavel TEXT,
            observacoes TEXT,
            FOREIGN KEY (material_id) REFERENCES materiais (id)
        )
    ''')
    
    # Tabela de Contratos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_contrato TEXT UNIQUE NOT NULL,
            fornecedor_id INTEGER,
            objeto TEXT,
            valor_total DECIMAL(15,2),
            data_inicio DATETIME,
            data_fim DATETIME,
            data_renovacao DATETIME,
            status TEXT DEFAULT 'Ativo',
            tipo_contrato TEXT,
            observacoes TEXT,
            responsavel TEXT,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id)
        )
    ''')
    
    # Tabela de Reembolsos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reembolsos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            descricao TEXT NOT NULL,
            categoria TEXT,
            valor DECIMAL(15,2),
            data_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_aprovacao DATETIME,
            data_pagamento DATETIME,
            status TEXT DEFAULT 'Pendente',
            comprovante_path TEXT,
            observacoes_solicitante TEXT,
            observacoes_aprovador TEXT,
            aprovado_por TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabela de Logs de Auditoria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tabela_afetada TEXT,
            operacao TEXT, -- 'INSERT', 'UPDATE', 'DELETE'
            registro_id INTEGER,
            dados_anteriores TEXT,
            dados_novos TEXT,
            data_operacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Inserir dados iniciais
    insert_initial_data(cursor)
    
    # Commit e fechar
    conn.commit()
    conn.close()
    
    print(f"✅ Banco de dados '{db_name}' criado com sucesso!")
    return db_name

def insert_initial_data(cursor):
    """Insere dados iniciais no banco"""
    
    # Usuários iniciais
    usuarios_iniciais = [
        ('admin@essencis.com', 'admin123', 'Administrador', 'admin', 'TI'),
        ('comprador@essencis.com', 'comprador123', 'João Comprador', 'comprador', 'Compras'),
        ('financeiro@essencis.com', 'financeiro123', 'Maria Financeiro', 'financeiro', 'Financeiro'),
        ('almoxarife@essencis.com', 'almoxarife123', 'Pedro Almoxarife', 'almoxarife', 'Almoxarifado'),
        ('gestor@essencis.com', 'gestor123', 'Ana Gestora', 'gestor', 'Gestão')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO usuarios (email, senha, nome, perfil, departamento)
        VALUES (?, ?, ?, ?, ?)
    ''', usuarios_iniciais)
    
    # Módulos do sistema
    modulos_iniciais = [
        ('compras', 'Gestão de Compras', 'Sistema completo de compras com aprovações', '🛒', 'Operacional', 1),
        ('consulta', 'Consulta de Compras', 'Consulta rápida de pedidos e status', '🔍', 'Consulta', 2),
        ('fornecedores', 'Carteira de Fornecedores', 'Gestão completa de fornecedores', '🏪', 'Operacional', 3),
        ('estoque', 'Gestão de Estoque', 'Controle de estoque e movimentações', '📦', 'Operacional', 4),
        ('fiscal', 'Gestão de Notas Fiscais', 'Controle de NFs e pagamentos', '📋', 'Financeiro', 5),
        ('reembolso', 'Sistema de Reembolsos', 'Gestão de reembolsos e aprovações', '💰', 'Financeiro', 6),
        ('contratos', 'Gestão de Contratos', 'Controle de contratos e renovações', '📑', 'Jurídico', 7),
        ('dashboard', 'Dashboard Executivo', 'Painéis e métricas gerenciais', '📊', 'Gerencial', 8)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO modulos (codigo, nome, descricao, icone, categoria, ordem)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', modulos_iniciais)
    
    # Fornecedores de exemplo
    fornecedores_exemplo = [
        ('Fornecedor A Ltda', 'Fornecedor A', '12.345.678/0001-90', '123.456.789.123', 'Rua A, 123', 'São Paulo', 'SP', '01234-567', '(11) 1234-5678', 'contato@fornecedora.com', 'João Silva', 'Ativo'),
        ('Empresa B S.A.', 'Empresa B', '98.765.432/0001-10', '987.654.321.987', 'Av. B, 456', 'Rio de Janeiro', 'RJ', '20123-456', '(21) 9876-5432', 'vendas@empresab.com', 'Maria Santos', 'Ativo'),
        ('Comércio C Eireli', 'Comércio C', '11.223.344/0001-55', '111.222.333.444', 'Rua C, 789', 'Belo Horizonte', 'MG', '30123-789', '(31) 1122-3344', 'comercial@comercioc.com', 'Pedro Costa', 'Ativo')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO fornecedores 
        (razao_social, nome_fantasia, cnpj, inscricao_estadual, endereco, cidade, estado, cep, telefone, email, contato_nome, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', fornecedores_exemplo)
    
    # Materiais de exemplo
    materiais_exemplo = [
        ('MAT001', 'Papel A4 - 500 folhas', 'PC', 'Escritório', 'Papelaria', 15.90),
        ('MAT002', 'Caneta Esferográfica Azul', 'UN', 'Escritório', 'Papelaria', 2.50),
        ('MAT003', 'Toner Impressora HP', 'UN', 'Informática', 'Suprimentos', 89.90),
        ('MAT004', 'Monitor LED 24"', 'UN', 'Informática', 'Equipamentos', 450.00),
        ('MAT005', 'Mesa de Escritório', 'UN', 'Móveis', 'Mobiliário', 280.00)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO materiais (codigo, descricao, unidade_medida, categoria, subcategoria, valor_unitario)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', materiais_exemplo)

def get_connection():
    """Retorna conexão com o banco de dados"""
    db_name = "gestao_empresarial.db"
    if not os.path.exists(db_name):
        create_database()
    return sqlite3.connect(db_name)

def execute_query(query, params=None):
    """Executa uma query no banco de dados"""
    conn = get_connection()
    try:
        if params:
            result = pd.read_sql_query(query, conn, params=params)
        else:
            result = pd.read_sql_query(query, conn)
        return result
    finally:
        conn.close()

def execute_command(command, params=None):
    """Executa um comando no banco (INSERT, UPDATE, DELETE)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(command, params)
        else:
            cursor.execute(command)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

# Funções de conveniência para cada tabela
def get_usuarios():
    """Retorna todos os usuários"""
    return execute_query("SELECT * FROM usuarios WHERE ativo = 1")

def get_fornecedores():
    """Retorna todos os fornecedores ativos"""
    return execute_query("SELECT * FROM fornecedores WHERE status = 'Ativo'")

def get_materiais():
    """Retorna todos os materiais ativos"""
    return execute_query("SELECT * FROM materiais WHERE ativo = 1")

def get_pedidos_compra():
    """Retorna pedidos de compra com dados do fornecedor"""
    query = '''
        SELECT p.*, f.razao_social as fornecedor_nome
        FROM pedidos_compra p
        LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
        ORDER BY p.data_pedido DESC
    '''
    return execute_query(query)

def get_notas_fiscais():
    """Retorna notas fiscais com dados do fornecedor"""
    query = '''
        SELECT n.*, f.razao_social as fornecedor_nome
        FROM notas_fiscais n
        LEFT JOIN fornecedores f ON n.fornecedor_id = f.id
        ORDER BY n.data_emissao DESC
    '''
    return execute_query(query)

if __name__ == "__main__":
    # Criar banco de dados se executado diretamente
    create_database()
    
    # Testar algumas consultas
    print("\n📊 Testando consultas:")
    print(f"Usuários: {len(get_usuarios())} registros")
    print(f"Fornecedores: {len(get_fornecedores())} registros")
    print(f"Materiais: {len(get_materiais())} registros")
    
    print("\n✅ Setup do banco concluído!")