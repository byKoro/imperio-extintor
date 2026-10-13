"""Serviço com regras de negócio para Pedidos."""

import sqlite3
from typing import Optional, List
from app.core.constants import (
    STATUS_PEDIDO_ABERTO,
    STATUS_PEDIDO_EXECUTADO,
    STATUS_PEDIDO_FATURADO,
    STATUS_PEDIDO_PAGO,
)
from db.models import Pedido, ItemPedido
from db.repositories import (
    buscar_pedido_por_id,
    criar_pedido,
    adicionar_item_pedido,
    listar_itens_pedido,
    obter_preco_produto_para_cliente,
)


def validar_transicao_status(status_atual: str, novo_status: str, data_execucao: Optional[str]) -> None:
    """Valida as regras de transição de status de pedidos.
    
    Regras:
    - Aberto -> Executado: exige data de execução.
    - Pedido Faturado ou Pago não pode voltar para Aberto ou Executado.
    """
    if status_atual in (STATUS_PEDIDO_FATURADO, STATUS_PEDIDO_PAGO):
        if novo_status in (STATUS_PEDIDO_ABERTO, STATUS_PEDIDO_EXECUTADO):
            raise PermissionError("Pedido já faturado ou pago não pode retornar para Aberto ou Executado.")

    if novo_status == STATUS_PEDIDO_EXECUTADO:
        if not data_execucao or not str(data_execucao).strip():
            raise ValueError("A transição para o status Executado exige a data de execução preenchida.")

    if novo_status == STATUS_PEDIDO_FATURADO:
        if status_atual == STATUS_PEDIDO_ABERTO and (not data_execucao or not str(data_execucao).strip()):
            raise ValueError("Para faturar um pedido, ele deve ter sido executado com data de execução informada.")


def verificar_edicao_permitida(pedido: Pedido) -> None:
    """Garante que pedidos faturados ou pagos não sejam editados."""
    if pedido.status in (STATUS_PEDIDO_FATURADO, STATUS_PEDIDO_PAGO):
        raise PermissionError("Pedido faturado não pode ser editado.")


def obter_preco_sugerido_item(conn: sqlite3.Connection, cliente_id: int, produto_id: int) -> float:
    """Retorna o preço sugerido do produto para o cliente (tabela própria ou tabela padrão)."""
    return obter_preco_produto_para_cliente(conn, cliente_id, produto_id)


def duplicar_pedido(
    conn: sqlite3.Connection,
    pedido_origem_id: int,
    novo_numero_pedido: str,
    nova_data_emissao: str
) -> int:
    """Cria uma cópia do pedido com mesmo cliente e loja, quantidades e preços zerados.
    
    Regra 5.5: A função 'duplicar' cria um novo pedido com a mesma loja e cliente,
    com quantidades e preços zerados. O pedido original não é alterado.
    """
    pedido_orig = buscar_pedido_por_id(conn, pedido_origem_id)
    if not pedido_orig:
        raise ValueError(f"Pedido de origem {pedido_origem_id} não encontrado.")

    novo_pedido = Pedido(
        cliente_id=pedido_orig.cliente_id,
        loja_id=pedido_orig.loja_id,
        numero_pedido=novo_numero_pedido,
        data_emissao=nova_data_emissao,
        data_execucao=None,
        status=STATUS_PEDIDO_ABERTO,
        observacao_loja=pedido_orig.observacao_loja,
        observacoes=pedido_orig.observacoes,
        prazo_pagamento=pedido_orig.prazo_pagamento,
        forma_pagamento=pedido_orig.forma_pagamento,
        prazo_entrega=pedido_orig.prazo_entrega,
        texto_impostos=pedido_orig.texto_impostos,
    )

    novo_id = criar_pedido(conn, novo_pedido)

    # Copia itens com quantidades e preços zerados
    itens_orig = listar_itens_pedido(conn, pedido_origem_id)
    for it in itens_orig:
        novo_item = ItemPedido(
            pedido_id=novo_id,
            produto_id=it.produto_id,
            secao=it.secao,
            descricao=it.descricao,
            quantidade=0.0,
            unidade=it.unidade,
            preco_unitario=0.0,
            valor_total=0.0,
            ordem=it.ordem,
        )
        adicionar_item_pedido(conn, novo_item)

    conn.commit()
    return novo_id
