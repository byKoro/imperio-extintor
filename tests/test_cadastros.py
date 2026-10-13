"""Testes específicos da Fase 2 — Cadastros.

Cobre:
1. Unicidade de código de loja por cliente.
2. Unicidade de nome de produto.
3. Sobreposição de preço por cliente (tabela própria vs fallback para padrão).
4. Histórico de atendimentos da loja (distinção entre faturado e pendente).
"""

import pytest
import sqlite3
from db.models import Cliente, Loja, Produto, Pedido, ItemPedido
from db.repositories import (
    criar_cliente, criar_loja, criar_produto, criar_pedido,
    adicionar_item_pedido, definir_preco_cliente, remover_preco_cliente,
    obter_preco_produto_para_cliente, listar_precos_por_cliente,
    obter_historico_atendimentos_loja, buscar_loja_por_id
)
from app.core.constants import (
    STATUS_PEDIDO_ABERTO, STATUS_PEDIDO_EXECUTADO, STATUS_PEDIDO_FATURADO,
    SECAO_SERVICOS
)


def test_unicidade_codigo_loja_por_cliente(conn: sqlite3.Connection):
    """Garante que uma loja tenha código único dentro do mesmo cliente, mas permite em clientes distintos."""
    c1 = criar_cliente(conn, Cliente(razao_social="CLIENTE FICTICIO 1"))
    c2 = criar_cliente(conn, Cliente(razao_social="CLIENTE FICTICIO 2"))

    # Cria loja no cliente 1
    loja1 = Loja(
        cliente_id=c1,
        codigo_loja="LJ-001",
        nome_site="SHOPPING TESTE A",
        cidade="São Paulo",
        uf="SP",
        modelo_bandeira="MODA"
    )
    criar_loja(conn, loja1)
    conn.commit()

    # Tentativa de duplicar o código 'LJ-001' no cliente 1 deve falhar
    loja_duplicada = Loja(
        cliente_id=c1,
        codigo_loja="LJ-001",
        nome_site="SHOPPING TESTE B",
        cidade="Campinas",
        uf="SP",
        modelo_bandeira="CASA"
    )
    with pytest.raises(sqlite3.IntegrityError):
        criar_loja(conn, loja_duplicada)

    # Mas o mesmo código 'LJ-001' no cliente 2 deve ser aceito normalmente
    loja_outro_cliente = Loja(
        cliente_id=c2,
        codigo_loja="LJ-001",
        nome_site="OUTLET TESTE C",
        cidade="Curitiba",
        uf="PR",
        modelo_bandeira="CARTERS"
    )
    id_c2 = criar_loja(conn, loja_outro_cliente)
    assert id_c2 is not None


def test_unicidade_nome_produto(conn: sqlite3.Connection):
    """Garante que não existam dois produtos cadastrados com o mesmo nome."""
    p1 = Produto(
        nome="EXTINTOR TESTE PQS 4KG",
        tipo="SERVICO",
        unidade="SV",
        preco_padrao=60.0
    )
    criar_produto(conn, p1)
    conn.commit()

    p_duplicado = Produto(
        nome="EXTINTOR TESTE PQS 4KG",
        tipo="SERVICO",
        unidade="SV",
        preco_padrao=75.0
    )
    with pytest.raises(sqlite3.IntegrityError):
        criar_produto(conn, p_duplicado)


def test_sobreposicao_preco_por_cliente(conn: sqlite3.Connection):
    """Valida a prioridade de precos_cliente sobre o preço padrão e o fallback."""
    cliente_id = criar_cliente(conn, Cliente(razao_social="CLIENTE COM TABELA PROPRIA"))
    
    prod_a = criar_produto(conn, Produto(nome="SERVICO TESTE A", tipo="SERVICO", preco_padrao=100.0))
    prod_b = criar_produto(conn, Produto(nome="SERVICO TESTE B", tipo="SERVICO", preco_padrao=50.0))
    conn.commit()

    # Antes de configurar customização: ambos usam o preço padrão
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_a) == 100.0
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_b) == 50.0

    # Define preço especial para o produto A (R$ 80.00)
    definir_preco_cliente(conn, cliente_id, prod_a, 80.0)
    conn.commit()

    # Produto A retorna o preço customizado
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_a) == 80.0
    # Produto B mantém o fallback para o padrão
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_b) == 50.0

    # Verifica na listagem de preços
    tabela = listar_precos_por_cliente(conn, cliente_id)
    mapa = {item["produto_id"]: item for item in tabela}
    
    assert mapa[prod_a]["preco_padrao"] == 100.0
    assert mapa[prod_a]["preco_cliente"] == 80.0
    assert mapa[prod_a]["preco_efetivo"] == 80.0
    assert mapa[prod_a]["tem_personalizacao"] is True

    assert mapa[prod_b]["preco_padrao"] == 50.0
    assert mapa[prod_b]["preco_cliente"] is None
    assert mapa[prod_b]["preco_efetivo"] == 50.0
    assert mapa[prod_b]["tem_personalizacao"] is False

    # Remove personalização de A e confirma retorno ao preço padrão
    remover_preco_cliente(conn, cliente_id, prod_a)
    conn.commit()
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_a) == 100.0


def test_historico_atendimentos_loja(conn: sqlite3.Connection):
    """Regra 3: Uma loja só é considerada atendida depois que o atendimento é faturado.
    
    Atendimentos ainda não faturados aparecem como pendentes.
    Confirma também que pedidos não alteram a data de vencimento da loja.
    """
    cliente_id = criar_cliente(conn, Cliente(razao_social="CLIENTE HISTORICO"))
    loja_id = criar_loja(conn, Loja(
        cliente_id=cliente_id,
        codigo_loja="HIST-10",
        nome_site="LOJA TESTE HISTORICO",
        cidade="São Paulo",
        uf="SP",
        modelo_bandeira="MODA",
        vencimento="2026-11-01"
    ))
    prod_id = criar_produto(conn, Produto(nome="RECARGA TESTE", tipo="SERVICO", preco_padrao=50.0))
    conn.commit()

    # 1. Pedido Aberto
    p_aberto_id = criar_pedido(conn, Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="PED-01",
        data_emissao="2026-08-01",
        status=STATUS_PEDIDO_ABERTO
    ))
    adicionar_item_pedido(conn, ItemPedido(pedido_id=p_aberto_id, produto_id=prod_id, secao=SECAO_SERVICOS, descricao="Item 1", quantidade=2, preco_unitario=50.0))

    # 2. Pedido Executado
    p_exec_id = criar_pedido(conn, Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="PED-02",
        data_emissao="2026-09-01",
        data_execucao="2026-09-05",
        status=STATUS_PEDIDO_EXECUTADO
    ))
    adicionar_item_pedido(conn, ItemPedido(pedido_id=p_exec_id, produto_id=prod_id, secao=SECAO_SERVICOS, descricao="Item 2", quantidade=3, preco_unitario=50.0))

    # 3. Pedido Executado e depois Faturado
    p_fat_id = criar_pedido(conn, Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="PED-03",
        data_emissao="2026-10-01",
        data_execucao="2026-10-04",
        status=STATUS_PEDIDO_EXECUTADO
    ))
    adicionar_item_pedido(conn, ItemPedido(pedido_id=p_fat_id, produto_id=prod_id, secao=SECAO_SERVICOS, descricao="Item 3", quantidade=4, preco_unitario=50.0))
    # Simula fechamento do faturamento alterando status para FATURADO
    conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (STATUS_PEDIDO_FATURADO, p_fat_id))
    conn.commit()

    # Consulta o histórico da loja
    historico = obter_historico_atendimentos_loja(conn, loja_id)
    assert len(historico) == 3

    # Mapeia por número do pedido
    mapa_hist = {h["numero_pedido"]: h for h in historico}

    # Pedido Aberto -> Não atendido / Pendente
    assert mapa_hist["PED-01"]["atendido"] is False
    assert "PENDENTE" in mapa_hist["PED-01"]["situacao_atendimento"]
    assert mapa_hist["PED-01"]["valor_total"] == 100.0

    # Pedido Executado -> Não atendido / Pendente
    assert mapa_hist["PED-02"]["atendido"] is False
    assert "PENDENTE" in mapa_hist["PED-02"]["situacao_atendimento"]
    assert mapa_hist["PED-02"]["valor_total"] == 150.0

    # Pedido Faturado -> Atendido
    assert mapa_hist["PED-03"]["atendido"] is True
    assert "ATENDIDO" in mapa_hist["PED-03"]["situacao_atendimento"]
    assert mapa_hist["PED-03"]["valor_total"] == 200.0

    # Confirmação da regra: o vencimento cadastrado da loja NÃO foi alterado
    loja_recarregada = buscar_loja_por_id(conn, loja_id)
    assert loja_recarregada.vencimento == "2026-11-01"
