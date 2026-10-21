"""Funções diretas de persistência em SQLite (repositório)."""

import sqlite3
from typing import List, Optional, Tuple, Dict, Any
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


def atualizar_cliente(conn: sqlite3.Connection, c: Cliente) -> None:
    if c.id is None:
        raise ValueError("ID do cliente não informado para atualização.")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clientes SET
            razao_social = ?,
            nome_fantasia = ?,
            cnpj = ?,
            inscricao_estadual = ?,
            endereco = ?,
            telefone = ?,
            email = ?,
            contato = ?,
            prazo_pagamento = ?,
            forma_pagamento = ?,
            prazo_entrega = ?,
            texto_impostos = ?,
            ativo = ?
        WHERE id = ?
    """, (
        c.razao_social, c.nome_fantasia, c.cnpj, c.inscricao_estadual,
        c.endereco, c.telefone, c.email, c.contato, c.prazo_pagamento,
        c.forma_pagamento, c.prazo_entrega, c.texto_impostos, c.ativo,
        c.id
    ))


def excluir_cliente(conn: sqlite3.Connection, cliente_id: int) -> None:
    """Inativa o cliente ou remove caso não haja pedidos vinculados."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE cliente_id = ?", (cliente_id,))
    row = cursor.fetchone()
    if row and row["total"] > 0:
        cursor.execute("UPDATE clientes SET ativo = 0 WHERE id = ?", (cliente_id,))
    else:
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))


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


def atualizar_loja(conn: sqlite3.Connection, loja: Loja) -> None:
    if loja.id is None:
        raise ValueError("ID da loja não informado para atualização.")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lojas SET
            codigo_loja = ?,
            nome_site = ?,
            cidade = ?,
            uf = ?,
            modelo_bandeira = ?,
            vencimento = ?,
            observacao = ?,
            notificada = ?,
            ativo = ?
        WHERE id = ?
    """, (
        str(loja.codigo_loja).strip(), loja.nome_site.strip(),
        loja.cidade.strip(), loja.uf.strip().upper(), loja.modelo_bandeira.strip(),
        loja.vencimento, loja.observacao, loja.notificada, loja.ativo,
        loja.id
    ))


def excluir_loja(conn: sqlite3.Connection, loja_id: int) -> None:
    """Inativa a loja ou remove caso não haja pedidos vinculados."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE loja_id = ?", (loja_id,))
    row = cursor.fetchone()
    if row and row["total"] > 0:
        cursor.execute("UPDATE lojas SET ativo = 0 WHERE id = ?", (loja_id,))
    else:
        cursor.execute("DELETE FROM lojas WHERE id = ?", (loja_id,))


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


def buscar_loja_por_codigo(conn: sqlite3.Connection, cliente_id: int, codigo_loja: str) -> Optional[Loja]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lojas WHERE cliente_id = ? AND codigo_loja = ?", (cliente_id, str(codigo_loja).strip()))
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


def obter_historico_atendimentos_loja(conn: sqlite3.Connection, loja_id: int) -> List[Dict[str, Any]]:
    """Retorna o histórico de atendimentos de uma loja.
    
    Regra 3: Uma loja só é considerada atendida depois que o atendimento é faturado.
    Atendimentos ainda não faturados aparecem como pendentes.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id,
            p.numero_pedido,
            p.data_emissao,
            p.data_execucao,
            p.status,
            COALESCE(SUM(i.valor_total), 0.0) as valor_total
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        WHERE p.loja_id = ?
        GROUP BY p.id
        ORDER BY p.data_emissao DESC, p.id DESC
    """, (loja_id,))
    
    historico = []
    for row in cursor.fetchall():
        status = row["status"]
        is_faturado = (status in ("FATURADO", "PAGO"))
        historico.append({
            "pedido_id": row["id"],
            "numero_pedido": row["numero_pedido"],
            "data_emissao": row["data_emissao"],
            "data_execucao": row["data_execucao"],
            "status": status,
            "valor_total": float(row["valor_total"]),
            "atendido": is_faturado,
            "situacao_atendimento": "ATENDIDO (FATURADO)" if is_faturado else f"PENDENTE ({status})"
        })
    return historico


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


def atualizar_produto(conn: sqlite3.Connection, p: Produto) -> None:
    if p.id is None:
        raise ValueError("ID do produto não informado para atualização.")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produtos SET
            nome = ?,
            categoria = ?,
            tipo = ?,
            unidade = ?,
            capacidade = ?,
            preco_padrao = ?,
            ativo = ?
        WHERE id = ?
    """, (
        p.nome.strip(), p.categoria, p.tipo, p.unidade, p.capacidade,
        p.preco_padrao, p.ativo, p.id
    ))


def excluir_produto(conn: sqlite3.Connection, produto_id: int) -> None:
    """Inativa o produto ou remove caso não tenha sido usado em pedidos."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM itens_pedido WHERE produto_id = ?", (produto_id,))
    row = cursor.fetchone()
    if row and row["total"] > 0:
        cursor.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
    else:
        cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))


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


def buscar_produto_por_nome(conn: sqlite3.Connection, nome: str) -> Optional[Produto]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE nome = ?", (nome.strip(),))
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
    """, (cliente_id, produto_id, float(preco)))


def remover_preco_cliente(conn: sqlite3.Connection, cliente_id: int, produto_id: int) -> None:
    """Remove a personalização de preço do cliente, restaurando o preço padrão da tabela."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM precos_cliente WHERE cliente_id = ? AND produto_id = ?", (cliente_id, produto_id))


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


def listar_precos_por_cliente(conn: sqlite3.Connection, cliente_id: int) -> List[Dict[str, Any]]:
    """Lista todos os produtos ativos indicando se possuem preço customizado para o cliente."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id as produto_id,
            p.nome,
            p.categoria,
            p.tipo,
            p.unidade,
            p.capacidade,
            p.preco_padrao,
            pc.preco as preco_cliente
        FROM produtos p
        LEFT JOIN precos_cliente pc ON pc.produto_id = p.id AND pc.cliente_id = ?
        WHERE p.ativo = 1
        ORDER BY p.tipo, p.nome
    """, (cliente_id,))
    
    itens = []
    for row in cursor.fetchall():
        preco_cliente = row["preco_cliente"]
        preco_padrao = float(row["preco_padrao"])
        preco_efetivo = float(preco_cliente) if preco_cliente is not None else preco_padrao
        itens.append({
            "produto_id": row["produto_id"],
            "nome": row["nome"],
            "categoria": row["categoria"],
            "tipo": row["tipo"],
            "unidade": row["unidade"],
            "capacidade": row["capacidade"],
            "preco_padrao": preco_padrao,
            "preco_cliente": float(preco_cliente) if preco_cliente is not None else None,
            "preco_efetivo": preco_efetivo,
            "tem_personalizacao": (preco_cliente is not None)
        })
    return itens


# ==========================================
# PEDIDOS E ITENS
# ==========================================

def criar_pedido(conn: sqlite3.Connection, pedido: Pedido) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pedidos (
            cliente_id, loja_id, numero_pedido, data_emissao,
            data_execucao, status, observacoes,
            prazo_pagamento, forma_pagamento, prazo_entrega, texto_impostos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pedido.cliente_id, pedido.loja_id, str(pedido.numero_pedido).strip(),
        pedido.data_emissao, pedido.data_execucao, pedido.status,
        pedido.observacoes, pedido.prazo_pagamento,
        pedido.forma_pagamento, pedido.prazo_entrega, pedido.texto_impostos
    ))
    return cursor.lastrowid


def atualizar_pedido(conn: sqlite3.Connection, pedido: Pedido) -> None:
    """Atualiza dados do cabeçalho do pedido no banco de dados."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos WHERE id = ?", (pedido.id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Pedido com id {pedido.id} não encontrado.")

    cursor.execute("""
        UPDATE pedidos SET
            cliente_id = ?,
            loja_id = ?,
            numero_pedido = ?,
            data_emissao = ?,
            data_execucao = ?,
            status = ?,
            observacoes = ?,
            prazo_pagamento = ?,
            forma_pagamento = ?,
            prazo_entrega = ?,
            texto_impostos = ?
        WHERE id = ?
    """, (
        pedido.cliente_id, pedido.loja_id, str(pedido.numero_pedido).strip(),
        pedido.data_emissao, pedido.data_execucao, pedido.status,
        pedido.observacoes, pedido.prazo_pagamento,
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
        observacoes=row["observacoes"],
        prazo_pagamento=row["prazo_pagamento"],
        forma_pagamento=row["forma_pagamento"],
        prazo_entrega=row["prazo_entrega"],
        texto_impostos=row["texto_impostos"],
        created_at=row["created_at"],
    )


def adicionar_item_pedido(conn: sqlite3.Connection, item: ItemPedido) -> int:
    """Adiciona um item ao pedido."""
    cursor = conn.cursor()
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


def verificar_numero_pedido_existe(
    conn: sqlite3.Connection,
    cliente_id: int,
    numero_pedido: str,
    exceto_id: Optional[int] = None
) -> bool:
    """Verifica se já existe pedido com o mesmo número para o cliente."""
    cursor = conn.cursor()
    num = str(numero_pedido).strip()
    if exceto_id is not None:
        cursor.execute(
            "SELECT 1 FROM pedidos WHERE cliente_id = ? AND numero_pedido = ? AND id != ?",
            (cliente_id, num, exceto_id)
        )
    else:
        cursor.execute(
            "SELECT 1 FROM pedidos WHERE cliente_id = ? AND numero_pedido = ?",
            (cliente_id, num)
        )
    return cursor.fetchone() is not None


def listar_clientes_ativos(conn: sqlite3.Connection) -> List[Cliente]:
    """Retorna clientes ativos (ativo = 1) para novos pedidos."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes WHERE ativo = 1 ORDER BY razao_social COLLATE NOCASE")
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


def listar_lojas_por_cliente(
    conn: sqlite3.Connection,
    cliente_id: int,
    incluir_loja_id: Optional[int] = None
) -> List[Loja]:
    """Retorna lojas do cliente.
    
    Se incluir_loja_id for None (novo pedido), retorna apenas lojas com ativo = 1.
    Se incluir_loja_id for fornecido (edição de pedido), retorna lojas ativas + a loja histórica especificada.
    """
    cursor = conn.cursor()
    if incluir_loja_id is not None:
        cursor.execute("""
            SELECT * FROM lojas
            WHERE cliente_id = ? AND (ativo = 1 OR id = ?)
            ORDER BY codigo_loja
        """, (cliente_id, incluir_loja_id))
    else:
        cursor.execute("""
            SELECT * FROM lojas
            WHERE cliente_id = ? AND ativo = 1
            ORDER BY codigo_loja
        """, (cliente_id,))
    
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


def listar_pedidos(
    conn: sqlite3.Connection,
    cliente_id: Optional[int] = None,
    loja_id: Optional[int] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lista pedidos com dados complementares para a visualização em tabela."""
    cursor = conn.cursor()
    query = """
        SELECT 
            p.id,
            p.cliente_id,
            c.razao_social as cliente_nome,
            p.loja_id,
            l.codigo_loja,
            l.nome_site as loja_nome,
            p.numero_pedido,
            p.data_emissao,
            p.data_execucao,
            p.status,
            p.observacoes,
            COALESCE(SUM(i.valor_total), 0.0) as valor_total
        FROM pedidos p
        INNER JOIN clientes c ON c.id = p.cliente_id
        INNER JOIN lojas l ON l.id = p.loja_id
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        WHERE 1=1
    """
    params = []
    if cliente_id is not None:
        query += " AND p.cliente_id = ?"
        params.append(cliente_id)
    if loja_id is not None:
        query += " AND p.loja_id = ?"
        params.append(loja_id)
    if status is not None and str(status).strip() and str(status).strip().upper() != "TODOS":
        query += " AND p.status = ?"
        params.append(str(status).strip().upper())

    query += " GROUP BY p.id ORDER BY p.data_emissao DESC, p.id DESC"
    cursor.execute(query, params)

    pedidos = []
    for row in cursor.fetchall():
        pedidos.append({
            "id": row["id"],
            "cliente_id": row["cliente_id"],
            "cliente_nome": row["cliente_nome"],
            "loja_id": row["loja_id"],
            "loja_codigo": row["codigo_loja"],
            "loja_nome": row["loja_nome"],
            "numero_pedido": row["numero_pedido"],
            "data_emissao": row["data_emissao"],
            "data_execucao": row["data_execucao"],
            "status": row["status"],
            "observacoes": row["observacoes"],
            "valor_total": float(row["valor_total"]),
        })
    return pedidos


def salvar_pedido_completo(
    conn: sqlite3.Connection,
    pedido: Pedido,
    itens: List[ItemPedido]
) -> int:
    """Salva pedido e itens de forma atômica.
    
    Se conn.in_transaction for False, abre transação e faz commit ao final.
    Se já houver transação aberta pelo chamador, preserva a transação existente.
    """
    abriu_transacao = False
    if not conn.in_transaction:
        conn.execute("BEGIN TRANSACTION;")
        abriu_transacao = True

    try:
        if pedido.id is None:
            pedido_id = criar_pedido(conn, pedido)
            pedido.id = pedido_id
        else:
            atualizar_pedido(conn, pedido)
            pedido_id = pedido.id
            conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))

        for idx, item in enumerate(itens):
            item.pedido_id = pedido_id
            item.ordem = idx
            adicionar_item_pedido(conn, item)

        if abriu_transacao:
            conn.commit()
        return pedido_id
    except Exception:
        if abriu_transacao:
            conn.rollback()
        raise


def excluir_pedido_seguro(conn: sqlite3.Connection, pedido_id: int) -> None:
    """Exclui pedido e seus itens de forma atômica dentro de transação."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ajustes WHERE pedido_id = ?", (pedido_id,))
    if cur.fetchone()[0] > 0:
        raise PermissionError("Não é possível excluir: existem ajustes vinculados a este pedido.")

    cur.execute("SELECT COUNT(*) FROM faturamento_itens WHERE pedido_id = ?", (pedido_id,))
    if cur.fetchone()[0] > 0:
        raise PermissionError("Não é possível excluir: existem faturamentos vinculados a este pedido.")

    abriu_transacao = False
    if not conn.in_transaction:
        conn.execute("BEGIN TRANSACTION;")
        abriu_transacao = True

    try:
        conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
        conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        if abriu_transacao:
            conn.commit()
    except Exception:
        if abriu_transacao:
            conn.rollback()
        raise


# ==========================================
# AJUSTES (FATURAMENTO COMPLEMENTAR)
# ==========================================

def criar_ajuste(conn: sqlite3.Connection, ajuste: Ajuste) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ajustes (
            pedido_id, numero_ajuste, data_emissao, data_execucao, modo_geracao,
            status, faturamento_id, valor_cobrado, observacoes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ajuste.pedido_id, ajuste.numero_ajuste, ajuste.data_emissao, ajuste.data_execucao,
        ajuste.modo_geracao, ajuste.status, ajuste.faturamento_id,
        ajuste.valor_cobrado, ajuste.observacoes
    ))
    return cursor.lastrowid


def _mapear_ajuste(row: sqlite3.Row) -> Ajuste:
    return Ajuste(
        id=row["id"],
        pedido_id=row["pedido_id"],
        numero_ajuste=row["numero_ajuste"],
        data_emissao=row["data_emissao"],
        data_execucao=row["data_execucao"],
        modo_geracao=row["modo_geracao"],
        status=row["status"],
        faturamento_id=row["faturamento_id"],
        valor_cobrado=row["valor_cobrado"],
        observacoes=row["observacoes"],
        created_at=row["created_at"],
    )


def buscar_ajuste_por_id(conn: sqlite3.Connection, ajuste_id: int) -> Optional[Ajuste]:
    row = conn.execute("SELECT * FROM ajustes WHERE id = ?", (ajuste_id,)).fetchone()
    return _mapear_ajuste(row) if row else None


def obter_quantidade_ajustes_pedido(conn: sqlite3.Connection, pedido_id: int) -> int:
    return conn.execute("SELECT COUNT(*) FROM ajustes WHERE pedido_id = ?", (pedido_id,)).fetchone()[0]


def listar_ajustes_pendentes_por_periodo(
    conn: sqlite3.Connection, cliente_id: int, mes: int, ano: int
) -> List[Ajuste]:
    """Ajustes PENDENTES cujo mês de execução é o do período, de pedidos do cliente."""
    prefixo = f"{ano:04d}-{mes:02d}"
    rows = conn.execute("""
        SELECT a.* FROM ajustes a
        JOIN pedidos p ON p.id = a.pedido_id
        WHERE p.cliente_id = ?
          AND a.status = 'PENDENTE'
          AND substr(a.data_execucao, 1, 7) = ?
        ORDER BY a.data_execucao, a.id
    """, (cliente_id, prefixo)).fetchall()
    return [_mapear_ajuste(r) for r in rows]


def marcar_ajuste_faturado(conn: sqlite3.Connection, ajuste_id: int, faturamento_id: int) -> None:
    conn.execute(
        "UPDATE ajustes SET status = 'FATURADO', faturamento_id = ? WHERE id = ?",
        (faturamento_id, ajuste_id),
    )


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
            data_execucao=row["data_execucao"],
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


# ==========================================
# FATURAMENTO MENSAL
# ==========================================

def _mapear_faturamento(row: sqlite3.Row) -> Faturamento:
    return Faturamento(
        id=row["id"],
        cliente_id=row["cliente_id"],
        mes_referencia=row["mes_referencia"],
        ano_referencia=row["ano_referencia"],
        data_fechamento=row["data_fechamento"],
        total_geral=row["total_geral"],
        status=row["status"],
        observacoes=row["observacoes"],
        created_at=row["created_at"],
    )


def criar_faturamento(conn: sqlite3.Connection, f: Faturamento) -> int:
    cur = conn.execute("""
        INSERT INTO faturamentos (
            cliente_id, mes_referencia, ano_referencia, data_fechamento,
            total_geral, status, observacoes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (f.cliente_id, f.mes_referencia, f.ano_referencia, f.data_fechamento,
          f.total_geral, f.status, f.observacoes))
    return cur.lastrowid


def buscar_faturamento_por_id(conn: sqlite3.Connection, faturamento_id: int) -> Optional[Faturamento]:
    row = conn.execute("SELECT * FROM faturamentos WHERE id = ?", (faturamento_id,)).fetchone()
    return _mapear_faturamento(row) if row else None


def buscar_faturamento_por_periodo(
    conn: sqlite3.Connection, cliente_id: int, mes: int, ano: int
) -> Optional[Faturamento]:
    row = conn.execute("""
        SELECT * FROM faturamentos
        WHERE cliente_id = ? AND mes_referencia = ? AND ano_referencia = ?
    """, (cliente_id, mes, ano)).fetchone()
    return _mapear_faturamento(row) if row else None


def atualizar_faturamento(conn: sqlite3.Connection, f: Faturamento) -> None:
    conn.execute("""
        UPDATE faturamentos
        SET data_fechamento = ?, total_geral = ?, status = ?, observacoes = ?
        WHERE id = ?
    """, (f.data_fechamento, f.total_geral, f.status, f.observacoes, f.id))


def verificar_mes_fechado(conn: sqlite3.Connection, cliente_id: int, mes: int, ano: int) -> bool:
    row = conn.execute("""
        SELECT 1 FROM faturamentos
        WHERE cliente_id = ? AND mes_referencia = ? AND ano_referencia = ? AND status = 'FECHADO'
    """, (cliente_id, mes, ano)).fetchone()
    return row is not None


def adicionar_item_faturamento(conn: sqlite3.Connection, item: FaturamentoItem) -> int:
    cur = conn.execute("""
        INSERT INTO faturamento_itens (faturamento_id, pedido_id, ajuste_id, valor_cobrado)
        VALUES (?, ?, ?, ?)
    """, (item.faturamento_id, item.pedido_id, item.ajuste_id, item.valor_cobrado))
    return cur.lastrowid


def listar_itens_faturamento(conn: sqlite3.Connection, faturamento_id: int) -> List[FaturamentoItem]:
    rows = conn.execute(
        "SELECT * FROM faturamento_itens WHERE faturamento_id = ? ORDER BY id", (faturamento_id,)
    ).fetchall()
    return [FaturamentoItem(
        id=r["id"], faturamento_id=r["faturamento_id"], pedido_id=r["pedido_id"],
        ajuste_id=r["ajuste_id"], valor_cobrado=r["valor_cobrado"],
    ) for r in rows]


def listar_pedidos_executados_periodo(
    conn: sqlite3.Connection, cliente_id: int, mes: int, ano: int
) -> List[Pedido]:
    """Pedidos EXECUTADOS do cliente cujo mês de execução é o do período e ainda não estão em nenhuma fatura."""
    prefixo = f"{ano:04d}-{mes:02d}"
    ids = conn.execute("""
        SELECT p.id FROM pedidos p
        WHERE p.cliente_id = ?
          AND p.status = 'EXECUTADO'
          AND substr(p.data_execucao, 1, 7) = ?
          AND NOT EXISTS (SELECT 1 FROM faturamento_itens fi WHERE fi.pedido_id = p.id)
        ORDER BY p.data_execucao, p.id
    """, (cliente_id, prefixo)).fetchall()
    return [buscar_pedido_por_id(conn, r[0]) for r in ids]


def atualizar_status_pedido(conn: sqlite3.Connection, pedido_id: int, status: str) -> None:
    """Grava o status direto. A validação de transição fica em order_service/billing_service."""
    conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
