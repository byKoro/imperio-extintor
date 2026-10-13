"""Funções diretas de persistência em SQLite (repositório)."""

import sqlite3
from typing import List, Optional, Tuple
from db.models import (
    Cliente, Loja, Produto, PrecoCliente, Pedido, ItemPedido,
    Ajuste, ItemAjuste, Faturamento, FaturamentoItem
)


# ==========================================
# CLIENTES
# ==========================================

def criar_cliente(conn: sqlite3.Connection, c: Cliente) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clientes (
            razao_social, nome_fantasia, cnpj, inscricao_estadual,
            endereco, telefone, email, contato, prazo_pagamento,
            forma_pagamento, prazo_entrega, texto_impostos, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        c.razao_social, c.nome_fantasia, c.cnpj, c.inscricao_estadual,
        c.endereco, c.telefone, c.email, c.contato, c.prazo_pagamento,
        c.forma_pagamento, c.prazo_entrega, c.texto_impostos, c.ativo
    ))
    return cursor.lastrowid


def buscar_cliente_por_id(conn: sqlite3.Connection, cliente_id: int) -> Optional[Cliente]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return Cliente(
        id=row["id"],
        razao_social=row["razao_social"],
        nome_fantasia=row["nome_fantasia"],
        cnpj=row["cnpj"],
        inscricao_estadual=row["inscricao_estadual"],
        endereco=row["endereco"],
        telefone=row["telefone"],
        email=row["email"],
        contato=row["contato"],
        prazo_pagamento=row["prazo_pagamento"],
        forma_pagamento=row["forma_pagamento"],
        prazo_entrega=row["prazo_entrega"],
        texto_impostos=row["texto_impostos"],
        ativo=row["ativo"],
        created_at=row["created_at"],
    )


def listar_clientes(conn: sqlite3.Connection, apenas_ativos: bool = True) -> List[Cliente]:
    cursor = conn.cursor()
    query = "SELECT * FROM clientes" + (" WHERE ativo = 1" if apenas_ativos else "") + " ORDER BY razao_social"
    cursor.execute(query)
    clientes = []
    for row in cursor.fetchall():
        clientes.append(Cliente(
            id=row["id"],
            razao_social=row["razao_social"],
            nome_fantasia=row["nome_fantasia"],
            cnpj=row["cnpj"],
            inscricao_estadual=row["inscricao_estadual"],
            endereco=row["endereco"],
            telefone=row["telefone"],
            email=row["email"],
            contato=row["contato"],
            prazo_pagamento=row["prazo_pagamento"],
            forma_pagamento=row["forma_pagamento"],
            prazo_entrega=row["prazo_entrega"],
            texto_impostos=row["texto_impostos"],
            ativo=row["ativo"],
            created_at=row["created_at"],
        ))
    return clientes


# ==========================================
# LOJAS
# ==========================================

def criar_loja(conn: sqlite3.Connection, loja: Loja) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lojas (
            cliente_id, codigo_loja, nome_site, cidade, uf,
            modelo_bandeira, vencimento, observacao, notificada, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        loja.cliente_id, str(loja.codigo_loja).strip(), loja.nome_site.strip(),
        loja.cidade.strip(), loja.uf.strip().upper(), loja.modelo_bandeira.strip(),
        loja.vencimento, loja.observacao, loja.notificada, loja.ativo
    ))
    return cursor.lastrowid


def buscar_loja_por_id(conn: sqlite3.Connection, loja_id: int) -> Optional[Loja]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lojas WHERE id = ?", (loja_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return Loja(
        id=row["id"],
        cliente_id=row["cliente_id"],
        codigo_loja=row["codigo_loja"],
        nome_site=row["nome_site"],
        cidade=row["cidade"],
        uf=row["uf"],
        modelo_bandeira=row["modelo_bandeira"],
        vencimento=row["vencimento"],
        observacao=row["observacao"],
        notificada=row["notificada"],
        ativo=row["ativo"],
        created_at=row["created_at"],
    )


def listar_lojas_por_cliente(conn: sqlite3.Connection, cliente_id: int, apenas_ativas: bool = True) -> List[Loja]:
    cursor = conn.cursor()
    query = "SELECT * FROM lojas WHERE cliente_id = ?"
    if apenas_ativas:
        query += " AND ativo = 1"
    query += " ORDER BY codigo_loja"
    cursor.execute(query, (cliente_id,))
    lojas = []
    for row in cursor.fetchall():
        lojas.append(Loja(
            id=row["id"],
            cliente_id=row["cliente_id"],
            codigo_loja=row["codigo_loja"],
            nome_site=row["nome_site"],
            cidade=row["cidade"],
            uf=row["uf"],
            modelo_bandeira=row["modelo_bandeira"],
            vencimento=row["vencimento"],
            observacao=row["observacao"],
            notificada=row["notificada"],
            ativo=row["ativo"],
            created_at=row["created_at"],
        ))
    return lojas


# ==========================================
# PRODUTOS E PREÇOS POR CLIENTE
# ==========================================

def criar_produto(conn: sqlite3.Connection, p: Produto) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO produtos (
            nome, categoria, tipo, unidade, capacidade, preco_padrao, ativo
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        p.nome.strip(), p.categoria, p.tipo, p.unidade, p.capacidade, p.preco_padrao, p.ativo
    ))
    return cursor.lastrowid


def buscar_produto_por_id(conn: sqlite3.Connection, produto_id: int) -> Optional[Produto]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return Produto(
        id=row["id"],
        nome=row["nome"],
        categoria=row["categoria"],
        tipo=row["tipo"],
        unidade=row["unidade"],
        capacidade=row["capacidade"],
        preco_padrao=row["preco_padrao"],
        ativo=row["ativo"],
        created_at=row["created_at"],
    )


def listar_produtos(conn: sqlite3.Connection, apenas_ativos: bool = True) -> List[Produto]:
    cursor = conn.cursor()
    query = "SELECT * FROM produtos" + (" WHERE ativo = 1" if apenas_ativos else "") + " ORDER BY tipo, nome"
    cursor.execute(query)
    produtos = []
    for row in cursor.fetchall():
        produtos.append(Produto(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            tipo=row["tipo"],
            unidade=row["unidade"],
            capacidade=row["capacidade"],
            preco_padrao=row["preco_padrao"],
            ativo=row["ativo"],
            created_at=row["created_at"],
        ))
    return produtos


def definir_preco_cliente(conn: sqlite3.Connection, cliente_id: int, produto_id: int, preco: float) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO precos_cliente (cliente_id, produto_id, preco)
        VALUES (?, ?, ?)
        ON CONFLICT(cliente_id, produto_id) DO UPDATE SET preco = excluded.preco
    """, (cliente_id, produto_id, preco))


def obter_preco_produto_para_cliente(conn: sqlite3.Connection, cliente_id: int, produto_id: int) -> float:
    """Busca preço específico do cliente. Se não existir, retorna o preço padrão do produto."""
    cursor = conn.cursor()
    # Verifica preço na tabela do cliente
    cursor.execute(
        "SELECT preco FROM precos_cliente WHERE cliente_id = ? AND produto_id = ?",
        (cliente_id, produto_id)
    )
    row = cursor.fetchone()
    if row is not None:
        return float(row["preco"])

    # Fallback: preço padrão da tabela de produtos
    cursor.execute("SELECT preco_padrao FROM produtos WHERE id = ?", (produto_id,))
    row_prod = cursor.fetchone()
    if row_prod is not None:
        return float(row_prod["preco_padrao"])

    return 0.0


# ==========================================
# PEDIDOS E ITENS
# ==========================================

def criar_pedido(conn: sqlite3.Connection, pedido: Pedido) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pedidos (
            cliente_id, loja_id, numero_pedido, data_emissao,
            data_execucao, status, observacao_loja, observacoes,
            prazo_pagamento, forma_pagamento, prazo_entrega, texto_impostos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pedido.cliente_id, pedido.loja_id, str(pedido.numero_pedido).strip(),
        pedido.data_emissao, pedido.data_execucao, pedido.status,
        pedido.observacao_loja, pedido.observacoes, pedido.prazo_pagamento,
        pedido.forma_pagamento, pedido.prazo_entrega, pedido.texto_impostos
    ))
    return cursor.lastrowid


def atualizar_pedido(conn: sqlite3.Connection, pedido: Pedido) -> None:
    """Atualiza dados do pedido. Levanta ValueError se o pedido já estiver FATURADO."""
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pedidos WHERE id = ?", (pedido.id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Pedido com id {pedido.id} não encontrado.")
    if row["status"] in ("FATURADO", "PAGO"):
        raise PermissionError("Pedido faturado ou pago não pode ser alterado.")

    cursor.execute("""
        UPDATE pedidos SET
            data_emissao = ?,
            data_execucao = ?,
            status = ?,
            observacao_loja = ?,
            observacoes = ?,
            prazo_pagamento = ?,
            forma_pagamento = ?,
            prazo_entrega = ?,
            texto_impostos = ?
        WHERE id = ?
    """, (
        pedido.data_emissao, pedido.data_execucao, pedido.status,
        pedido.observacao_loja, pedido.observacoes, pedido.prazo_pagamento,
        pedido.forma_pagamento, pedido.prazo_entrega, pedido.texto_impostos,
        pedido.id
    ))


def buscar_pedido_por_id(conn: sqlite3.Connection, pedido_id: int) -> Optional[Pedido]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return Pedido(
        id=row["id"],
        cliente_id=row["cliente_id"],
        loja_id=row["loja_id"],
        numero_pedido=row["numero_pedido"],
        data_emissao=row["data_emissao"],
        data_execucao=row["data_execucao"],
        status=row["status"],
        observacao_loja=row["observacao_loja"],
        observacoes=row["observacoes"],
        prazo_pagamento=row["prazo_pagamento"],
        forma_pagamento=row["forma_pagamento"],
        prazo_entrega=row["prazo_entrega"],
        texto_impostos=row["texto_impostos"],
        created_at=row["created_at"],
    )


def adicionar_item_pedido(conn: sqlite3.Connection, item: ItemPedido) -> int:
    """Adiciona um item ao pedido. Bloqueia se o pedido estiver faturado."""
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pedidos WHERE id = ?", (item.pedido_id,))
    row = cursor.fetchone()
    if row and row["status"] in ("FATURADO", "PAGO"):
        raise PermissionError("Não é permitido adicionar itens a um pedido faturado.")

    # Calcula valor_total arredondado para 2 casas decimais
    total = round(item.quantidade * item.preco_unitario, 2)
    cursor.execute("""
        INSERT INTO itens_pedido (
            pedido_id, produto_id, secao, descricao,
            quantidade, unidade, preco_unitario, valor_total, ordem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.pedido_id, item.produto_id, item.secao, item.descricao,
        item.quantidade, item.unidade, item.preco_unitario, total, item.ordem
    ))
    return cursor.lastrowid


def listar_itens_pedido(conn: sqlite3.Connection, pedido_id: int) -> List[ItemPedido]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ? ORDER BY ordem, id", (pedido_id,))
    itens = []
    for row in cursor.fetchall():
        itens.append(ItemPedido(
            id=row["id"],
            pedido_id=row["pedido_id"],
            produto_id=row["produto_id"],
            secao=row["secao"],
            descricao=row["descricao"],
            quantidade=row["quantidade"],
            unidade=row["unidade"],
            preco_unitario=row["preco_unitario"],
            valor_total=row["valor_total"],
            ordem=row["ordem"],
        ))
    return itens


# ==========================================
# AJUSTES (FATURAMENTO COMPLEMENTAR)
# ==========================================

def criar_ajuste(conn: sqlite3.Connection, ajuste: Ajuste) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ajustes (
            pedido_id, numero_ajuste, data_emissao, modo_geracao,
            status, faturamento_id, valor_cobrado, observacoes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ajuste.pedido_id, ajuste.numero_ajuste, ajuste.data_emissao,
        ajuste.modo_geracao, ajuste.status, ajuste.faturamento_id,
        ajuste.valor_cobrado, ajuste.observacoes
    ))
    return cursor.lastrowid


def adicionar_item_ajuste(conn: sqlite3.Connection, item: ItemAjuste) -> int:
    cursor = conn.cursor()
    total = round(item.quantidade * item.preco_unitario, 2)
    cursor.execute("""
        INSERT INTO itens_ajuste (
            ajuste_id, produto_id, secao, descricao,
            quantidade, unidade, preco_unitario, valor_total, ordem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.ajuste_id, item.produto_id, item.secao, item.descricao,
        item.quantidade, item.unidade, item.preco_unitario, total, item.ordem
    ))
    return cursor.lastrowid


def listar_ajustes_do_pedido(conn: sqlite3.Connection, pedido_id: int) -> List[Ajuste]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ajustes WHERE pedido_id = ? ORDER BY id", (pedido_id,))
    ajustes = []
    for row in cursor.fetchall():
        ajustes.append(Ajuste(
            id=row["id"],
            pedido_id=row["pedido_id"],
            numero_ajuste=row["numero_ajuste"],
            data_emissao=row["data_emissao"],
            modo_geracao=row["modo_geracao"],
            status=row["status"],
            faturamento_id=row["faturamento_id"],
            valor_cobrado=row["valor_cobrado"],
            observacoes=row["observacoes"],
            created_at=row["created_at"],
        ))
    return ajustes


def listar_itens_ajuste(conn: sqlite3.Connection, ajuste_id: int) -> List[ItemAjuste]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens_ajuste WHERE ajuste_id = ? ORDER BY ordem, id", (ajuste_id,))
    itens = []
    for row in cursor.fetchall():
        itens.append(ItemAjuste(
            id=row["id"],
            ajuste_id=row["ajuste_id"],
            produto_id=row["produto_id"],
            secao=row["secao"],
            descricao=row["descricao"],
            quantidade=row["quantidade"],
            unidade=row["unidade"],
            preco_unitario=row["preco_unitario"],
            valor_total=row["valor_total"],
            ordem=row["ordem"],
        ))
    return itens
