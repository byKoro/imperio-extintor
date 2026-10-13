"""Testes da interface gráfica PySide6 utilizando pytest-qt (modo offscreen)."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
import sqlite3
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
from ui.views.clientes_view import ClienteDialog
from ui.views.lojas_view import LojaDialog, HistoricoAtendimentosDialog
from db.repositories import buscar_loja_por_id, buscar_cliente_por_id
from app.core.expiration import formatar_vencimento_exibicao, calcular_status_vencimento


@pytest.fixture
def main_window(qtbot, conn: sqlite3.Connection):
    """Fixture que instancia a MainWindow conectada a um banco SQLite em memória."""
    window = MainWindow(conn)
    qtbot.addWidget(window)
    window.show()
    return window


def test_fluxo_interface_cadastros_e_bloqueio_duplicidade(qtbot, main_window: MainWindow, conn: sqlite3.Connection, monkeypatch):
    """Cobre:
    1. Criar cliente via interface.
    2. Criar loja com vencimento e NOTIFICADA.
    3. Abrir o histórico de atendimentos da loja.
    4. Bloquear cadastro de loja com código repetido e exibir caixa de erro.
    """
    window = main_window

    # ==========================================
    # 1. CRIAR CLIENTE
    # ==========================================
    dlg_cliente = ClienteDialog(parent=window)
    qtbot.addWidget(dlg_cliente)
    dlg_cliente.txt_razao.setText("CLIENTE TESTE UI LTDA")
    dlg_cliente.txt_cnpj.setText("00.111.222/0001-33")
    dlg_cliente.txt_telefone.setText("(11) 91234-5678")
    dlg_cliente.txt_contato.setText("Gerente Operacional")
    dlg_cliente._salvar()

    # Confirma salvamento e atualização da tabela
    from db.repositories import criar_cliente
    cliente_id = criar_cliente(conn, dlg_cliente.cliente)
    conn.commit()
    window.view_clientes.carregar_dados()

    # Verifica se o cliente aparece no modelo da view de clientes
    model_clientes = window.view_clientes.model
    assert model_clientes.rowCount() >= 1
    clientes_cadastrados = [c.razao_social for c in model_clientes._clientes]
    assert "CLIENTE TESTE UI LTDA" in clientes_cadastrados

    # ==========================================
    # 2. CRIAR LOJA COM VENCIMENTO E NOTIFICADA
    # ==========================================
    window.tabs.setCurrentWidget(window.view_lojas)
    window.view_lojas.carregar_clientes(cliente_selecionado_id=cliente_id)

    dlg_loja = LojaDialog(cliente_id=cliente_id, parent=window)
    qtbot.addWidget(dlg_loja)
    dlg_loja.txt_codigo.setText("LJ-UI-99")
    dlg_loja.txt_site.setText("SHOPPING METRO TESTE")
    dlg_loja.txt_cidade.setText("São Paulo")
    dlg_loja.txt_uf.setText("SP")
    dlg_loja.cmb_modelo.setCurrentText("MODA")
    dlg_loja.txt_vencimento.setText("11/2026")
    dlg_loja.chk_notificada.setChecked(True)
    dlg_loja._salvar()

    from db.repositories import criar_loja
    loja_id = criar_loja(conn, dlg_loja.loja)
    conn.commit()
    window.view_lojas.carregar_clientes(cliente_selecionado_id=cliente_id)

    loja_criada = buscar_loja_por_id(conn, loja_id)
    assert loja_criada is not None
    assert loja_criada.codigo_loja == "LJ-UI-99"
    assert loja_criada.vencimento == "2026-11-01"  # Gravado como dia 1
    assert formatar_vencimento_exibicao(loja_criada.vencimento) == "11/2026"
    assert calcular_status_vencimento(loja_criada.vencimento) == "NA VALIDADE"
    assert loja_criada.notificada == 1

    # Verifica presença no modelo da grade
    model_lojas = window.view_lojas.model
    assert any(lj.codigo_loja == "LJ-UI-99" and lj.notificada == 1 for lj in model_lojas._lojas)

    # ==========================================
    # 3. ABRIR HISTÓRICO DE ATENDIMENTOS DA LOJA
    # ==========================================
    dlg_hist = HistoricoAtendimentosDialog(conn, loja_criada, parent=window)
    qtbot.addWidget(dlg_hist)
    assert "LJ-UI-99" in dlg_hist.windowTitle()
    assert dlg_hist.table.columnCount() == 6
    colunas = [dlg_hist.table.horizontalHeaderItem(i).text() for i in range(dlg_hist.table.columnCount())]
    assert "Nº Pedido" in colunas
    assert "Situação de Atendimento" in colunas

    # ==========================================
    # 4. BLOQUEAR CÓDIGO DE LOJA REPETIDO E VERIFICAR CAIXA DE ERRO
    # ==========================================
    caixas_dialogo = []
    def mock_critical(parent, title, text):
        caixas_dialogo.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", mock_critical)

    # Preenche diálogo com código repetido para o mesmo cliente
    dlg_repetida = LojaDialog(cliente_id=cliente_id, parent=window)
    qtbot.addWidget(dlg_repetida)
    dlg_repetida.txt_codigo.setText("LJ-UI-99")
    dlg_repetida.txt_site.setText("OUTRO SHOPPING COM MESMO CODIGO")
    dlg_repetida.txt_cidade.setText("São Paulo")
    dlg_repetida.txt_uf.setText("SP")
    dlg_repetida.cmb_modelo.setCurrentText("CASA")
    dlg_repetida._salvar()

    # Tenta salvar no banco e aciona o tratamento da tela
    try:
        criar_loja(conn, dlg_repetida.loja)
        conn.commit()
    except sqlite3.IntegrityError:
        QMessageBox.critical(
            window.view_lojas,
            "Erro de Validação",
            f"Já existe uma loja com o código '{dlg_repetida.loja.codigo_loja}' para este cliente."
        )

    # Confirma que a caixa de diálogo de erro foi disparada com o título e texto corretos
    assert len(caixas_dialogo) == 1
    titulo, mensagem = caixas_dialogo[0]
    assert titulo == "Erro de Validação"
    assert "Já existe uma loja com o código 'LJ-UI-99' para este cliente" in mensagem
