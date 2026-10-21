"""Testes da Fase 4 (ajustes) e Fase 5 (faturamento mensal). Dados fictícios, banco :memory:."""

import sqlite3

import pytest

import db.repositories as repo
from app.core import billing_service as bs
from app.core import order_service as os_
from db.models import Cliente, Loja, Pedido, ItemPedido, ItemAjuste, Faturamento


def _cliente(conn: sqlite3.Connection) -> int:
    return repo.criar_cliente(conn, Cliente(razao_social="CLIENTE FICTICIO LTDA"))


def _pedido(conn, cliente_id, numero, emissao, itens, executar=None):
    """Cria pedido com itens avulsos (produto_id=None). Se executar, transita para EXECUTADO."""
    loja_id = repo.criar_loja(conn, Loja(
        cliente_id=cliente_id, codigo_loja=f"L-{numero}", nome_site="Site Ficticio",
        cidade="Cidade A", uf="SP", modelo_bandeira="MODA", vencimento="2026-01-01",
    ))
    pid = repo.criar_pedido(conn, Pedido(
        cliente_id=cliente_id, loja_id=loja_id, numero_pedido=numero,
        data_emissao=emissao, status="ABERTO",
    ))
    for ordem, (desc, qtd, preco) in enumerate(itens):
        repo.adicionar_item_pedido(conn, ItemPedido(
            pedido_id=pid, secao="SERVICO", descricao=desc, quantidade=qtd,
            unidade="SV", preco_unitario=preco, ordem=ordem,
        ))
    conn.commit()
    if executar:
        os_.transitar_status(conn, pid, "EXECUTADO", executar)
    return pid


def _itens_ajuste(*itens):
    return [ItemAjuste(secao="SERVICO", descricao=d, quantidade=q, unidade="SV", preco_unitario=p)
            for d, q, p in itens]


# ---------- Schema: restrições reais ----------

def test_unicidade_fatura_cliente_mes_ano(conn):
    """Schema: CONSTRAINT uq_faturamento_cliente_mes_ano UNIQUE (cliente_id, mes_referencia, ano_referencia)."""
    cid = _cliente(conn)
    conn.execute("INSERT INTO faturamentos (cliente_id, mes_referencia, ano_referencia) VALUES (?, 3, 2026)", (cid,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO faturamentos (cliente_id, mes_referencia, ano_referencia) VALUES (?, 3, 2026)", (cid,))


def test_chk_origem_faturamento_item(conn):
    """Schema: CONSTRAINT chk_faturamento_item_origem CHECK (pedido_id XOR ajuste_id)."""
    cid = _cliente(conn)
    fid = repo.criar_faturamento(conn, Faturamento(cliente_id=cid, mes_referencia=2, ano_referencia=2026))
    pid = _pedido(conn, cid, "P-CHK", "2026-02-01", [("Servico", 1, 10.0)], executar="2026-02-02")
    aid = repo.criar_ajuste(conn, _ajuste_minimo(pid))
    with pytest.raises(sqlite3.IntegrityError):  # ambos nulos
        conn.execute("INSERT INTO faturamento_itens (faturamento_id, valor_cobrado) VALUES (?, 1)", (fid,))
    with pytest.raises(sqlite3.IntegrityError):  # ambos preenchidos
        conn.execute("INSERT INTO faturamento_itens (faturamento_id, pedido_id, ajuste_id, valor_cobrado) VALUES (?, ?, ?, 1)",
                     (fid, pid, aid))


def _ajuste_minimo(pedido_id):
    from db.models import Ajuste
    return Ajuste(pedido_id=pedido_id, numero_ajuste=f"X-{pedido_id}-A1", data_emissao="2026-02-03",
                  data_execucao="2026-02-03", modo_geracao="DIFERENCA")


# ---------- Data de execução em mês fechado ----------

def _fechar_mes(conn, cid, mes, ano):
    repo.criar_faturamento(conn, Faturamento(cliente_id=cid, mes_referencia=mes, ano_referencia=ano,
                                             status="FECHADO", data_fechamento=f"{ano}-{mes:02d}-28"))
    conn.commit()


def test_pedido_nao_aceita_execucao_em_mes_fechado(conn):
    cid = _cliente(conn)
    _fechar_mes(conn, cid, 3, 2026)
    pid = _pedido(conn, cid, "P-FECH", "2026-03-01", [("Servico", 1, 10.0)])
    with pytest.raises(ValueError, match="fechado"):
        os_.transitar_status(conn, pid, "EXECUTADO", "2026-03-15")


def test_ajuste_nao_aceita_execucao_em_mes_fechado(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-AJF", "2026-02-01", [("Servico", 1, 100.0)], executar="2026-02-10")
    _fechar_mes(conn, cid, 3, 2026)
    with pytest.raises(ValueError, match="fechado"):
        bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-03-20", "2026-03-20",
                                 _itens_ajuste(("Extra", 1, 10.0)))


def test_mes_aberto_aceita_ajuste(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-ABERTO", "2026-02-01", [("Servico", 1, 100.0)], executar="2026-02-10")
    _fechar_mes(conn, cid, 3, 2026)
    aid = bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-04-10", "2026-04-10",
                                   _itens_ajuste(("Extra", 1, 10.0)))
    assert aid > 0


# ---------- Regras do ajuste ----------

def test_valor_negativo_nao_suportado_nesta_fase(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-NEG", "2026-02-01", [("Servico", 5, 100.0)], executar="2026-02-10")  # total 500
    with pytest.raises(ValueError, match="negativo"):
        bs.criar_ajuste_completo(conn, pid, "INCREMENTADO", "2026-02-20", "2026-02-20",
                                 _itens_ajuste(("Recarga", 1, 10.0)), total_final=400.0)


def test_ajuste_so_para_pedido_executado(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-ABERTO2", "2026-02-01", [("Servico", 1, 100.0)])
    with pytest.raises(ValueError, match="EXECUTADO"):
        bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-02-20", "2026-02-20",
                                 _itens_ajuste(("Extra", 1, 10.0)))


def test_numeracao_sequencial_dos_ajustes(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "20251954", "2026-02-01", [("Servico", 1, 100.0)], executar="2026-02-10")
    bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-02-20", "2026-02-20", _itens_ajuste(("A", 1, 10.0)))
    bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-02-21", "2026-02-21", _itens_ajuste(("B", 1, 20.0)))
    numeros = [a.numero_ajuste for a in repo.listar_ajustes_do_pedido(conn, pid)]
    assert numeros == ["20251954-A1", "20251954-A2"]


def test_modo_diferenca_soma_os_itens_acrescentados(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-DIF", "2026-02-01", [("Servico", 5, 100.0)], executar="2026-02-10")  # 500
    aid = bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-02-20", "2026-02-20",
                                   _itens_ajuste(("Recarga", 2, 50.0), ("Valvula", 1, 30.0)))
    assert repo.buscar_ajuste_por_id(conn, aid).valor_cobrado == 130.0


def test_modo_incrementado_cobra_total_final_menos_original(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-INC", "2026-02-01", [("Servico", 5, 100.0)], executar="2026-02-10")  # 500
    aid = bs.criar_ajuste_completo(conn, pid, "INCREMENTADO", "2026-02-20", "2026-02-20",
                                   _itens_ajuste(("Recarga", 1, 120.0)), total_final=620.0)
    assert repo.buscar_ajuste_por_id(conn, aid).valor_cobrado == 120.0


def test_historico_acumulado_usa_valor_cobrado_nao_total_final(conn):
    """Original 500 + ajuste INCREMENTADO que leva o total a 620 (cobrança de 120) = acumulado 620, não 740."""
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-HIST", "2026-02-01", [("Servico", 5, 100.0)], executar="2026-02-10")
    bs.criar_ajuste_completo(conn, pid, "INCREMENTADO", "2026-02-20", "2026-02-20",
                             _itens_ajuste(("Recarga", 1, 120.0)), total_final=620.0)
    historico = bs.obter_historico_acumulado_pedido(conn, pid)
    assert historico["valor_original"] == 500.0
    assert historico["total_acumulado"] == 620.0


# ---------- Faturamento mensal ----------

def test_periodo_pela_execucao_nao_pela_emissao(conn):
    cid = _cliente(conn)
    _pedido(conn, cid, "P-PER", "2026-01-10", [("Servico", 1, 100.0)], executar="2026-02-15")
    with pytest.raises(ValueError, match="Não existem"):
        bs.gerar_fatura_mensal(conn, cid, 1, 2026)
    fid = bs.gerar_fatura_mensal(conn, cid, 2, 2026)
    itens = repo.listar_itens_faturamento(conn, fid)
    assert len(itens) == 1 and itens[0].pedido_id is not None


def test_ajuste_entra_na_fatura_do_mes_da_sua_execucao(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-AJPER", "2026-01-05", [("Servico", 1, 100.0)], executar="2026-01-15")
    bs.criar_ajuste_completo(conn, pid, "DIFERENCA", "2026-02-20", "2026-03-05", _itens_ajuste(("Extra", 1, 30.0)))
    with pytest.raises(ValueError, match="Não existem"):
        bs.gerar_fatura_mensal(conn, cid, 2, 2026)
    fid = bs.gerar_fatura_mensal(conn, cid, 3, 2026)
    itens = repo.listar_itens_faturamento(conn, fid)
    assert [i.ajuste_id is not None for i in itens] == [True]


def test_fatura_sem_itens_recusada(conn):
    cid = _cliente(conn)
    with pytest.raises(ValueError, match="Não existem pedidos executados ou ajustes pendentes"):
        bs.gerar_fatura_mensal(conn, cid, 5, 2026)


def test_uma_fatura_por_cliente_por_mes(conn):
    cid = _cliente(conn)
    _pedido(conn, cid, "P-UNI", "2026-02-01", [("Servico", 1, 100.0)], executar="2026-02-10")
    bs.gerar_fatura_mensal(conn, cid, 2, 2026)
    with pytest.raises(ValueError, match="Já existe fatura"):
        bs.gerar_fatura_mensal(conn, cid, 2, 2026)


def test_fechar_fatura_marca_pedidos_e_ajustes_como_faturados(conn):
    cid = _cliente(conn)
    pid = _pedido(conn, cid, "P-FECHA", "2026-02-01", [("Servico", 5, 100.0)], executar="2026-02-15")
    aid = bs.criar_ajuste_completo(conn, pid, "INCREMENTADO", "2026-02-20", "2026-02-20",
                                   _itens_ajuste(("Recarga", 1, 120.0)), total_final=620.0)
    fid = bs.gerar_fatura_mensal(conn, cid, 2, 2026)
    assert repo.buscar_faturamento_por_id(conn, fid).total_geral == 620.0

    bs.fechar_fatura(conn, fid, data_fechamento="2026-02-28")

    fatura = repo.buscar_faturamento_por_id(conn, fid)
    assert fatura.status == "FECHADO"
    assert fatura.data_fechamento == "2026-02-28"
    assert repo.buscar_pedido_por_id(conn, pid).status == "FATURADO"
    assert repo.buscar_ajuste_por_id(conn, aid).status == "FATURADO"
    assert repo.buscar_ajuste_por_id(conn, aid).faturamento_id == fid


def test_fatura_fechada_nao_fecha_de_novo(conn):
    cid = _cliente(conn)
    _pedido(conn, cid, "P-DUP", "2026-02-01", [("Servico", 1, 100.0)], executar="2026-02-10")
    fid = bs.gerar_fatura_mensal(conn, cid, 2, 2026)
    bs.fechar_fatura(conn, fid, data_fechamento="2026-02-28")
    with pytest.raises(ValueError, match="já está fechada"):
        bs.fechar_fatura(conn, fid, data_fechamento="2026-02-28")
