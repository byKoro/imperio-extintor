"""Testes das regras de negócio de pedidos.

Valida:
- Cópia do preço no momento do lançamento (imunidade a mudanças posteriores na tabela).
- Tabela de preços por cliente com fallback para tabela padrão.
- Bloqueio de edição e inserção de itens em pedidos faturados.
- Transições de status e exigência de data de execução.
- Duplicação de pedidos com valores zerados.
"""

import pytest
import sqlite3
from app.core.constants import (
    STATUS_PEDIDO_ABERTO,
    STATUS_PEDIDO_EXECUTADO,
    STATUS_PEDIDO_FATURADO,
    SECAO_SERVICOS,
)
from db.models import Pedido, ItemPedido
from db.repositories import (
    criar_pedido,
    buscar_pedido_por_id,
    adicionar_item_pedido,
    listar_itens_pedido,
    atualizar_pedido,
    definir_preco_cliente,
    obter_preco_produto_para_cliente,
)
from app.core.order_service import (
    validar_transicao_status,
    duplicar_pedido,
)


def test_copia_preco_no_lancamento(conn: sqlite3.Connection, dados_ficticios: dict):
    """Regra 4 e 5.2: O preço usado no item é gravado no momento do lançamento.
    
    Alterar o preço da tabela depois NÃO muda pedidos já lançados.
    """
    cliente_id = dados_ficticios["cliente_id"]
    loja_id = dados_ficticios["loja_id"]
    prod_id = dados_ficticios["prod_servico_id"]

    # 1. Cria pedido
    pedido = Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="2026001",
        data_emissao="2026-10-13",
        status=STATUS_PEDIDO_ABERTO,
    )
    pedido_id = criar_pedido(conn, pedido)

    # 2. Obtém preço atual da tabela e lança item
    preco_inicial = obter_preco_produto_para_cliente(conn, cliente_id, prod_id)
    assert preco_inicial == 50.0

    item = ItemPedido(
        pedido_id=pedido_id,
        produto_id=prod_id,
        secao=SECAO_SERVICOS,
        descricao="RECARGA EXTINTOR AP 10L TESTE",
        quantidade=5.0,
        unidade="SV",
        preco_unitario=preco_inicial,
        valor_total=round(5.0 * preco_inicial, 2),
    )
    adicionar_item_pedido(conn, item)

    # 3. Altera o preço do produto na tabela para 99.00
    conn.execute("UPDATE produtos SET preco_padrao = 99.00 WHERE id = ?", (prod_id,))
    conn.commit()

    # 4. Verifica se o item no pedido continua com 50.0
    itens = listar_itens_pedido(conn, pedido_id)
    assert len(itens) == 1
    assert itens[0].preco_unitario == 50.0
    assert itens[0].valor_total == 250.0


def test_tabela_precos_por_cliente(conn: sqlite3.Connection, dados_ficticios: dict):
    """Regra 4: Tabela própria do cliente substitui preço padrão só para produtos que contém."""
    cliente_id = dados_ficticios["cliente_id"]
    prod_servico_id = dados_ficticios["prod_servico_id"]
    prod_peca_id = dados_ficticios["prod_peca_id"]

    # Preço padrão original: servico=50.0, peca=15.0
    # Define preço especial para este cliente apenas para o serviço
    definir_preco_cliente(conn, cliente_id, prod_servico_id, 42.50)

    # Produto com preço customizado retorna 42.50
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_servico_id) == 42.50
    # Produto sem preço customizado retorna o padrão 15.00
    assert obter_preco_produto_para_cliente(conn, cliente_id, prod_peca_id) == 15.00


def test_bloqueio_pedido_faturado(conn: sqlite3.Connection, dados_ficticios: dict):
    """Regra 6: Pedido incluído em faturamento não pode ser editado nem receber novos itens."""
    cliente_id = dados_ficticios["cliente_id"]
    loja_id = dados_ficticios["loja_id"]
    prod_id = dados_ficticios["prod_servico_id"]

    pedido = Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="2026002",
        data_emissao="2026-10-10",
        data_execucao="2026-10-12",
        status=STATUS_PEDIDO_FATURADO,
    )
    pedido_id = criar_pedido(conn, pedido)

    # Tentativa de atualizar pedido faturado deve falhar
    pedido_carregado = buscar_pedido_por_id(conn, pedido_id)
    pedido_carregado.observacoes = "Tentativa de alteração"
    with pytest.raises(PermissionError, match="não pode ser alterado"):
        atualizar_pedido(conn, pedido_carregado)

    # Tentativa de adicionar item a pedido faturado deve falhar
    novo_item = ItemPedido(
        pedido_id=pedido_id,
        produto_id=prod_id,
        secao=SECAO_SERVICOS,
        descricao="Item extra indevido",
        quantidade=1.0,
        unidade="SV",
        preco_unitario=50.0,
    )
    with pytest.raises(PermissionError, match=r"(?i)não é permitido adicionar itens"):
        adicionar_item_pedido(conn, novo_item)


def test_transicoes_status_pedido():
    """Regra 6: Validação de transições de status."""
    # Aberto -> Executado sem data deve falhar
    with pytest.raises(ValueError, match="exige a data de execução preenchida"):
        validar_transicao_status(STATUS_PEDIDO_ABERTO, STATUS_PEDIDO_EXECUTADO, None)

    # Aberto -> Executado com data válida deve passar
    validar_transicao_status(STATUS_PEDIDO_ABERTO, STATUS_PEDIDO_EXECUTADO, "2026-10-12")

    # Faturado -> Aberto deve falhar
    with pytest.raises(PermissionError, match="não pode retornar"):
        validar_transicao_status(STATUS_PEDIDO_FATURADO, STATUS_PEDIDO_ABERTO, "2026-10-12")


def test_duplicar_pedido(conn: sqlite3.Connection, dados_ficticios: dict):
    """Regra 5.5: Duplicar cria novo pedido com mesma loja e cliente, quantidades e preços zerados."""
    cliente_id = dados_ficticios["cliente_id"]
    loja_id = dados_ficticios["loja_id"]
    prod_id = dados_ficticios["prod_servico_id"]

    # Cria pedido original com itens
    pedido_orig = Pedido(
        cliente_id=cliente_id,
        loja_id=loja_id,
        numero_pedido="2026003",
        data_emissao="2026-10-01",
        data_execucao="2026-10-05",
        status=STATUS_PEDIDO_EXECUTADO,
        observacoes="Nota original",
    )
    pedido_orig_id = criar_pedido(conn, pedido_orig)

    item_orig = ItemPedido(
        pedido_id=pedido_orig_id,
        produto_id=prod_id,
        secao=SECAO_SERVICOS,
        descricao="Item original com valor",
        quantidade=8.0,
        unidade="SV",
        preco_unitario=50.0,
        valor_total=400.0,
    )
    adicionar_item_pedido(conn, item_orig)

    # Duplica pedido
    novo_pedido_id = duplicar_pedido(
        conn,
        pedido_origem_id=pedido_orig_id,
        novo_numero_pedido="2026004",
        nova_data_emissao="2026-10-13"
    )

    # Verifica o novo pedido
    novo_pedido = buscar_pedido_por_id(conn, novo_pedido_id)
    assert novo_pedido.cliente_id == cliente_id
    assert novo_pedido.loja_id == loja_id
    assert novo_pedido.numero_pedido == "2026004"
    assert novo_pedido.status == STATUS_PEDIDO_ABERTO
    assert novo_pedido.data_execucao is None

    # Verifica que itens do novo pedido estão zerados
    novos_itens = listar_itens_pedido(conn, novo_pedido_id)
    assert len(novos_itens) == 1
    assert novos_itens[0].quantidade == 0.0
    assert novos_itens[0].preco_unitario == 0.0
    assert novos_itens[0].valor_total == 0.0

    # Verifica que o pedido original não foi alterado
    itens_originais_recarregados = listar_itens_pedido(conn, pedido_orig_id)
    assert itens_originais_recarregados[0].quantidade == 8.0
    assert itens_originais_recarregados[0].preco_unitario == 50.0
    assert itens_originais_recarregados[0].valor_total == 400.0
