"""Testes das migrações do banco de dados e restrições de integridade."""

import pytest
import sqlite3
from db.connection import get_connection
from db.migrations import run_migrations
from db.models import Cliente, Loja, Produto, Pedido
from db.repositories import criar_cliente, criar_loja, criar_produto, criar_pedido


def test_migracao_inicial_e_idempotencia():
    """Testa criação do schema e garantia de idempotência do script de migração."""
    conn = get_connection(":memory:")
    
    # 1. Primeira execução: deve aplicar versão 2
    v1 = run_migrations(conn)
    assert v1 == 2

    # 2. Segunda execução: não deve falhar e deve manter versão 2
    v2 = run_migrations(conn)
    assert v2 == 2
    
    conn.close()


def test_restricao_unique_loja_por_cliente(conn: sqlite3.Connection):
    """Regra 3: Código de loja é único dentro do cliente."""
    c1 = criar_cliente(conn, Cliente(razao_social="CLIENTE 1"))
    c2 = criar_cliente(conn, Cliente(razao_social="CLIENTE 2"))

    # Cria loja código '10' no cliente 1
    criar_loja(conn, Loja(cliente_id=c1, codigo_loja="10", nome_site="Site A", cidade="SP", uf="SP", modelo_bandeira="MODA"))
    conn.commit()

    # Tentar criar mesma loja '10' no cliente 1 deve falhar
    with pytest.raises(sqlite3.IntegrityError):
        criar_loja(conn, Loja(cliente_id=c1, codigo_loja="10", nome_site="Site Duplicado", cidade="SP", uf="SP", modelo_bandeira="MODA"))

    # Mas mesma loja '10' em outro cliente (cliente 2) deve ser permitida
    id_c2 = criar_loja(conn, Loja(cliente_id=c2, codigo_loja="10", nome_site="Site B", cidade="RJ", uf="RJ", modelo_bandeira="CASA"))
    assert id_c2 is not None


def test_restricao_unique_numero_pedido_por_cliente(conn: sqlite3.Connection):
    """Regra 5.1: O número do pedido é digitado e único para o mesmo cliente."""
    c1 = criar_cliente(conn, Cliente(razao_social="CLIENTE 1"))
    c2 = criar_cliente(conn, Cliente(razao_social="CLIENTE 2"))
    loja1 = criar_loja(conn, Loja(cliente_id=c1, codigo_loja="1", nome_site="S1", cidade="SP", uf="SP", modelo_bandeira="MODA"))
    loja2 = criar_loja(conn, Loja(cliente_id=c2, codigo_loja="1", nome_site="S2", cidade="RJ", uf="RJ", modelo_bandeira="MODA"))

    criar_pedido(conn, Pedido(cliente_id=c1, loja_id=loja1, numero_pedido="2026100", data_emissao="2026-10-13"))
    conn.commit()

    # Mesmo número para o mesmo cliente deve falhar
    with pytest.raises(sqlite3.IntegrityError):
        criar_pedido(conn, Pedido(cliente_id=c1, loja_id=loja1, numero_pedido="2026100", data_emissao="2026-10-13"))

    # Mesmo número para cliente diferente deve ser aceito
    ped_c2 = criar_pedido(conn, Pedido(cliente_id=c2, loja_id=loja2, numero_pedido="2026100", data_emissao="2026-10-13"))
    assert ped_c2 is not None


def test_restricao_unique_nome_produto(conn: sqlite3.Connection):
    """Regra 4: Não podem existir dois produtos com o mesmo nome."""
    criar_produto(conn, Produto(nome="EXTINTOR ABC 4KG TESTE", tipo="SERVICO", preco_padrao=50.0))
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        criar_produto(conn, Produto(nome="EXTINTOR ABC 4KG TESTE", tipo="SERVICO", preco_padrao=60.0))
