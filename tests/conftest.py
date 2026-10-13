"""Fixtures de testes com banco SQLite em memória e dados fictícios."""

import pytest
import sqlite3
from db.connection import get_connection
from db.migrations import run_migrations
from db.models import Cliente, Loja, Produto
from db.repositories import criar_cliente, criar_loja, criar_produto


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Retorna uma conexão com banco SQLite em memória com todas as migrações aplicadas."""
    conexao = get_connection(":memory:")
    run_migrations(conexao)
    yield conexao
    conexao.close()


@pytest.fixture
def dados_ficticios(conn: sqlite3.Connection):
    """Cria entidades fictícias de teste para uso nos testes de regras."""
    # Cliente fictício
    cliente = Cliente(
        razao_social="EMPRESA FICTICIA EXEMPLO LTDA",
        nome_fantasia="FICTICIA EXEMPLO",
        cnpj="00.123.456/0001-99",
        inscricao_estadual="123.456.789.000",
        endereco="Av. Teste, 100, São Paulo - SP",
        telefone="(11) 99999-0000",
        email="contato@ficticia.exemplo.com",
        contato="Gerente Teste",
        prazo_pagamento="30 dias",
        forma_pagamento="Depósito bancário",
        prazo_entrega="7 dias úteis",
        texto_impostos="Impostos inclusos",
    )
    cliente_id = criar_cliente(conn, cliente)

    # Loja fictícia
    loja = Loja(
        cliente_id=cliente_id,
        codigo_loja="101",
        nome_site="SHOPPING TESTE NORTE",
        cidade="São Paulo",
        uf="SP",
        modelo_bandeira="MODA",
        vencimento="2026-12-01",
        observacao="ENCAIXE DE ROTEIRO",
        notificada=0,
    )
    loja_id = criar_loja(conn, loja)

    # Produtos fictícios (Serviço e Peça)
    p_servico = Produto(
        nome="RECARGA EXTINTOR AP 10L TESTE",
        categoria="Extintores",
        tipo="SERVICO",
        unidade="SV",
        capacidade="10 L",
        preco_padrao=50.0,
    )
    prod_servico_id = criar_produto(conn, p_servico)

    p_peca = Produto(
        nome="MANOMETRO EXTINTOR TESTE",
        categoria="Peças",
        tipo="PECA",
        unidade="UN",
        capacidade="-",
        preco_padrao=15.0,
    )
    prod_peca_id = criar_produto(conn, p_peca)

    conn.commit()

    return {
        "cliente_id": cliente_id,
        "loja_id": loja_id,
        "prod_servico_id": prod_servico_id,
        "prod_peca_id": prod_peca_id,
    }
