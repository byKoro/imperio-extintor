"""Mecanismo simples e versionado de migração do banco de dados SQLite."""

import sqlite3
from pathlib import Path
from typing import Dict, Callable

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _migration_v1(conn: sqlite3.Connection) -> None:
    """Migração inicial legada (v1): cria schema inicial com observacao_loja."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    # Se o schema.sql já estiver no estado v2 (sem observacao_loja), v1 injeta para simular o estado inicial
    if "observacao_loja" not in sql:
        sql = sql.replace(
            "    status TEXT NOT NULL DEFAULT 'ABERTO', -- 'ABERTO', 'EXECUTADO', 'FATURADO', 'PAGO'\n",
            "    status TEXT NOT NULL DEFAULT 'ABERTO', -- 'ABERTO', 'EXECUTADO', 'FATURADO', 'PAGO'\n    observacao_loja TEXT,\n"
        )
    conn.executescript(sql)


def _migration_v2(conn: sqlite3.Connection) -> None:
    """Migração v2: Remove observacao_loja de pedidos via recriação de tabela.
    
    Usa o procedimento seguro de recriação de tabela em SQLite:
    1. Comita qualquer transação pendente e desativa foreign keys fora de transação;
    2. Cria pedidos_new com a mesma estrutura e constraints, exceto observacao_loja;
    3. Copia todos os dados existentes preservando todas as colunas;
    4. Remove a tabela antiga pedidos;
    5. Renomeia pedidos_new para pedidos;
    6. Recria os índices existentes (idx_pedidos_cliente, idx_pedidos_loja, idx_pedidos_status);
    7. Valida integridade referencial via PRAGMA foreign_key_check;
    8. Reativa PRAGMA foreign_keys = ON fora de transação.
    """
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF;")

    script = """
    BEGIN TRANSACTION;

    DROP TABLE IF EXISTS pedidos_new;

    CREATE TABLE pedidos_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        loja_id INTEGER NOT NULL REFERENCES lojas(id) ON DELETE RESTRICT,
        numero_pedido TEXT NOT NULL,
        data_emissao TEXT NOT NULL,
        data_execucao TEXT,
        status TEXT NOT NULL DEFAULT 'ABERTO',
        observacoes TEXT,
        prazo_pagamento TEXT,
        forma_pagamento TEXT,
        prazo_entrega TEXT,
        texto_impostos TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        CONSTRAINT uq_pedido_cliente_numero UNIQUE (cliente_id, numero_pedido)
    );

    INSERT INTO pedidos_new (
        id, cliente_id, loja_id, numero_pedido, data_emissao, data_execucao,
        status, observacoes, prazo_pagamento, forma_pagamento, prazo_entrega,
        texto_impostos, created_at
    )
    SELECT
        id, cliente_id, loja_id, numero_pedido, data_emissao, data_execucao,
        status, observacoes, prazo_pagamento, forma_pagamento, prazo_entrega,
        texto_impostos, created_at
    FROM pedidos;

    DROP TABLE pedidos;

    ALTER TABLE pedidos_new RENAME TO pedidos;

    CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id);
    CREATE INDEX IF NOT EXISTS idx_pedidos_loja ON pedidos(loja_id);
    CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
    """

    try:
        conn.executescript(script)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_key_check;")
        violations = cur.fetchall()
        if violations:
            conn.execute("ROLLBACK;")
            raise sqlite3.IntegrityError(f"Violação de FK após migração v2: {violations}")
        conn.execute("COMMIT;")
    except Exception:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")


MIGRATIONS: Dict[int, tuple[str, Callable[[sqlite3.Connection], None]]] = {
    1: ("Criação inicial do schema (clientes, lojas, produtos, pedidos, faturamentos, ajustes)", _migration_v1),
    2: ("Remove coluna observacao_loja de pedidos via recriação da tabela", _migration_v2),
}


def run_migrations(conn: sqlite3.Connection) -> int:
    """Executa migrações no banco de dados SQLite.
    
    - Para bancos novos (sem tabela clientes e sem histórico de migrações),
      aplica o schema.sql (estado final) diretamente e registra a versão mais recente.
    - Para bancos existentes, executa as migrações incrementais pendentes em ordem.
    
    Retorna a versão atual do banco de dados após a execução.
    """
    cursor = conn.cursor()

    # Cria tabela de migrações se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            description TEXT
        )
    """)
    conn.commit()

    cursor.execute("SELECT MAX(version) FROM schema_migrations")
    row = cursor.fetchone()
    current_version = row[0] if (row and row[0] is not None) else 0

    latest_version = max(MIGRATIONS.keys())

    # Verifica se o banco é completamente novo (sem tabela clientes)
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='clientes'")
    tabela_clientes_existe = cursor.fetchone()[0] > 0

    if not tabela_clientes_existe and current_version == 0:
        # Banco novo: inicializa a partir do schema.sql (estado final) e marca versão mais recente
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        cursor.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
            (latest_version, f"Criação inicial direta a partir do schema.sql final (v{latest_version})")
        )
        conn.commit()
        return latest_version

    # Banco existente: aplica migrações incrementais pendentes
    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            desc, migration_func = MIGRATIONS[version]
            migration_func(conn)
            cursor.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, desc)
            )
            conn.commit()
            current_version = version

    return current_version
