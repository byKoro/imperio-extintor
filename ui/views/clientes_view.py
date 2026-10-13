"""Tela de Gerenciamento de Clientes (CRUD)."""

import sqlite3
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QDialog, QFormLayout, QMessageBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from db.models import Cliente
from db.repositories import (
    listar_clientes, criar_cliente, atualizar_cliente,
    excluir_cliente, buscar_cliente_por_id
)
from ui.components.data_table import DataTable
from ui.components.proxy_model import GenericFilterProxyModel


class ClientesTableModel(QAbstractTableModel):
    """Modelo de dados para a listagem de clientes."""

    HEADERS = [
        "ID", "Razão Social", "Nome Fantasia", "CNPJ", "Telefone",
        "Contato", "Prazo Pgto", "Forma Pgto", "Prazo Entrega"
    ]

    def __init__(self, clientes: Optional[List[Cliente]] = None):
        super().__init__()
        self._clientes = clientes or []

    def set_clientes(self, clientes: List[Cliente]):
        self.beginResetModel()
        self._clientes = clientes
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._clientes)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        cliente = self._clientes[index.row()]
        col = index.column()

        if col == 0:
            return str(cliente.id)
        elif col == 1:
            return cliente.razao_social
        elif col == 2:
            return cliente.nome_fantasia or ""
        elif col == 3:
            return cliente.cnpj or ""
        elif col == 4:
            return cliente.telefone or ""
        elif col == 5:
            return cliente.contato or ""
        elif col == 6:
            return cliente.prazo_pagamento or ""
        elif col == 7:
            return cliente.forma_pagamento or ""
        elif col == 8:
            return cliente.prazo_entrega or ""
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def get_cliente(self, row: int) -> Optional[Cliente]:
        if 0 <= row < len(self._clientes):
            return self._clientes[row]
        return None


class ClienteDialog(QDialog):
    """Diálogo para criação e edição de cliente."""

    def __init__(self, cliente: Optional[Cliente] = None, parent=None):
        super().__init__(parent)
        self.cliente = cliente or Cliente()
        self.is_edicao = cliente is not None and cliente.id is not None
        self.setWindowTitle("Editar Cliente" if self.is_edicao else "Novo Cliente")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_razao = QLineEdit(self.cliente.razao_social)
        self.txt_fantasia = QLineEdit(self.cliente.nome_fantasia or "")
        self.txt_cnpj = QLineEdit(self.cliente.cnpj or "")
        self.txt_ie = QLineEdit(self.cliente.inscricao_estadual or "")
        self.txt_endereco = QLineEdit(self.cliente.endereco or "")
        self.txt_telefone = QLineEdit(self.cliente.telefone or "")
        self.txt_email = QLineEdit(self.cliente.email or "")
        self.txt_contato = QLineEdit(self.cliente.contato or "")
        self.txt_prazo_pag = QLineEdit(self.cliente.prazo_pagamento or "30 dias")
        self.txt_forma_pag = QLineEdit(self.cliente.forma_pagamento or "Transferência bancária")
        self.txt_prazo_entrega = QLineEdit(self.cliente.prazo_entrega or "7 dias úteis")
        self.txt_impostos = QLineEdit(self.cliente.texto_impostos or "Impostos inclusos")

        form.addRow("Razão Social *:", self.txt_razao)
        form.addRow("Nome Fantasia:", self.txt_fantasia)
        form.addRow("CNPJ:", self.txt_cnpj)
        form.addRow("Inscrição Estadual:", self.txt_ie)
        form.addRow("Endereço:", self.txt_endereco)
        form.addRow("Telefone:", self.txt_telefone)
        form.addRow("E-mail:", self.txt_email)
        form.addRow("Contato:", self.txt_contato)
        form.addRow("Prazo de Pagamento:", self.txt_prazo_pag)
        form.addRow("Forma de Pagamento:", self.txt_forma_pag)
        form.addRow("Prazo de Entrega:", self.txt_prazo_entrega)
        form.addRow("Texto de Impostos:", self.txt_impostos)

        layout.addLayout(form)

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _salvar(self):
        razao = self.txt_razao.text().strip()
        if not razao:
            QMessageBox.warning(self, "Aviso", "A Razão Social é obrigatória.")
            return

        self.cliente.razao_social = razao
        self.cliente.nome_fantasia = self.txt_fantasia.text().strip() or None
        self.cliente.cnpj = self.txt_cnpj.text().strip() or None
        self.cliente.inscricao_estadual = self.txt_ie.text().strip() or None
        self.cliente.endereco = self.txt_endereco.text().strip() or None
        self.cliente.telefone = self.txt_telefone.text().strip() or None
        self.cliente.email = self.txt_email.text().strip() or None
        self.cliente.contato = self.txt_contato.text().strip() or None
        self.cliente.prazo_pagamento = self.txt_prazo_pag.text().strip() or "30 dias"
        self.cliente.forma_pagamento = self.txt_forma_pag.text().strip() or "Transferência bancária"
        self.cliente.prazo_entrega = self.txt_prazo_entrega.text().strip() or "7 dias úteis"
        self.cliente.texto_impostos = self.txt_impostos.text().strip() or "Impostos inclusos"

        self.accept()


class ClientesView(QWidget):
    """View principal de listagem e controle de clientes."""

    abrir_lojas_solicitado = Signal(int)  # cliente_id
    abrir_precos_solicitado = Signal(int)  # cliente_id

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._init_ui()
        self.carregar_dados()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Barra de ferramentas
        toolbar = QHBoxLayout()
        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar clientes por razão social, CNPJ, contato...")
        self.txt_busca.textChanged.connect(self._ao_filtrar)
        toolbar.addWidget(self.txt_busca)

        btn_novo = QPushButton("+ Novo Cliente")
        btn_novo.clicked.connect(self._novo_cliente)
        toolbar.addWidget(btn_novo)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self._editar_cliente)
        toolbar.addWidget(btn_editar)

        btn_lojas = QPushButton("Ver Lojas")
        btn_lojas.clicked.connect(self._ver_lojas)
        toolbar.addWidget(btn_lojas)

        btn_precos = QPushButton("Tabela de Preços")
        btn_precos.clicked.connect(self._ver_precos)
        toolbar.addWidget(btn_precos)

        btn_excluir = QPushButton("Excluir")
        btn_excluir.clicked.connect(self._excluir_cliente)
        toolbar.addWidget(btn_excluir)

        layout.addLayout(toolbar)

        # Tabela
        self.table = DataTable()
        self.model = ClientesTableModel()
        self.proxy = GenericFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.doubleClicked.connect(self._editar_cliente)

        layout.addWidget(self.table)

    def _ao_filtrar(self, texto: str):
        self.proxy.set_filter_text(texto)

    def carregar_dados(self):
        clientes = listar_clientes(self.conn)
        self.model.set_clientes(clientes)

    def _obter_cliente_selecionado(self) -> Optional[Cliente]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        proxy_idx = indexes[0]
        source_idx = self.proxy.mapToSource(proxy_idx)
        return self.model.get_cliente(source_idx.row())

    def _novo_cliente(self):
        dialog = ClienteDialog(parent=self)
        if dialog.exec():
            criar_cliente(self.conn, dialog.cliente)
            self.conn.commit()
            self.carregar_dados()

    def _editar_cliente(self):
        cliente = self._obter_cliente_selecionado()
        if not cliente:
            QMessageBox.information(self, "Aviso", "Selecione um cliente para editar.")
            return

        dialog = ClienteDialog(cliente=cliente, parent=self)
        if dialog.exec():
            atualizar_cliente(self.conn, dialog.cliente)
            self.conn.commit()
            self.carregar_dados()

    def _excluir_cliente(self):
        cliente = self._obter_cliente_selecionado()
        if not cliente:
            QMessageBox.information(self, "Aviso", "Selecione um cliente para excluir.")
            return

        resp = QMessageBox.question(
            self, "Confirmação",
            f"Deseja realmente excluir ou inativar o cliente '{cliente.razao_social}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            excluir_cliente(self.conn, cliente.id)
            self.conn.commit()
            self.carregar_dados()

    def _ver_lojas(self):
        cliente = self._obter_cliente_selecionado()
        if cliente and cliente.id is not None:
            self.abrir_lojas_solicitado.emit(cliente.id)
        else:
            QMessageBox.information(self, "Aviso", "Selecione um cliente para ver suas lojas.")

    def _ver_precos(self):
        cliente = self._obter_cliente_selecionado()
        if cliente and cliente.id is not None:
            self.abrir_precos_solicitado.emit(cliente.id)
        else:
            QMessageBox.information(self, "Aviso", "Selecione um cliente para gerenciar a tabela de preços.")
