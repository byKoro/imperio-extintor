"""Testes específicos do mecanismo de migração e preservação de dados (Migração v2)."""

import sqlite3
import pytest
from db.connection import get_connection
from db.migrations import run_migrations, _migration_v1, _migration_v2, MIGRATIONS


def test_migracao_v2_preserva_dados_completos_e_condicoes():
    """Migração v2 preserva dados completos de pedidos, observações e condições comerciais."""
    conn = get_connection(":memory:")
    _migration_v1(conn)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO schema_migrations (version, description) VALUES (1, 'v1')")

    # Inserção de dados completos em v1
    cur.execute("INSERT INTO clientes (razao_social, cnpj) VALUES ('CLIENTE TESTE LTDA', '12.345.678/0001-99')")
    cliente_id = cur.lastrowid
    cur.execute("INSERT INTO lojas (cliente_id, codigo_loja, nome_site, cidade, uf, modelo_bandeira) VALUES (?, '01', 'SITE 1', 'SP', 'SP', 'MODA')", (cliente_id,))
    loja_id = cur.lastrowid

    cur.execute("""
        INSERT INTO pedidos (
            cliente_id, loja_id, numero_pedido, data_emissao, data_execucao, status,
            observacao_loja, observacoes, prazo_pagamento, forma_pagamento, prazo_entrega, texto_impostos
        ) VALUES (
            ?, ?, 'PED-999', '2026-10-13', '2026-10-14', 'EXECUTADO',
            'Obs interna loja antiga', 'Entregar somente pela manhã', '45 dias', 'Boleto bancário', '10 dias', 'Sem retenção'
        )
    """, (cliente_id, loja_id))
    pedido_id = cur.lastrowid
    conn.commit()

    # Aplica migração v2
    nova_versao = run_migrations(conn)
    assert nova_versao == 2

    # Verifica que observacao_loja não existe mais nas colunas de pedidos
    colunas = [col[1] for col in conn.execute("PRAGMA table_info(pedidos)").fetchall()]
    assert "observacao_loja" not in colunas
    assert "observacoes" in colunas

    # Verifica dados preservados
    row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    assert row["numero_pedido"] == "PED-999"
    assert row["data_emissao"] == "2026-10-13"
    assert row["data_execucao"] == "2026-10-14"
    assert row["status"] == "EXECUTADO"
    assert row["observacoes"] == "Entregar somente pela manhã"
    assert row["prazo_pagamento"] == "45 dias"
    assert row["forma_pagamento"] == "Boleto bancário"
    assert row["prazo_entrega"] == "10 dias"
    assert row["texto_impostos"] == "Sem retenção"

    conn.close()


def test_migracao_v2_preserva_itens_ajustes_faturamento_vinculados():
    """Itens de pedido, ajustes e faturamento_itens continuam válidos e vinculados após v2."""
    conn = get_connection(":memory:")
    _migration_v1(conn)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO schema_migrations (version, description) VALUES (1, 'v1')")

    cur.execute("INSERT INTO clientes (razao_social) VALUES ('CLIENTE VINCULOS')")
    cliente_id = cur.lastrowid
    cur.execute("INSERT INTO lojas (cliente_id, codigo_loja, nome_site, cidade, uf, modelo_bandeira) VALUES (?, 'L1', 'S1', 'SP', 'SP', 'B')", (cliente_id,))
    loja_id = cur.lastrowid

    cur.execute("""
        INSERT INTO pedidos (cliente_id, loja_id, numero_pedido, data_emissao, status)
        VALUES (?, ?, 'PED-VINC', '2026-10-13', 'EXECUTADO')
    """, (cliente_id, loja_id))
    pedido_id = cur.lastrowid

    # Vincula item de pedido
    cur.execute("""
        INSERT INTO itens_pedido (pedido_id, secao, descricao, quantidade, unidade, preco_unitario, valor_total)
        VALUES (?, 'SERVICO', 'Manutenção Extintor CO2', 3.0, 'SV', 80.0, 240.0)
    """, (pedido_id,))
    item_id = cur.lastrowid

    # Vincula ajuste
    cur.execute("""
        INSERT INTO ajustes (pedido_id, numero_ajuste, data_emissao, modo_geracao, status, valor_cobrado)
        VALUES (?, 'AJ-VINC-01', '2026-10-14', 'DIFERENCA', 'PENDENTE', 50.0)
    """, (pedido_id,))
    ajuste_id = cur.lastrowid

    # Vincula faturamento e item de faturamento
    cur.execute("INSERT INTO faturamentos (cliente_id, mes_referencia, ano_referencia) VALUES (?, 10, 2026)", (cliente_id,))
    fat_id = cur.lastrowid
    cur.execute("INSERT INTO faturamento_itens (faturamento_id, pedido_id, valor_cobrado) VALUES (?, ?, 240.0)", (fat_id, pedido_id))
    fat_item_id = cur.lastrowid
    conn.commit()

    # Executa migração v2
    run_migrations(conn)

    # Valida integridade referencial dos registros vinculados
    it = conn.execute("SELECT * FROM itens_pedido WHERE id = ?", (item_id,)).fetchone()
    assert it is not None
    assert it["pedido_id"] == pedido_id
    assert it["valor_total"] == 240.0

    aj = conn.execute("SELECT * FROM ajustes WHERE id = ?", (ajuste_id,)).fetchone()
    assert aj is not None
    assert aj["pedido_id"] == pedido_id
    assert aj["numero_ajuste"] == "AJ-VINC-01"

    fi = conn.execute("SELECT * FROM faturamento_itens WHERE id = ?", (fat_item_id,)).fetchone()
    assert fi is not None
    assert fi["pedido_id"] == pedido_id
    assert fi["faturamento_id"] == fat_id

    conn.close()


def test_migracao_v2_foreign_key_check():
    """Valida que foreign_key_check é lido e não possui violações após migração com dados íntegros."""
    conn = get_connection(":memory:")
    _migration_v1(conn)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO schema_migrations (version, description) VALUES (1, 'v1')")

    # Inserção de dados
    cur.execute("INSERT INTO clientes (razao_social) VALUES ('CLIENTE FK')")
    c_id = cur.lastrowid
    cur.execute("INSERT INTO lojas (cliente_id, codigo_loja, nome_site, cidade, uf, modelo_bandeira) VALUES (?, 'L1', 'S1', 'SP', 'SP', 'B')", (c_id,))
    l_id = cur.lastrowid
    cur.execute("INSERT INTO pedidos (cliente_id, loja_id, numero_pedido, data_emissao) VALUES (?, ?, 'PED-FK', '2026-10-13')", (c_id, l_id))
    p_id = cur.lastrowid
    cur.execute("INSERT INTO itens_pedido (pedido_id, secao, descricao, quantidade, unidade, preco_unitario, valor_total) VALUES (?, 'PECA', 'Manômetro', 1.0, 'UN', 10.0, 10.0)", (p_id,))
    conn.commit()

    # Executa migração
    run_migrations(conn)

    # Lê violações de FK
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert len(violations) == 0, f"Violações de integridade encontradas: {violations}"

    conn.close()


def test_migracao_v2_atomica_falha_insert_preserva_tabela_original():
    """Atomicidade: Se o INSERT falhar no meio, pedidos original continua intacto e FK volta a ON."""
    conn = get_connection(":memory:")
    _migration_v1(conn)
    cur = conn.cursor()

    cur.execute("INSERT INTO clientes (razao_social) VALUES ('CLIENTE ATOMICO')")
    c_id = cur.lastrowid
    cur.execute("INSERT INTO lojas (cliente_id, codigo_loja, nome_site, cidade, uf, modelo_bandeira) VALUES (?, 'L1', 'S1', 'SP', 'SP', 'B')", (c_id,))
    l_id = cur.lastrowid

    # Cria tabela pedidos permissiva temporariamente para simular dado que violará NOT NULL do novo schema
    conn.execute("DROP TABLE pedidos;")
    conn.execute("""
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            loja_id INTEGER NOT NULL REFERENCES lojas(id),
            numero_pedido TEXT, -- nulo para forçar falha no schema novo
            data_emissao TEXT NOT NULL,
            data_execucao TEXT,
            status TEXT NOT NULL DEFAULT 'ABERTO',
            observacao_loja TEXT,
            observacoes TEXT,
            prazo_pagamento TEXT,
            forma_pagamento TEXT,
            prazo_entrega TEXT,
            texto_impostos TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.execute("INSERT INTO pedidos (cliente_id, loja_id, numero_pedido, data_emissao, observacao_loja) VALUES (?, ?, NULL, '2026-10-13', 'DADO INTACTO');", (c_id, l_id))
    conn.commit()

    # A migração deve falhar devido a NOT NULL em numero_pedido
    with pytest.raises(sqlite3.IntegrityError):
        _migration_v2(conn)

    # Verifica que pedidos original continua com todos os dados e observacao_loja
    rows = conn.execute("SELECT * FROM pedidos").fetchall()
    assert len(rows) == 1
    assert rows[0]["observacao_loja"] == "DADO INTACTO"

    # Verifica que pedidos_new não ficou solta no banco
    tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "pedidos_new" not in tabelas

    # Verifica que foreign_keys voltou a ON
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk_status == 1

    conn.close()


def test_falha_foreign_key_check_faz_rollback_e_restaura_foreign_keys_on():
    """Quando foreign_key_check falha, a migração sofre rollback, dados são preservados e foreign_keys volta a ON."""
    conn = get_connection(":memory:")
    _migration_v1(conn)
    cur = conn.cursor()

    cur.execute("INSERT INTO clientes (razao_social) VALUES ('CLIENTE FK CORROMPIDO')")
    c_id = cur.lastrowid

    # Inserção com loja_id inexistente (desativando FK para simular dado legado corrompido)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("""
        INSERT INTO pedidos (cliente_id, loja_id, numero_pedido, data_emissao, observacao_loja)
        VALUES (?, 9999, 'PED-CORROMPIDO', '2026-10-13', 'OBS ORIGINAL');
    """, (c_id,))
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")

    # A migração deve detectar a violação no foreign_key_check e levantar IntegrityError
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _migration_v2(conn)
    assert "Violação de FK" in str(exc_info.value)

    # Verifica que o banco não ficou parcialmente migrado: pedidos ainda tem observacao_loja
    cols = [r[1] for r in conn.execute("PRAGMA table_info(pedidos)").fetchall()]
    assert "observacao_loja" in cols

    # Verifica que pedidos_new foi descartada
    tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "pedidos_new" not in tabelas

    # Verifica que os dados originais foram preservados
    row = conn.execute("SELECT * FROM pedidos WHERE numero_pedido = 'PED-CORROMPIDO'").fetchone()
    assert row is not None
    assert row["observacao_loja"] == "OBS ORIGINAL"

    # Verifica que foreign_keys voltou a ON
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk_status == 1

    conn.close()


def test_runner_nao_reexecuta_migracoes_ja_aplicadas_e_suporta_pedidos_new_residual():
    """O runner não reexecuta migrações já aplicadas e a migração é segura contra pedidos_new residual."""
    conn = get_connection(":memory:")
    v1 = run_migrations(conn)
    assert v1 == 2

    # Segunda chamada: runner verifica versão e não reexecuta
    v2 = run_migrations(conn)
    assert v2 == 2

    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    assert row[0] == 2

    # Segurança: cria tabela residual pedidos_new para simular aborto prévio e testa reexecução direta de _migration_v2
    conn.execute("CREATE TABLE IF NOT EXISTS pedidos_new (id INTEGER PRIMARY KEY);")
    conn.commit()
    # _migration_v2 possui DROP TABLE IF EXISTS pedidos_new, logo não deve falhar
    _migration_v2(conn)

    conn.close()


def test_banco_novo_e_banco_migrado_mesmo_sqlite_master():
    """Banco novo criado do schema.sql e banco migrado possuem estrutura idêntica para pedidos e schema_migrations."""
    # 1. Banco novo
    conn_novo = get_connection(":memory:")
    run_migrations(conn_novo)

    # 2. Banco migrado (v1 -> v2)
    conn_migrado = get_connection(":memory:")
    _migration_v1(conn_migrado)
    conn_migrado.execute("INSERT OR REPLACE INTO schema_migrations (version, description) VALUES (1, 'v1')")
    conn_migrado.commit()
    run_migrations(conn_migrado)

    # Compara colunas, tipos e nullability de pedidos via PRAGMA table_info
    cols_novo = [(r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"]) for r in conn_novo.execute("PRAGMA table_info(pedidos)").fetchall()]
    cols_migrado = [(r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"]) for r in conn_migrado.execute("PRAGMA table_info(pedidos)").fetchall()]
    assert cols_novo == cols_migrado

    # Compara chaves estrangeiras de pedidos via PRAGMA foreign_key_list
    fks_novo = [(r["id"], r["table"], r["from"], r["to"], r["on_update"], r["on_delete"]) for r in conn_novo.execute("PRAGMA foreign_key_list(pedidos)").fetchall()]
    fks_migrado = [(r["id"], r["table"], r["from"], r["to"], r["on_update"], r["on_delete"]) for r in conn_migrado.execute("PRAGMA foreign_key_list(pedidos)").fetchall()]
    assert sorted(fks_novo) == sorted(fks_migrado)

    # Compara índices de pedidos via PRAGMA index_list
    idx_novo = sorted([r["name"] for r in conn_novo.execute("PRAGMA index_list(pedidos)").fetchall()])
    idx_migrado = sorted([r["name"] for r in conn_migrado.execute("PRAGMA index_list(pedidos)").fetchall()])
    assert idx_novo == idx_migrado

    # Compara estrutura de schema_migrations
    sm_cols_novo = [(r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"]) for r in conn_novo.execute("PRAGMA table_info(schema_migrations)").fetchall()]
    sm_cols_migrado = [(r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"]) for r in conn_migrado.execute("PRAGMA table_info(schema_migrations)").fetchall()]
    assert sm_cols_novo == sm_cols_migrado

    # Compara versão máxima em schema_migrations (ambos devem estar em 2)
    max_v_novo = conn_novo.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    max_v_migrado = conn_migrado.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    assert max_v_novo == 2
    assert max_v_migrado == 2

    conn_novo.close()
    conn_migrado.close()
