"""Testes de interface gráfica de Pedidos com pytest-qt (offscreen) e banco em memória."""

import os
import sqlite3
import pytest
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QDialog

from db.connection import get_connection
from db.migrations import run_migrations
from db.models import Cliente, Loja, Produto, Pedido, ItemPedido
import db.repositories as repo
from ui.views.pedido_dialog import PedidoDialog, formatar_data_br_para_iso
from ui.views.pedidos_view import PedidosView, DataExecucaoDialog, DuplicarPedidoDialog


@pytest.fixture(autouse=True)
def setup_qt_offscreen():
    """Garante plataforma offscreen do Qt."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture
def conn():
    """Cria conexão em memória para testes de interface."""
    conexao = get_connection(":memory:")
    run_migrations(conexao)
    yield conexao
    conexao.close()


@pytest.fixture
def setup_dados_ui(conn):
    """Cria dados básicos fictícios para os testes de interface."""
    # Cliente 1 (ativo) e Cliente 2 (inativo)
    c_ativo_id = repo.criar_cliente(conn, Cliente(razao_social="CLIENTE ATIVO LTDA", ativo=1))
    c_inativo_id = repo.criar_cliente(conn, Cliente(razao_social="CLIENTE INATIVO LTDA", ativo=0))

    # Lojas do Cliente Ativo: 1 ativa e 1 inativa
    l_ativa_id = repo.criar_loja(conn, Loja(cliente_id=c_ativo_id, codigo_loja="L01", nome_site="SHOPPING A", cidade="SP", uf="SP", modelo_bandeira="MODA", ativo=1))
    l_inativa_id = repo.criar_loja(conn, Loja(cliente_id=c_ativo_id, codigo_loja="L02", nome_site="SHOPPING B", cidade="SP", uf="SP", modelo_bandeira="MODA", ativo=0))

    # Produtos
    p_serv_id = repo.criar_produto(conn, Produto(nome="RECARGA 10L", tipo="SERVICO", preco_padrao=50.0, ativo=1))
    p_peca_id = repo.criar_produto(conn, Produto(nome="VALVULA", tipo="PECA", preco_padrao=20.0, ativo=1))

    conn.commit()
    return {
        "c_ativo_id": c_ativo_id,
        "c_inativo_id": c_inativo_id,
        "l_ativa_id": l_ativa_id,
        "l_inativa_id": l_inativa_id,
        "p_serv_id": p_serv_id,
        "p_peca_id": p_peca_id,
    }


def test_cliente_inativo_nao_aparece_novo_pedido(qtbot, conn, setup_dados_ui):
    """Regra 3.2: Cliente inativo não deve aparecer no seletor de novo pedido."""
    dlg = PedidoDialog(conn)
    qtbot.addWidget(dlg)

    c_inativo_id = setup_dados_ui["c_inativo_id"]
    c_ativo_id = setup_dados_ui["c_ativo_id"]

    # Verifica os IDs presentes no combo de clientes
    itens_combo_ids = [dlg.cbo_cliente.itemData(i) for i in range(dlg.cbo_cliente.count())]
    assert c_ativo_id in itens_combo_ids
    assert c_inativo_id not in itens_combo_ids


def test_pedido_antigo_com_loja_inativa_exibe_loja(qtbot, conn, setup_dados_ui):
    """Regra 3.2: Ao editar/visualizar pedido com loja inativa, ela continua sendo exibida."""
    c_ativo_id = setup_dados_ui["c_ativo_id"]
    l_inativa_id = setup_dados_ui["l_inativa_id"]

    # Cria pedido antigo associado à loja que hoje é inativa
    ped_antigo = Pedido(
        cliente_id=c_ativo_id,
        loja_id=l_inativa_id,
        numero_pedido="PED-HISTORICO",
        data_emissao="2026-01-10",
        status="ABERTO"
    )
    ped_antigo_id = repo.salvar_pedido_completo(conn, ped_antigo, [])

    dlg = PedidoDialog(conn, pedido_id=ped_antigo_id)
    qtbot.addWidget(dlg)

    # A loja inativa deve estar no combo e selecionada
    lojas_combo_ids = [dlg.cbo_loja.itemData(i) for i in range(dlg.cbo_loja.count())]
    assert l_inativa_id in lojas_combo_ids
    assert dlg.cbo_loja.currentData() == l_inativa_id


def test_rejeicao_data_invalida_calendario(qtbot, conn, setup_dados_ui, monkeypatch):
    """Validação de data: datas inválidas como 31/02/2026 são recusadas com aviso antes de gravar."""
    dlg = PedidoDialog(conn)
    qtbot.addWidget(dlg)

    dlg.txt_numero.setText("PED-DATA-INV")
    dlg.txt_data_emissao.setText("31/02/2026")

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(f"{args[1]}: {args[2]}"))

    dlg._salvar()

    assert len(avisos) > 0
    assert "Data de Emissão Inválida" in str(avisos[0])
    # Garante que nada foi gravado
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE numero_pedido = 'PED-DATA-INV'")
    assert cur.fetchone()[0] == 0


def test_numero_pedido_repetido_recusado_interface(qtbot, conn, setup_dados_ui, monkeypatch):
    """Número repetido para o mesmo cliente é recusado na interface com mensagem clara."""
    c_ativo_id = setup_dados_ui["c_ativo_id"]
    l_ativa_id = setup_dados_ui["l_ativa_id"]

    # Cria pedido existente
    p1 = Pedido(cliente_id=c_ativo_id, loja_id=l_ativa_id, numero_pedido="2026100", data_emissao="2026-10-13")
    repo.salvar_pedido_completo(conn, p1, [])

    # Tenta criar outro pedido no mesmo cliente com mesmo número pela tela
    dlg = PedidoDialog(conn)
    qtbot.addWidget(dlg)
    dlg.txt_numero.setText("2026100")
    dlg.txt_data_emissao.setText("13/10/2026")

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(f"{args[1]}: {args[2]}"))

    dlg._salvar()

    assert any("Erro de Validação" in a for a in avisos)
    assert any("Já existe um pedido" in a for a in avisos)


def test_acao_marcar_executado_com_dialogo(qtbot, conn, setup_dados_ui, monkeypatch):
    """Botão 'Marcar Executado' abre diálogo pedindo data de execução e atualiza status."""
    c_ativo_id = setup_dados_ui["c_ativo_id"]
    l_ativa_id = setup_dados_ui["l_ativa_id"]

    ped = Pedido(cliente_id=c_ativo_id, loja_id=l_ativa_id, numero_pedido="PED-EXEC-UI", data_emissao="2026-10-13", status="ABERTO")
    ped_id = repo.salvar_pedido_completo(conn, ped, [])

    view = PedidosView(conn)
    qtbot.addWidget(view)

    # Seleciona a primeira linha da tabela
    view.table.selectRow(0)

    # Simula resposta do diálogo de data de execução
    class MockDataExecDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.data_iso = "2026-10-15"

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("ui.views.pedidos_view.DataExecucaoDialog", MockDataExecDialog)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    view._marcar_executado()

    p_atual = repo.buscar_pedido_por_id(conn, ped_id)
    assert p_atual.status == "EXECUTADO"
    assert p_atual.data_execucao == "2026-10-15"


def test_marcar_faturado_a_partir_de_aberto_recusado(qtbot, conn, setup_dados_ui, monkeypatch):
    """Marcar FATURADO a partir de ABERTO é recusado com mensagem explicativa."""
    c_ativo_id = setup_dados_ui["c_ativo_id"]
    l_ativa_id = setup_dados_ui["l_ativa_id"]

    ped = Pedido(cliente_id=c_ativo_id, loja_id=l_ativa_id, numero_pedido="PED-FAT-UI", data_emissao="2026-10-13", status="ABERTO")
    ped_id = repo.salvar_pedido_completo(conn, ped, [])

    view = PedidosView(conn)
    qtbot.addWidget(view)
    view.table.selectRow(0)

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(f"{args[1]}: {args[2]}"))

    view._marcar_faturado()

    assert any("Ação Não Permitida" in a for a in avisos)
    p_atual = repo.buscar_pedido_por_id(conn, ped_id)
    assert p_atual.status == "ABERTO"  # Não alterou!


def test_duplicar_pedido_interface(qtbot, conn, setup_dados_ui, monkeypatch):
    """Duplicação pela interface solicita novo número e cria o clone zerado."""
    c_ativo_id = setup_dados_ui["c_ativo_id"]
    l_ativa_id = setup_dados_ui["l_ativa_id"]

    ped = Pedido(cliente_id=c_ativo_id, loja_id=l_ativa_id, numero_pedido="PED-CLONE-UI", data_emissao="2026-10-13", status="ABERTO")
    item = ItemPedido(secao="SERVICO", descricao="Recarga", quantidade=2.0, unidade="SV", preco_unitario=50.0, valor_total=100.0)
    ped_id = repo.salvar_pedido_completo(conn, ped, [item])

    view = PedidosView(conn)
    qtbot.addWidget(view)
    view.table.selectRow(0)

    # Simula diálogo de duplicação retornando novo número válido
    class MockDuplicarDialog(QDialog):
        def __init__(self, orig_num, parent=None):
            super().__init__(parent)
            self.novo_numero = "PED-NOVO-123"
            self.data_emissao_iso = "2026-10-14"

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("ui.views.pedidos_view.DuplicarPedidoDialog", MockDuplicarDialog)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    view._duplicar_pedido()

    # Verifica novo pedido criado
    cur = conn.cursor()
    cur.execute("SELECT id, status, data_emissao FROM pedidos WHERE numero_pedido = 'PED-NOVO-123'")
    row = cur.fetchone()
    assert row is not None
    assert row[1] == "ABERTO"
    assert row[2] == "2026-10-14"

    # Verifica que itens do clone foram zerados
    itens_clone = repo.listar_itens_pedido(conn, row[0])
    assert len(itens_clone) == 1
    assert itens_clone[0].quantidade == 0.0
    assert itens_clone[0].preco_unitario == 0.0
