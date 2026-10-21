-- Schema inicial do Sistema Imperio Extintores
-- SQLite 3

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    cnpj TEXT,
    inscricao_estadual TEXT,
    endereco TEXT,
    telefone TEXT,
    email TEXT,
    contato TEXT,
    prazo_pagamento TEXT DEFAULT '30 dias',
    forma_pagamento TEXT DEFAULT 'Transferência bancária',
    prazo_entrega TEXT DEFAULT '7 dias úteis',
    texto_impostos TEXT DEFAULT 'Impostos inclusos',
    ativo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS lojas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    codigo_loja TEXT NOT NULL,
    nome_site TEXT NOT NULL,
    cidade TEXT NOT NULL,
    uf TEXT NOT NULL,
    modelo_bandeira TEXT NOT NULL,
    vencimento TEXT, -- Data armazenada como 'YYYY-MM-01', exibida como MM/YYYY
    observacao TEXT,
    notificada INTEGER NOT NULL DEFAULT 0, -- Chave de alerta (0 = Não, 1 = Sim)
    ativo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT uq_loja_cliente_codigo UNIQUE (cliente_id, codigo_loja)
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    categoria TEXT,
    tipo TEXT NOT NULL, -- 'SERVICO' ou 'PECA'
    unidade TEXT NOT NULL DEFAULT 'UN', -- 'SV' ou 'UN'
    capacidade TEXT,
    preco_padrao REAL NOT NULL DEFAULT 0.0,
    ativo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS precos_cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    preco REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT uq_preco_cliente_produto UNIQUE (cliente_id, produto_id)
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    loja_id INTEGER NOT NULL REFERENCES lojas(id) ON DELETE RESTRICT,
    numero_pedido TEXT NOT NULL, -- Digitado pelo usuário
    data_emissao TEXT NOT NULL,  -- YYYY-MM-DD
    data_execucao TEXT,          -- YYYY-MM-DD (obrigatória para status EXECUTADO)
    status TEXT NOT NULL DEFAULT 'ABERTO', -- 'ABERTO', 'EXECUTADO', 'FATURADO', 'PAGO'
    observacoes TEXT,
    prazo_pagamento TEXT,
    forma_pagamento TEXT,
    prazo_entrega TEXT,
    texto_impostos TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT uq_pedido_cliente_numero UNIQUE (cliente_id, numero_pedido)
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE SET NULL,
    secao TEXT NOT NULL,         -- 'SERVICO' ou 'PECA'
    descricao TEXT NOT NULL,
    quantidade REAL NOT NULL DEFAULT 0.0,
    unidade TEXT NOT NULL,       -- 'SV' ou 'UN'
    preco_unitario REAL NOT NULL DEFAULT 0.0, -- Gravado no momento do lançamento
    valor_total REAL NOT NULL DEFAULT 0.0,    -- quantidade * preco_unitario
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS faturamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    mes_referencia INTEGER NOT NULL, -- 1 a 12
    ano_referencia INTEGER NOT NULL, -- YYYY
    data_fechamento TEXT,
    total_geral REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'ABERTO', -- 'ABERTO', 'FECHADO'
    observacoes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT uq_faturamento_cliente_mes_ano UNIQUE (cliente_id, mes_referencia, ano_referencia)
);

CREATE TABLE IF NOT EXISTS ajustes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE RESTRICT,
    numero_ajuste TEXT NOT NULL,
    data_emissao TEXT NOT NULL,
    data_execucao TEXT,
    modo_geracao TEXT NOT NULL, -- 'DIFERENCA' ou 'INCREMENTADO'
    status TEXT NOT NULL DEFAULT 'PENDENTE', -- 'PENDENTE', 'FATURADO'
    faturamento_id INTEGER REFERENCES faturamentos(id) ON DELETE SET NULL,
    valor_cobrado REAL NOT NULL DEFAULT 0.0,
    observacoes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CONSTRAINT uq_ajuste_pedido_numero UNIQUE (pedido_id, numero_ajuste)
);

CREATE TABLE IF NOT EXISTS itens_ajuste (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ajuste_id INTEGER NOT NULL REFERENCES ajustes(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE SET NULL,
    secao TEXT NOT NULL,
    descricao TEXT NOT NULL,
    quantidade REAL NOT NULL DEFAULT 0.0,
    unidade TEXT NOT NULL,
    preco_unitario REAL NOT NULL DEFAULT 0.0,
    valor_total REAL NOT NULL DEFAULT 0.0,
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS faturamento_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faturamento_id INTEGER NOT NULL REFERENCES faturamentos(id) ON DELETE CASCADE,
    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE RESTRICT,
    ajuste_id INTEGER REFERENCES ajustes(id) ON DELETE RESTRICT,
    valor_cobrado REAL NOT NULL DEFAULT 0.0,
    CONSTRAINT chk_faturamento_item_origem CHECK (
        (pedido_id IS NOT NULL AND ajuste_id IS NULL) OR
        (pedido_id IS NULL AND ajuste_id IS NOT NULL)
    ),
    CONSTRAINT uq_faturamento_pedido UNIQUE (faturamento_id, pedido_id),
    CONSTRAINT uq_faturamento_ajuste UNIQUE (faturamento_id, ajuste_id)
);

-- Tabela de controle de versão das migrações
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    description TEXT
);

-- Índices para buscas rápidas
CREATE INDEX IF NOT EXISTS idx_lojas_cliente ON lojas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_lojas_vencimento ON lojas(vencimento);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_loja ON pedidos(loja_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_itens_pedido_pedido ON itens_pedido(pedido_id);
CREATE INDEX IF NOT EXISTS idx_ajustes_pedido ON ajustes(pedido_id);
CREATE INDEX IF NOT EXISTS idx_itens_ajuste_ajuste ON itens_ajuste(ajuste_id);
