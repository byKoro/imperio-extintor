"""Regras de faturamento mensal e de ajustes (Fases 4 e 5). Sem Qt.

Decisões de negócio (confirmadas pelo usuário):
- O período de faturamento é o mês da data de execução, para pedidos e ajustes.
- Uma fatura por cliente por mês (imposto pelo schema).
- Ajuste: numeração NUMERO-A1, NUMERO-A2...; cobrado uma única vez.
- Modo DIFERENCA: cobra só os itens acrescentados.
- Modo INCREMENTADO: cobra total final menos o total original do pedido.
- Ajuste negativo não é suportado nesta fase.
- Data de execução em mês com fatura FECHADA é recusada (pedidos e ajustes).
- Fatura sem pedidos nem ajustes no período é recusada.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Optional

import db.repositories as repo
from app.core.calculations import calcular_valor_a_cobrar_ajuste_incrementado
from db.models import Ajuste, ItemAjuste, Faturamento, FaturamentoItem

STATUS_PEDIDO_EXECUTADO = "EXECUTADO"
STATUS_PEDIDO_FATURADO = "FATURADO"
MODOS_AJUSTE = ("DIFERENCA", "INCREMENTADO")
STATUS_FATURA_ABERTO = "ABERTO"
STATUS_FATURA_FECHADO = "FECHADO"


@contextmanager
def _transacao(conn: sqlite3.Connection) -> Iterator[None]:
    """Abre transação só se o chamador não tiver uma aberta (reentrante)."""
    abriu = False
    if not conn.in_transaction:
        conn.execute("BEGIN TRANSACTION;")
        abriu = True
    try:
        yield
        if abriu:
            conn.commit()
    except Exception:
        if abriu:
            conn.rollback()
        raise


def _mes_ano(data_iso: str) -> tuple[int, int]:
    try:
        d = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"Data inválida: '{data_iso}'. Use o formato AAAA-MM-DD e uma data existente.")
    return d.month, d.year


def verificar_data_execucao_permitida(conn: sqlite3.Connection, cliente_id: int, data_execucao_iso: str) -> None:
    """Recusa data de execução em mês cuja fatura do cliente já está FECHADA."""
    mes, ano = _mes_ano(data_execucao_iso)
    if repo.verificar_mes_fechado(conn, cliente_id, mes, ano):
        raise ValueError(
            f"O mês {mes:02d}/{ano} já está com faturamento fechado para este cliente. "
            "Não é possível lançar data de execução nesse mês."
        )


def gerar_proximo_numero_ajuste(conn: sqlite3.Connection, pedido_id: int) -> str:
    pedido = repo.buscar_pedido_por_id(conn, pedido_id)
    if pedido is None:
        raise ValueError(f"Pedido {pedido_id} não encontrado.")
    n = repo.obter_quantidade_ajustes_pedido(conn, pedido_id) + 1
    return f"{pedido.numero_pedido}-A{n}"


def validar_criacao_ajuste(
    conn: sqlite3.Connection, pedido_id: int, data_execucao: Optional[str], valor_cobrado: float
) -> None:
    pedido = repo.buscar_pedido_por_id(conn, pedido_id)
    if pedido is None:
        raise ValueError(f"Pedido {pedido_id} não encontrado.")
    if pedido.status not in (STATUS_PEDIDO_EXECUTADO, STATUS_PEDIDO_FATURADO):
        raise ValueError("Ajuste só pode ser criado para pedido EXECUTADO ou FATURADO.")
    if not data_execucao:
        raise ValueError("O ajuste precisa de data de execução.")
    _mes_ano(data_execucao)  # valida formato e calendário
    if valor_cobrado < 0:
        raise ValueError("Ajuste com valor negativo não é suportado nesta fase.")
    verificar_data_execucao_permitida(conn, pedido.cliente_id, data_execucao)


def criar_ajuste_completo(
    conn: sqlite3.Connection,
    pedido_id: int,
    modo_geracao: str,
    data_emissao: str,
    data_execucao: str,
    itens: List[ItemAjuste],
    observacoes: Optional[str] = None,
    total_final: Optional[float] = None,
) -> int:
    """Cria ajuste e seus itens. Modo INCREMENTADO exige total_final."""
    if modo_geracao not in MODOS_AJUSTE:
        raise ValueError(f"Modo de ajuste inválido: '{modo_geracao}'.")

    itens_pedido = repo.listar_itens_pedido(conn, pedido_id)
    total_original = round(sum(i.valor_total for i in itens_pedido), 2)

    if modo_geracao == "DIFERENCA":
        valor = round(sum(i.quantidade * i.preco_unitario for i in itens), 2)
    else:
        if total_final is None:
            raise ValueError("Modo INCREMENTADO exige o total final do pedido.")
        valor = calcular_valor_a_cobrar_ajuste_incrementado(total_final, total_original)

    validar_criacao_ajuste(conn, pedido_id, data_execucao, valor)

    numero = gerar_proximo_numero_ajuste(conn, pedido_id)
    ajuste = Ajuste(
        pedido_id=pedido_id,
        numero_ajuste=numero,
        data_emissao=data_emissao,
        data_execucao=data_execucao,
        modo_geracao=modo_geracao,
        status="PENDENTE",
        valor_cobrado=valor,
        observacoes=observacoes,
    )
    with _transacao(conn):
        ajuste_id = repo.criar_ajuste(conn, ajuste)
        for ordem, item in enumerate(itens):
            item.ajuste_id = ajuste_id
            item.ordem = ordem
            repo.adicionar_item_ajuste(conn, item)
    return ajuste_id


def gerar_fatura_mensal(
    conn: sqlite3.Connection, cliente_id: int, mes_referencia: int, ano_referencia: int,
    observacoes: Optional[str] = None,
) -> int:
    if repo.buscar_faturamento_por_periodo(conn, cliente_id, mes_referencia, ano_referencia):
        raise ValueError(f"Já existe fatura deste cliente para {mes_referencia:02d}/{ano_referencia}.")

    pedidos = repo.listar_pedidos_executados_periodo(conn, cliente_id, mes_referencia, ano_referencia)
    ajustes = repo.listar_ajustes_pendentes_por_periodo(conn, cliente_id, mes_referencia, ano_referencia)
    if not pedidos and not ajustes:
        raise ValueError("Não existem pedidos executados ou ajustes pendentes para faturar no período informado.")

    total_pedidos = sum(
        sum(i.valor_total for i in repo.listar_itens_pedido(conn, p.id)) for p in pedidos
    )
    total_ajustes = sum(a.valor_cobrado for a in ajustes)

    with _transacao(conn):
        fatura_id = repo.criar_faturamento(conn, Faturamento(
            cliente_id=cliente_id,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            total_geral=round(total_pedidos + total_ajustes, 2),
            status=STATUS_FATURA_ABERTO,
            observacoes=observacoes,
        ))
        for p in pedidos:
            repo.adicionar_item_faturamento(conn, FaturamentoItem(
                faturamento_id=fatura_id, pedido_id=p.id,
                valor_cobrado=round(sum(i.valor_total for i in repo.listar_itens_pedido(conn, p.id)), 2),
            ))
        for a in ajustes:
            repo.adicionar_item_faturamento(conn, FaturamentoItem(
                faturamento_id=fatura_id, ajuste_id=a.id, valor_cobrado=a.valor_cobrado,
            ))
    return fatura_id


def fechar_fatura(conn: sqlite3.Connection, faturamento_id: int, data_fechamento: Optional[str] = None) -> None:
    """Fecha a fatura: pedidos e ajustes incluídos passam a FATURADO."""
    fatura = repo.buscar_faturamento_por_id(conn, faturamento_id)
    if fatura is None:
        raise ValueError(f"Faturamento {faturamento_id} não encontrado.")
    if fatura.status == STATUS_FATURA_FECHADO:
        raise ValueError("Esta fatura já está fechada.")

    with _transacao(conn):
        for item in repo.listar_itens_faturamento(conn, faturamento_id):
            if item.pedido_id is not None:
                repo.atualizar_status_pedido(conn, item.pedido_id, STATUS_PEDIDO_FATURADO)
            if item.ajuste_id is not None:
                repo.marcar_ajuste_faturado(conn, item.ajuste_id, faturamento_id)
        fatura.status = STATUS_FATURA_FECHADO
        fatura.data_fechamento = data_fechamento or date.today().isoformat()
        repo.atualizar_faturamento(conn, fatura)


def obter_historico_acumulado_pedido(conn: sqlite3.Connection, pedido_id: int) -> Dict[str, Any]:
    """Total acumulado = valor original do pedido + valor_cobrado de cada ajuste."""
    valor_original = round(sum(i.valor_total for i in repo.listar_itens_pedido(conn, pedido_id)), 2)
    ajustes = repo.listar_ajustes_do_pedido(conn, pedido_id)
    total = round(valor_original + sum(a.valor_cobrado for a in ajustes), 2)
    return {
        "valor_original": valor_original,
        "ajustes": [
            {"numero": a.numero_ajuste, "modo": a.modo_geracao, "valor_cobrado": a.valor_cobrado}
            for a in ajustes
        ],
        "total_acumulado": total,
    }
