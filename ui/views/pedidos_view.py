"""Tela principal de listagem, consulta e operações de Pedidos."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QDialog
)
from ui.components.data_table import DataTable
from ui.components.proxy_model import GenericFilterProxyModel
from ui.views.pedido_dialog import PedidoDialog, formatar_data_br_para_iso, formatar_data_iso_para_br
import db.repositories as repo
import app.core.order_service as service


class DataExecucaoDialog(QDialog):
    """Diálogo modal para solicitar a data de execução obrigatória (sem valor padrão)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Marcar como Executado")
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Informe a <b>Data de Execução</b> obrigatória do serviço:"))

        form = QFormLayout()
        self.txt_data = QLineEdit()
        self.txt_data.setPlaceholderText("dd/mm/aaaa")
        form.addRow("Data (dd/mm/aaaa) *:", self.txt_data)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_confirmar = QPushButton("Confirmar Execução")
        btn_confirmar.setStyleSheet("font-weight: bold;")
        btn_confirmar.clicked.connect(self._confirmar)

        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(btn_confirmar)
        layout.addLayout(btn_box)

        self.data_iso: Optional[str] = None

    def _confirmar(self):
        data_digitada = self.txt_data.text().strip()
        if not data_digitada:
            QMessageBox.warning(self, "Aviso", "A data de execução é obrigatória.")
            return

        try:
            self.data_iso = formatar_data_br_para_iso(data_digitada)
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Data Inválida", str(e))


class DuplicarPedidoDialog(QDialog):
    """Diálogo modal para solicitar os parâmetros de duplicação de um pedido."""

    def __init__(self, numero_original: str, parent=None):
        super().__init__(parent)
        self.numero_original = numero_original
        self.setWindowTitle("Duplicar Pedido")
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Duplicando a partir do Pedido <b>#{numero_original}</b>:"))

        form = QFormLayout()
        self.txt_novo_numero = QLineEdit()
        self.txt_novo_numero.setPlaceholderText("Novo número obrigatório...")
        form.addRow("Novo Nº Pedido *:", self.txt_novo_numero)

        self.txt_data_emissao = QLineEdit()
        self.txt_data_emissao.setText(datetime.now().strftime("%d/%m/%Y"))
        form.addRow("Data de Emissão *:", self.txt_data_emissao)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_confirmar = QPushButton("Duplicar Pedido")
        btn_confirmar.setStyleSheet("font-weight: bold;")
        btn_confirmar.clicked.connect(self._confirmar)

        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(btn_confirmar)
        layout.addLayout(btn_box)

        self.novo_numero: Optional[str] = None
        self.data_emissao_iso: Optional[str] = None

    def _confirmar(self):
        novo_num = self.txt_novo_numero.text().strip()
        if not novo_num:
            QMessageBox.warning(self, "Aviso", "O novo número do pedido é obrigatório.")
            return

        if novo_num == self.numero_original:
            QMessageBox.warning(self, "Aviso", "O novo número deve ser diferente do número original.")
            return

        try:
            self.data_emissao_iso = formatar_data_br_para_iso(self.txt_data_emissao.text())
        except ValueError as e:
            QMessageBox.warning(self, "Data Inválida", str(e))
            return

        self.novo_numero = novo_num
        self.accept()


class PedidosView(QWidget):
    """Tela principal de listagem e controle de pedidos."""

    COLUNAS = [
        "ID", "Nº Pedido", "Data Emissão", "Data Execução",
        "Cliente", "Loja", "Status", "Valor Total"
    ]

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._criar_ui()
        self.recarregar_dados()

    def _criar_ui(self):
        layout = QVBoxLayout(self)

        # Barra de Filtros
        lay_filtros = QHBoxLayout()

        lay_filtros.addWidget(QLabel("Filtrar por Cliente:"))
        self.cbo_filtro_cliente = QComboBox()
        self.cbo_filtro_cliente.addItem("Todos os Clientes", None)
        self.cbo_filtro_cliente.currentIndexChanged.connect(self._on_filtro_alterado)
        lay_filtros.addWidget(self.cbo_filtro_cliente)

        lay_filtros.addWidget(QLabel("Loja:"))
        self.cbo_filtro_loja = QComboBox()
        self.cbo_filtro_loja.addItem("Todas as Lojas", None)
        self.cbo_filtro_loja.currentIndexChanged.connect(self.recarregar_dados)
        lay_filtros.addWidget(self.cbo_filtro_loja)

        lay_filtros.addWidget(QLabel("Status:"))
        lay_filtros.addWidget(QLabel("Status:"))
        self.cbo_filtro_status = QComboBox()
        self.cbo_filtro_status.addItems(["TODOS", "ABERTO", "EXECUTADO", "FATURADO", "PAGO"])
        self.cbo_filtro_status.currentIndexChanged.connect(self.recarregar_dados)
        lay_filtros.addWidget(self.cbo_filtro_status)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por texto...")
        self.txt_busca.textChanged.connect(self._ao_filtrar_texto)
        lay_filtros.addWidget(self.txt_busca)

        lay_filtros.addStretch()
        layout.addLayout(lay_filtros)

        # Tabela padronizada DataTable com modelo proxy
        self.table = DataTable(self)
        self.data_table = self.table
        self.source_model = QStandardItemModel(self)
        self.source_model.setHorizontalHeaderLabels(self.COLUNAS)
        self.proxy_model = GenericFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.table.setModel(self.proxy_model)
        self.table.doubleClicked.connect(self._editar_selecionado)
        layout.addWidget(self.table)

        # Barra de Ações
        lay_acoes = QHBoxLayout()

        self.btn_novo = QPushButton("➕ Novo Pedido")
        self.btn_novo.setStyleSheet("font-weight: bold;")
        self.btn_novo.clicked.connect(self._novo_pedido)

        self.btn_editar = QPushButton("✏️ Editar / Visualizar")
        self.btn_editar.clicked.connect(self._editar_selecionado)

        self.btn_marcar_executado = QPushButton("✔️ Marcar Executado")
        self.btn_marcar_executado.clicked.connect(self._marcar_executado)

        self.btn_marcar_faturado = QPushButton("💼 Marcar Faturado")
        self.btn_marcar_faturado.clicked.connect(self._marcar_faturado)

        self.btn_duplicar = QPushButton("📋 Duplicar Pedido")
        self.btn_duplicar.clicked.connect(self._duplicar_pedido)

        self.btn_excluir = QPushButton("🗑️ Excluir")
        self.btn_excluir.clicked.connect(self._excluir_pedido)

        lay_acoes.addWidget(self.btn_novo)
        lay_acoes.addWidget(self.btn_editar)
        lay_acoes.addWidget(self.btn_marcar_executado)
        lay_acoes.addWidget(self.btn_marcar_faturado)
        lay_acoes.addWidget(self.btn_duplicar)
        lay_acoes.addStretch()
        lay_acoes.addWidget(self.btn_excluir)

        layout.addLayout(lay_acoes)

        self._popular_combo_clientes()

    def _ao_filtrar_texto(self, texto: str):
        self.proxy_model.set_filter_text(texto)

    def _popular_combo_clientes(self):
        clientes = repo.listar_clientes(self.conn)
        for c in clientes:
            self.cbo_filtro_cliente.addItem(c.razao_social, c.id)

    def _on_filtro_alterado(self):
        cliente_id = self.cbo_filtro_cliente.currentData()
        self.cbo_filtro_loja.clear()
        self.cbo_filtro_loja.addItem("Todas as Lojas", None)

        if cliente_id is not None:
            lojas = repo.listar_lojas_por_cliente(self.conn, cliente_id)
            for l in lojas:
                self.cbo_filtro_loja.addItem(f"{l.codigo_loja} — {l.nome_site}", l.id)

        self.recarregar_dados()

    def recarregar_dados(self):
        """Carrega e exibe a lista de pedidos aplicando os filtros de cliente, loja e status."""
        cliente_id = self.cbo_filtro_cliente.currentData()
        loja_id = self.cbo_filtro_loja.currentData()
        status_sel = self.cbo_filtro_status.currentText()
        status_filtro = status_sel if status_sel != "TODOS" else None

        pedidos = repo.listar_pedidos(
            self.conn,
            cliente_id=cliente_id,
            loja_id=loja_id,
            status=status_filtro
        )

        self.source_model.clear()
        self.source_model.setHorizontalHeaderLabels(self.COLUNAS)
        self.source_model.setRowCount(len(pedidos))

        for r_idx, ped in enumerate(pedidos):
            item_id = QStandardItem(str(ped["id"]))
            item_id.setData(ped["id"], Qt.ItemDataRole.UserRole)

            item_num = QStandardItem(str(ped["numero_pedido"]))
            item_emissao = QStandardItem(formatar_data_iso_para_br(ped["data_emissao"]))
            item_exec = QStandardItem(formatar_data_iso_para_br(ped["data_execucao"]) or "-")
            item_cli = QStandardItem(ped["cliente_nome"])
            item_loja = QStandardItem(f"{ped['loja_codigo']} — {ped['loja_nome']}")

            status_str = ped["status"]
            item_status = QStandardItem(status_str)
            if status_str == "FATURADO":
                item_status.setForeground(QColor("#2e7d32"))  # Verde
            elif status_str == "EXECUTADO":
                item_status.setForeground(QColor("#1565c0"))  # Azul
            elif status_str == "PAGO":
                item_status.setForeground(QColor("#6a1b9a"))  # Roxo
            else:
                item_status.setForeground(QColor("#e65100"))  # Laranja/Aberto

            val_total = ped["valor_total"]
            item_total = QStandardItem(f"R$ {val_total:.2f}".replace(".", ","))
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.source_model.setItem(r_idx, 0, item_id)
            self.source_model.setItem(r_idx, 1, item_num)
            self.source_model.setItem(r_idx, 2, item_emissao)
            self.source_model.setItem(r_idx, 3, item_exec)
            self.source_model.setItem(r_idx, 4, item_cli)
            self.source_model.setItem(r_idx, 5, item_loja)
            self.source_model.setItem(r_idx, 6, item_status)
            self.source_model.setItem(r_idx, 7, item_total)

    def _obter_id_selecionado(self) -> Optional[int]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        proxy_idx = indexes[0]
        src_idx = self.proxy_model.mapToSource(proxy_idx)
        item = self.source_model.item(src_idx.row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _novo_pedido(self):
        dlg = PedidoDialog(self.conn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.recarregar_dados()

    def _editar_selecionado(self):
        pedido_id = self._obter_id_selecionado()
        if pedido_id is None:
            QMessageBox.information(self, "Aviso", "Selecione um pedido para editar/visualizar.")
            return

        dlg = PedidoDialog(self.conn, pedido_id=pedido_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.recarregar_dados()

    def _marcar_executado(self):
        pedido_id = self._obter_id_selecionado()
        if pedido_id is None:
            QMessageBox.information(self, "Aviso", "Selecione um pedido da lista.")
            return

        pedido = repo.buscar_pedido_por_id(self.conn, pedido_id)
        if not pedido:
            return

        if pedido.status != "ABERTO":
            QMessageBox.warning(
                self, "Ação Inválida",
                f"Apenas pedidos com status ABERTO podem ser marcados como EXECUTADO. Status atual: '{pedido.status}'."
            )
            return

        dlg = DataExecucaoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.data_iso:
            try:
                service.transitar_status(self.conn, pedido_id, "EXECUTADO", data_execucao=dlg.data_iso)
                self.recarregar_dados()
                QMessageBox.information(self, "Sucesso", f"Pedido #{pedido.numero_pedido} marcado como EXECUTADO!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _marcar_faturado(self):
        pedido_id = self._obter_id_selecionado()
        if pedido_id is None:
            QMessageBox.information(self, "Aviso", "Selecione um pedido da lista.")
            return

        pedido = repo.buscar_pedido_por_id(self.conn, pedido_id)
        if not pedido:
            return

        if pedido.status == "ABERTO":
            QMessageBox.warning(
                self, "Ação Não Permitida",
                "Pedido precisa estar EXECUTADO antes de ser FATURADO."
            )
            return

        if pedido.status in ("FATURADO", "PAGO"):
            QMessageBox.information(self, "Aviso", f"O pedido já se encontra no status '{pedido.status}'.")
            return

        resp = QMessageBox.question(
            self, "Confirmar Faturamento",
            f"Deseja marcar o pedido #{pedido.numero_pedido} como FATURADO?\n\n"
            "Atenção: Esta ação bloqueará edições no cabeçalho e nos itens do pedido.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                service.transitar_status(self.conn, pedido_id, "FATURADO")
                self.recarregar_dados()
                QMessageBox.information(self, "Sucesso", f"Pedido #{pedido.numero_pedido} marcado como FATURADO com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _duplicar_pedido(self):
        pedido_id = self._obter_id_selecionado()
        if pedido_id is None:
            QMessageBox.information(self, "Aviso", "Selecione um pedido da lista para duplicar.")
            return

        pedido = repo.buscar_pedido_por_id(self.conn, pedido_id)
        if not pedido:
            return

        dlg = DuplicarPedidoDialog(pedido.numero_pedido, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.novo_numero and dlg.data_emissao_iso:
            try:
                novo_id = service.duplicar_pedido(
                    self.conn,
                    pedido_origem_id=pedido_id,
                    novo_numero_pedido=dlg.novo_numero,
                    nova_data_emissao=dlg.data_emissao_iso
                )
                self.recarregar_dados()
                QMessageBox.information(
                    self, "Sucesso",
                    f"Pedido duplicado com sucesso!\nNovo pedido: #{dlg.novo_numero} (ID: {novo_id})."
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro na Duplicação", str(e))

    def _excluir_pedido(self):
        pedido_id = self._obter_id_selecionado()
        if pedido_id is None:
            QMessageBox.information(self, "Aviso", "Selecione um pedido da lista para excluir.")
            return

        pedido = repo.buscar_pedido_por_id(self.conn, pedido_id)
        if not pedido:
            return

        if pedido.status != "ABERTO":
            QMessageBox.warning(
                self, "Exclusão Bloqueada",
                f"Apenas pedidos com status ABERTO podem ser excluídos. Pedido atual: '{pedido.status}'."
            )
            return

        resp = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o Pedido #{pedido.numero_pedido}?\n"
            "Esta ação removerá o pedido e todos os seus itens.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            try:
                service.excluir_pedido(self.conn, pedido_id)
                self.recarregar_dados()
                QMessageBox.information(self, "Sucesso", f"Pedido #{pedido.numero_pedido} excluído com sucesso.")
            except PermissionError as e:
                QMessageBox.critical(self, "Exclusão Recusada", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro inesperado ao excluir pedido:\n{e}")
