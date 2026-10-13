"""Testes unitários de regras de negócio, serviço de pedidos e persistência.

Testes executados sem dependência de Qt, utilizando banco SQLite em memória.
"""

import sqlite3
import pytest
from db.connection import get_connection
from db.migrations import run_migrations
from db.models import Cliente, Loja, Produto, PrecoCliente, Pedido, ItemPedido, Ajuste
import db.repositories as repo
import app.core.order_service as service


@pytest.fixture
def conn():
    """Retorna uma conexão em memória com todas as migrações aplicadas."""
    conexao = get_connection(":memory:")
    run_migrations(conexao)
    yield conexao
    conexao.close()


@pytest.fixture
def setup_dados(conn):
    """Cria cliente, lojas e produtos fictícios para os testes."""
    c1_id = repo.criar_cliente(conn, Cliente(razao_social="EMPRESA CLIENTE A"))
    c2_id = repo.criar_cliente(conn, Cliente(razao_social="EMPRESA CLIENTE B"))

    # Lojas do cliente A: 2 ativas e 1 inativa
    l1_id = repo.criar_loja(conn, Loja(cliente_id=c1_id, codigo_loja="101", nome_site="LOJA ATIVA 1", cidade="SP", uf="SP", modelo_bandeira="MODA", ativo=1))
    l2_id = repo.criar_loja(conn, Loja(cliente_id=c1_id, codigo_loja="102", nome_site="LOJA ATIVA 2", cidade="SP", uf="SP", modelo_bandeira="MODA", ativo=1))
    l_inativa_id = repo.criar_loja(conn, Loja(cliente_id=c1_id, codigo_loja="103", nome_site="LOJA INATIVA", cidade="SP", uf="SP", modelo_bandeira="MODA", ativo=0))

    # Loja do cliente B
    lb_id = repo.criar_loja(conn, Loja(cliente_id=c2_id, codigo_loja="201", nome_site="LOJA B", cidade="RJ", uf="RJ", modelo_bandeira="CASA", ativo=1))

    # Produtos
    p1_id = repo.criar_produto(conn, Produto(nome="EXTINTOR AP 10L", tipo="SERVICO", unidade="SV", preco_padrao=50.0))
    p2_id = repo.criar_produto(conn, Produto(nome="MANOMETRO", tipo="PECA", unidade="UN", preco_padrao=15.0))

    conn.commit()
    return {
        "c1_id": c1_id,
        "c2_id": c2_id,
        "l1_id": l1_id,
        "l2_id": l2_id,
        "l_inativa_id": l_inativa_id,
        "lb_id": lb_id,
        "p1_id": p1_id,
        "p2_id": p2_id,
    }


def test_transicoes_status_pedido(conn, setup_dados):
    """Testa a máquina de estados completa de pedidos."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]

    ped = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-01", data_emissao="2026-10-13", status="ABERTO")
    ped_id = repo.salvar_pedido_completo(conn, ped, [])

    # 1. ABERTO -> EXECUTADO sem data: deve falhar
    with pytest.raises(ValueError) as exc:
        service.transitar_status(conn, ped_id, "EXECUTADO", data_execucao="")
    assert "Data de execução é obrigatória" in str(exc.value)

    # 2. ABERTO -> FATURADO diretamente: recusado
    with pytest.raises(ValueError) as exc:
        service.transitar_status(conn, ped_id, "FATURADO")
    assert "Pedido precisa estar EXECUTADO antes de ser FATURADO" in str(exc.value)

    # 3. ABERTO -> EXECUTADO com data válida: sucesso
    service.transitar_status(conn, ped_id, "EXECUTADO", data_execucao="2026-10-14")
    p_atual = repo.buscar_pedido_por_id(conn, ped_id)
    assert p_atual.status == "EXECUTADO"
    assert p_atual.data_execucao == "2026-10-14"

    # 4. EXECUTADO -> ABERTO: reversão recusada
    with pytest.raises(ValueError) as exc:
        service.transitar_status(conn, ped_id, "ABERTO")
    assert "não é permitida" in str(exc.value)

    # 5. EXECUTADO -> FATURADO: permitido
    service.transitar_status(conn, ped_id, "FATURADO")
    p_atual = repo.buscar_pedido_por_id(conn, ped_id)
    assert p_atual.status == "FATURADO"

    # 6. FATURADO -> PAGO: permitido
    service.transitar_status(conn, ped_id, "PAGO")
    p_atual = repo.buscar_pedido_por_id(conn, ped_id)
    assert p_atual.status == "PAGO"

    # 7. PAGO -> qualquer outro status: bloqueado
    with pytest.raises(PermissionError):
        service.transitar_status(conn, ped_id, "EXECUTADO")


def test_permissao_edicao_por_status(conn, setup_dados):
    """Pedidos ABERTO e EXECUTADO são editáveis; FATURADO e PAGO são bloqueados."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]

    p_aberto = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-ED-1", data_emissao="2026-10-13", status="ABERTO")
    service.verificar_permissao_edicao(p_aberto)  # Não levanta exceção

    p_exec = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-ED-2", data_emissao="2026-10-13", data_execucao="2026-10-14", status="EXECUTADO")
    service.verificar_permissao_edicao(p_exec)  # Não levanta exceção

    p_fat = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-ED-3", data_emissao="2026-10-13", status="FATURADO")
    with pytest.raises(PermissionError):
        service.verificar_permissao_edicao(p_fat)

    p_pago = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-ED-4", data_emissao="2026-10-13", status="PAGO")
    with pytest.raises(PermissionError):
        service.verificar_permissao_edicao(p_pago)


def test_unicidade_numero_pedido_criacao_e_edicao(conn, setup_dados):
    """Testa unicidade de número por cliente no cadastro e na edição."""
    c1_id = setup_dados["c1_id"]
    c2_id = setup_dados["c2_id"]
    l1_id = setup_dados["l1_id"]
    lb_id = setup_dados["lb_id"]

    # Cria pedido 1 no cliente A
    ped1 = Pedido(cliente_id=c1_id, loja_id=l1_id, numero_pedido="2026001", data_emissao="2026-10-13", status="ABERTO")
    ped1_id = repo.salvar_pedido_completo(conn, ped1, [])

    # Cria pedido 2 no cliente A
    ped2 = Pedido(cliente_id=c1_id, loja_id=l1_id, numero_pedido="2026002", data_emissao="2026-10-13", status="ABERTO")
    ped2_id = repo.salvar_pedido_completo(conn, ped2, [])

    # 1. Tentar criar pedido novo no cliente A com número repetido '2026001' deve falhar
    with pytest.raises(ValueError) as exc:
        service.validar_numero_pedido(conn, c1_id, "2026001")
    assert "Já existe um pedido" in str(exc.value)

    # 2. Criar com mesmo número '2026001' para cliente B é PERMITIDO (unicidade por cliente)
    service.validar_numero_pedido(conn, c2_id, "2026001")
    ped_c2 = Pedido(cliente_id=c2_id, loja_id=lb_id, numero_pedido="2026001", data_emissao="2026-10-13", status="ABERTO")
    repo.salvar_pedido_completo(conn, ped_c2, [])

    # 3. Na edição do pedido 1, manter o mesmo número '2026001' é PERMITIDO
    service.validar_numero_pedido(conn, c1_id, "2026001", exceto_pedido_id=ped1_id)

    # 4. Na edição do pedido 1, alterar para '2026002' (número do pedido 2 do mesmo cliente) é RECUSADO
    with pytest.raises(ValueError) as exc:
        service.validar_numero_pedido(conn, c1_id, "2026002", exceto_pedido_id=ped1_id)
    assert "Já existe um pedido" in str(exc.value)


def test_duplicar_pedido_regras(conn, setup_dados):
    """Duplicação exige novo número, zera quantidades e preços e clona itens."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]
    p_id = setup_dados["p1_id"]

    orig = Pedido(
        cliente_id=c_id, loja_id=l_id, numero_pedido="ORIG-100", data_emissao="2026-10-01",
        data_execucao="2026-10-05", status="EXECUTADO", observacoes="Obs do original",
        prazo_pagamento="45 dias", forma_pagamento="Boleto", prazo_entrega="15 dias", texto_impostos="Inclusos"
    )
    item_orig = ItemPedido(
        produto_id=p_id, secao="SERVICO", descricao="Recarga",
        quantidade=5.0, unidade="SV", preco_unitario=50.0, valor_total=250.0
    )
    orig_id = repo.salvar_pedido_completo(conn, orig, [item_orig])

    # 1. Duplicar com o mesmo número: RECUSADO
    with pytest.raises(ValueError) as exc:
        service.duplicar_pedido(conn, orig_id, "ORIG-100", "2026-10-13")
    assert "deve ser diferente" in str(exc.value)

    # 2. Duplicar com número já existente no cliente: RECUSADO
    repo.salvar_pedido_completo(conn, Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="JA-EXISTE", data_emissao="2026-10-01"), [])
    with pytest.raises(ValueError) as exc:
        service.duplicar_pedido(conn, orig_id, "JA-EXISTE", "2026-10-13")
    assert "Já existe um pedido" in str(exc.value)

    # 3. Duplicar com número novo válido: SUCESSO
    novo_id = service.duplicar_pedido(conn, orig_id, "CLONE-200", "2026-10-13")
    novo = repo.buscar_pedido_por_id(conn, novo_id)
    assert novo.numero_pedido == "CLONE-200"
    assert novo.data_emissao == "2026-10-13"
    assert novo.status == "ABERTO"
    assert novo.data_execucao is None
    assert novo.observacoes == "Obs do original"
    assert novo.prazo_pagamento == "45 dias"

    # Itens duplicados com quantidades e preços zerados
    novos_itens = repo.listar_itens_pedido(conn, novo_id)
    assert len(novos_itens) == 1
    assert novos_itens[0].descricao == "Recarga"
    assert novos_itens[0].quantidade == 0.0
    assert novos_itens[0].preco_unitario == 0.0
    assert novos_itens[0].valor_total == 0.0


def test_exclusao_status_e_vinculos_reais(conn, setup_dados):
    """Exclusão permitida apenas em ABERTO; bloqueada se houver status!=ABERTO ou vínculos reais."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]

    # 1. Pedido em EXECUTADO não pode ser excluído
    p_exec = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="P-EXEC", data_emissao="2026-10-13", data_execucao="2026-10-14", status="EXECUTADO")
    p_exec_id = repo.salvar_pedido_completo(conn, p_exec, [])
    with pytest.raises(PermissionError) as exc:
        service.excluir_pedido(conn, p_exec_id)
    assert "Apenas pedidos com status ABERTO podem ser excluídos" in str(exc.value)

    # 2. Pedido ABERTO sem vínculos pode ser excluído
    p_aberto = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="P-ABERTO", data_emissao="2026-10-13", status="ABERTO")
    p_aberto_id = repo.salvar_pedido_completo(conn, p_aberto, [ItemPedido(secao="PECA", descricao="Item", quantidade=1.0, unidade="UN", preco_unitario=10.0, valor_total=10.0)])
    service.excluir_pedido(conn, p_aberto_id)
    assert repo.buscar_pedido_por_id(conn, p_aberto_id) is None
    assert len(repo.listar_itens_pedido(conn, p_aberto_id)) == 0

    # 3. Pedido ABERTO com vínculo REAL em Ajuste (usando modo_geracao='DIFERENCA' e repo.criar_ajuste)
    p_com_ajuste = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="P-AJUSTE", data_emissao="2026-10-13", status="ABERTO")
    p_com_ajuste_id = repo.salvar_pedido_completo(conn, p_com_ajuste, [])
    ajuste_real = Ajuste(
        pedido_id=p_com_ajuste_id,
        numero_ajuste="AJ-REAL-01",
        data_emissao="2026-10-14",
        modo_geracao="DIFERENCA",
        status="PENDENTE",
        valor_cobrado=30.0
    )
    repo.criar_ajuste(conn, ajuste_real)
    conn.commit()

    with pytest.raises(PermissionError) as exc:
        service.excluir_pedido(conn, p_com_ajuste_id)
    assert "ajustes" in str(exc.value).lower()

    # 4. Pedido ABERTO com vínculo REAL em faturamento_itens
    p_com_fat = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="P-FAT", data_emissao="2026-10-13", status="ABERTO")
    p_com_fat_id = repo.salvar_pedido_completo(conn, p_com_fat, [])
    # Inserção real no schema de faturamentos e faturamento_itens
    conn.execute("INSERT INTO faturamentos (cliente_id, mes_referencia, ano_referencia) VALUES (?, 10, 2026)", (c_id,))
    fat_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO faturamento_itens (faturamento_id, pedido_id, valor_cobrado) VALUES (?, ?, 100.0)", (fat_id, p_com_fat_id))
    conn.commit()

    with pytest.raises(PermissionError) as exc:
        service.excluir_pedido(conn, p_com_fat_id)
    assert "faturamento" in str(exc.value).lower()


def test_listar_lojas_inativas_regra_combo(conn, setup_dados):
    """Novo pedido lista apenas lojas ativas; edição de pedido com loja inativa inclui ela especificamente."""
    c1_id = setup_dados["c1_id"]
    l_inativa_id = setup_dados["l_inativa_id"]

    # 1. Novo pedido: incluir_loja_id=None -> apenas lojas com ativo = 1
    lojas_novo = repo.listar_lojas_por_cliente(conn, c1_id, incluir_loja_id=None)
    ids_novo = [l.id for l in lojas_novo]
    assert l_inativa_id not in ids_novo
    assert len(lojas_novo) == 2  # As 2 ativas

    # 2. Edição de pedido legado: incluir_loja_id=l_inativa_id -> inclui ela
    lojas_edicao = repo.listar_lojas_por_cliente(conn, c1_id, incluir_loja_id=l_inativa_id)
    ids_edicao = [l.id for l in lojas_edicao]
    assert l_inativa_id in ids_edicao
    assert len(lojas_edicao) == 3


def test_transacoes_reentrantes(conn, setup_dados):
    """salvar_pedido_completo e excluir_pedido_seguro não comitam nem fazem rollback próprios se chamador já abriu transação."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]

    # --- Caso 1: Salvar dentro de transação e rollback do chamador (prova ausência de commit próprio) ---
    conn.execute("BEGIN TRANSACTION;")
    assert conn.in_transaction is True

    ped1 = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-TX-ROLLBACK", data_emissao="2026-10-13", status="ABERTO")
    itens1 = [ItemPedido(secao="SERVICO", descricao="Recarga", quantidade=1.0, unidade="SV", preco_unitario=50.0, valor_total=50.0)]
    ped1_id = repo.salvar_pedido_completo(conn, ped1, itens1)

    assert conn.in_transaction is True  # Transação do chamador continua aberta
    conn.rollback()  # Chamador cancela
    assert conn.in_transaction is False
    # Como não houve commit próprio, o pedido não existe após o rollback
    assert repo.buscar_pedido_por_id(conn, ped1_id) is None

    # --- Caso 2: Salvar e Excluir dentro de transação e commit do chamador ---
    conn.execute("BEGIN TRANSACTION;")
    assert conn.in_transaction is True

    ped2 = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-TX-COMMIT", data_emissao="2026-10-13", status="ABERTO")
    ped2_id = repo.salvar_pedido_completo(conn, ped2, [])
    assert conn.in_transaction is True  # Transação continua válida

    # Executa exclusão dentro da mesma transação do chamador
    repo.excluir_pedido_seguro(conn, ped2_id)
    assert conn.in_transaction is True  # Transação continua válida para o chamador

    # Chamador ainda pode realizar outras operações na mesma transação
    conn.execute("INSERT INTO clientes (razao_social) VALUES ('NOVO CLIENTE NA MESMA TX')")
    assert conn.in_transaction is True

    conn.commit()
    assert conn.in_transaction is False


def test_snapshot_preco_e_item_avulso(conn, setup_dados):
    """Itens gravam snapshot de preço; itens avulsos têm produto_id=None sem criar produto."""
    c_id = setup_dados["c1_id"]
    l_id = setup_dados["l1_id"]
    p_id = setup_dados["p1_id"]  # Preço padrão 50.0

    itens = [
        # Item do catálogo
        ItemPedido(produto_id=p_id, secao="SERVICO", descricao="Recarga Snapshot", quantidade=2.0, unidade="SV", preco_unitario=50.0, valor_total=100.0),
        # Item avulso
        ItemPedido(produto_id=None, secao="PECA", descricao="Suporte Especial Avulso", quantidade=1.0, unidade="UN", preco_unitario=35.0, valor_total=35.0)
    ]
    ped = Pedido(cliente_id=c_id, loja_id=l_id, numero_pedido="PED-SNAP", data_emissao="2026-10-13", status="ABERTO")
    ped_id = repo.salvar_pedido_completo(conn, ped, itens)

    # Altera o preço do produto no catálogo para 80.0
    conn.execute("UPDATE produtos SET preco_padrao = 80.0 WHERE id = ?", (p_id,))
    conn.commit()

    # O pedido gravado mantém snapshot inalterado (50.0)
    itens_salvos = repo.listar_itens_pedido(conn, ped_id)
    assert itens_salvos[0].preco_unitario == 50.0
    assert itens_salvos[0].valor_total == 100.0

    # Item avulso tem produto_id=None e não criou produto em produtos
    assert itens_salvos[1].produto_id is None
    assert itens_salvos[1].descricao == "Suporte Especial Avulso"
    assert itens_salvos[1].preco_unitario == 35.0
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM produtos WHERE nome = 'Suporte Especial Avulso'")
    assert cur.fetchone()[0] == 0
