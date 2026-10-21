"""Serviço de gerenciamento e regras de negócio de pedidos.

Camada de domínio pura (sem interface gráfica ou dependências de Qt).
"""

import re
import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple
from db.models import Pedido, ItemPedido
import db.repositories as repo

# Constantes de status
STATUS_PEDIDO_ABERTO = "ABERTO"
STATUS_PEDIDO_EXECUTADO = "EXECUTADO"
STATUS_PEDIDO_FATURADO = "FATURADO"
STATUS_PEDIDO_PAGO = "PAGO"

STATUS_VALIDOS = {
    STATUS_PEDIDO_ABERTO,
    STATUS_PEDIDO_EXECUTADO,
    STATUS_PEDIDO_FATURADO,
    STATUS_PEDIDO_PAGO,
}


def validar_formato_data_iso(data_str: Optional[str]) -> bool:
    """Valida se uma data está no formato estrito YYYY-MM-DD e é válida no calendário."""
    if not data_str or not isinstance(data_str, str):
        return False
    data_limpa = data_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_limpa):
        return False
    try:
        datetime.strptime(data_limpa, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validar_transicao_status(
    status_atual: str,
    novo_status: str,
    data_execucao: Optional[str] = None
) -> None:
    """Valida as regras de transição de status do pedido.
    
    Regras:
    - ABERTO -> EXECUTADO: exige data_execucao válida (obrigatória).
    - EXECUTADO -> FATURADO: permitido manualmente.
    - ABERTO -> FATURADO: recusado (precisa estar EXECUTADO antes).
    - EXECUTADO -> ABERTO: recusado (sem reversão).
    - FATURADO -> PAGO: permitido.
    - FATURADO / PAGO: não podem transitar para ABERTO ou EXECUTADO.
    """
    if novo_status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido: '{novo_status}'. Permitidos: {STATUS_VALIDOS}")

    if status_atual == novo_status:
        # Se for manter EXECUTADO, ainda deve validar se tem data de execução
        if novo_status == STATUS_PEDIDO_EXECUTADO and not validar_formato_data_iso(data_execucao):
            raise ValueError("Transição para EXECUTADO exige a data de execução preenchida. Data de execução é obrigatória.")
        return

    if status_atual == STATUS_PEDIDO_ABERTO:
        if novo_status == STATUS_PEDIDO_EXECUTADO:
            if not validar_formato_data_iso(data_execucao):
                raise ValueError("Transição para EXECUTADO exige a data de execução preenchida. Data de execução é obrigatória.")
        elif novo_status == STATUS_PEDIDO_FATURADO:
            raise ValueError("Pedido precisa estar EXECUTADO antes de ser FATURADO.")
        elif novo_status == STATUS_PEDIDO_PAGO:
            raise ValueError("Pedido precisa estar FATURADO antes de ser PAGO.")

    elif status_atual == STATUS_PEDIDO_EXECUTADO:
        if novo_status == STATUS_PEDIDO_ABERTO:
            raise ValueError("Transição de status inválida: EXECUTADO -> ABERTO não é permitida.")
        elif novo_status == STATUS_PEDIDO_FATURADO:
            pass  # Permitido marcar Faturado
        elif novo_status == STATUS_PEDIDO_PAGO:
            raise ValueError("Pedido precisa ser FATURADO antes de ser PAGO.")

    elif status_atual in (STATUS_PEDIDO_FATURADO, STATUS_PEDIDO_PAGO):
        if status_atual == STATUS_PEDIDO_FATURADO and novo_status == STATUS_PEDIDO_PAGO:
            pass  # Permitido
        else:
            raise PermissionError(f"Pedido faturado não pode retornar para status '{novo_status}' ou ser alterado.")


def verificar_permissao_edicao(pedido: Pedido) -> None:
    """Valida se o pedido pode ser editado.
    
    Regra:
    - ABERTO e EXECUTADO: editáveis.
    - FATURADO e PAGO: bloqueados para qualquer edição.
    """
    if pedido.status in (STATUS_PEDIDO_FATURADO, STATUS_PEDIDO_PAGO):
        raise PermissionError(f"Pedido com status '{pedido.status}' está bloqueado para edição.")


def validar_numero_pedido(
    conn: sqlite3.Connection,
    cliente_id: int,
    numero_pedido: str,
    exceto_pedido_id: Optional[int] = None
) -> None:
    """Valida que o número de pedido foi informado e é único para o cliente."""
    num_limpo = str(numero_pedido).strip() if numero_pedido else ""
    if not num_limpo:
        raise ValueError("O número do pedido é obrigatório.")

    if repo.verificar_numero_pedido_existe(conn, cliente_id, num_limpo, exceto_id=exceto_pedido_id):
        raise ValueError(f"Já existe um pedido com o número '{num_limpo}' cadastrado para este cliente.")


def transitar_status(
    conn: sqlite3.Connection,
    pedido_id: int,
    novo_status: str,
    data_execucao: Optional[str] = None
) -> None:
    """Altera o status de um pedido no banco validando a máquina de estados."""
    pedido = repo.buscar_pedido_por_id(conn, pedido_id)
    if not pedido:
        raise ValueError(f"Pedido {pedido_id} não encontrado.")

    data_exec = data_execucao if data_execucao is not None else pedido.data_execucao
    validar_transicao_status(pedido.status, novo_status, data_exec)

    if novo_status == STATUS_PEDIDO_EXECUTADO and data_exec:
        mes, ano = int(data_exec[5:7]), int(data_exec[0:4])
        if repo.verificar_mes_fechado(conn, pedido.cliente_id, mes, ano):
            raise ValueError(
                f"O mês {mes:02d}/{ano} já está com faturamento fechado para este cliente. "
                "Não é possível lançar data de execução nesse mês."
            )

    pedido.status = novo_status
    if novo_status == STATUS_PEDIDO_EXECUTADO:
        pedido.data_execucao = data_exec

    repo.atualizar_pedido(conn, pedido)
    conn.commit()


def duplicar_pedido(
    conn: sqlite3.Connection,
    pedido_origem_id: int,
    novo_numero_pedido: str,
    nova_data_emissao: str
) -> int:
    """Duplica um pedido gerando uma cópia em status ABERTO com quantidades e preços zerados.
    
    Regras:
    - O novo número é obrigatório e deve ser diferente do pedido original.
    - O novo número não pode existir para o mesmo cliente.
    - O status é fixado em ABERTO e data_execucao é limpa (None).
    - Os itens originais são copiados com quantidade=0.0 e preco_unitario=0.0.
    """
    pedido_orig = repo.buscar_pedido_por_id(conn, pedido_origem_id)
    if not pedido_orig:
        raise ValueError(f"Pedido de origem {pedido_origem_id} não encontrado.")

    novo_numero = str(novo_numero_pedido).strip() if novo_numero_pedido else ""
    if not novo_numero:
        raise ValueError("O novo número do pedido é obrigatório.")

    if novo_numero == pedido_orig.numero_pedido:
        raise ValueError("O número do novo pedido duplicado deve ser diferente do pedido original.")

    validar_numero_pedido(conn, pedido_orig.cliente_id, novo_numero)

    if not validar_formato_data_iso(nova_data_emissao):
        raise ValueError("Data de emissão inválida para o novo pedido.")

    novo_pedido = Pedido(
        cliente_id=pedido_orig.cliente_id,
        loja_id=pedido_orig.loja_id,
        numero_pedido=novo_numero,
        data_emissao=nova_data_emissao,
        data_execucao=None,
        status=STATUS_PEDIDO_ABERTO,
        observacoes=pedido_orig.observacoes,
        prazo_pagamento=pedido_orig.prazo_pagamento,
        forma_pagamento=pedido_orig.forma_pagamento,
        prazo_entrega=pedido_orig.prazo_entrega,
        texto_impostos=pedido_orig.texto_impostos,
    )

    itens_orig = repo.listar_itens_pedido(conn, pedido_origem_id)
    novos_itens = []
    for it in itens_orig:
        novos_itens.append(ItemPedido(
            produto_id=it.produto_id,
            secao=it.secao,
            descricao=it.descricao,
            quantidade=0.0,
            unidade=it.unidade,
            preco_unitario=0.0,
            valor_total=0.0,
            ordem=it.ordem,
        ))

    novo_id = repo.salvar_pedido_completo(conn, novo_pedido, novos_itens)
    return novo_id


def validar_exclusao_pedido(conn: sqlite3.Connection, pedido_id: int) -> None:
    """Valida se um pedido pode ser excluído fisicamente.
    
    Regras:
    - Apenas pedidos com status ABERTO podem ser excluídos.
    - Pedidos com status EXECUTADO, FATURADO ou PAGO são recusados com PermissionError.
    - Se houver ajustes vinculados, a exclusão é recusada com PermissionError.
    - Se houver itens de faturamento vinculados, a exclusão é recusada com PermissionError.
    """
    pedido = repo.buscar_pedido_por_id(conn, pedido_id)
    if not pedido:
        raise ValueError(f"Pedido {pedido_id} não encontrado.")

    if pedido.status != STATUS_PEDIDO_ABERTO:
        raise PermissionError(f"Apenas pedidos com status ABERTO podem ser excluídos. Pedido atual: '{pedido.status}'.")

    # Verifica vínculos reais em ajustes
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ajustes WHERE pedido_id = ?", (pedido_id,))
    if cur.fetchone()[0] > 0:
        raise PermissionError("Não é possível excluir o pedido: existem faturamentos complementares (ajustes) vinculados a ele.")

    # Verifica vínculos reais em faturamento_itens
    cur.execute("SELECT COUNT(*) FROM faturamento_itens WHERE pedido_id = ?", (pedido_id,))
    if cur.fetchone()[0] > 0:
        raise PermissionError("Não é possível excluir o pedido: este pedido já foi incluído em um fechamento de faturamento.")


def excluir_pedido(conn: sqlite3.Connection, pedido_id: int) -> None:
    """Valida e executa a exclusão segura do pedido."""
    validar_exclusao_pedido(conn, pedido_id)
    repo.excluir_pedido_seguro(conn, pedido_id)
