"""Tela de Gerenciamento de Produtos e Serviços (CRUD)."""

import sqlite3
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QDialog, QFormLayout, QMessageBox, QDialogButtonBox,
    QComboBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from db.models import Produto
from db.repositories import (
    listar_produtos, criar_produto, atualizar_produto,
    excluir_produto
)
from app.core.constants import (
    TIPO_PRODUTO_SERVICO, TIPO_PRODUTO_PECA,
    UNIDADE_SERVICO, UNIDADE_PECA
)
from ui.components.data_table import DataTable
from ui.components.proxy_model import GenericFilterProxyModel


class ProdutosTableModel(QAbstractTableModel):
    """Modelo de dados para a grade de produtos e serviços."""

    HEADERS = [
        "ID", "Nome / Descrição", "Tipo", "Categoria", "Unidade", "Capacidade", "Preço Padrão (R$)"
    ]

    def __init__(self, produtos: Optional[List[Produto]] = None):
        super().__init__()
        self._produtos = produtos or []

    def set_produtos(self, produtos: List[Produto]):
        self.beginResetModel()
        self._produtos = produtos
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._produtos)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        produto = self._produtos[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(produto.id)
            elif col == 1:
                return produto.nome
            elif col == 2:
                return "Serviço" if produto.tipo == TIPO_PRODUTO_SERVICO else "Peça"
            elif col == 3:
                return produto.categoria or ""
            elif col == 4:
                return produto.unidade
            elif col == 5:
                return produto.capacidade or "-"
            elif col == 6:
                return f"R$ {produto.preco_padrao:.2f}".replace(".", ",")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 6:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def get_produto(self, row: int) -> Optional[Produto]:
        if 0 <= row < len(self._produtos):
            return self._produtos[row]
        return None


class ProdutoDialog(QDialog):
    """Diálogo para criação e edição de produto/serviço."""

    def __init__(self, produto: Optional[Produto] = None, parent=None):
        super().__init__(parent)
        self.produto = produto or Produto()
        self.is_edicao = produto is not None and produto.id is not None
        self.setWindowTitle("Editar Produto/Serviço" if self.is_edicao else "Novo Produto/Serviço")
        self.setMinimumWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_nome = QLineEdit(self.produto.nome)

        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItem("Serviço", TIPO_PRODUTO_SERVICO)
        self.cmb_tipo.addItem("Peça", TIPO_PRODUTO_PECA)
        if self.produto.tipo == TIPO_PRODUTO_PECA:
            self.cmb_tipo.setCurrentIndex(1)
        self.cmb_tipo.currentIndexChanged.connect(self._ao_mudar_tipo)

        self.txt_categoria = QLineEdit(self.produto.categoria or "")
        self.txt_categoria.setPlaceholderText("Ex.: Extintores, Mangueiras, Peças")

        self.txt_unidade = QLineEdit(self.produto.unidade or UNIDADE_SERVICO)
        self.txt_capacidade = QLineEdit(self.produto.capacidade or "")
        self.txt_capacidade.setPlaceholderText("Ex.: 10 L, 8 kg, -")

        self.spn_preco = QDoubleSpinBox()
        self.spn_preco.setPrefix("R$ ")
        self.spn_preco.setMaximum(999999.99)
        self.spn_preco.setDecimals(2)
        self.spn_preco.setValue(self.produto.preco_padrao)

        form.addRow("Nome / Descrição *:", self.txt_nome)
        form.addRow("Tipo *:", self.cmb_tipo)
        form.addRow("Categoria:", self.txt_categoria)
        form.addRow("Unidade (SV/UN) *:", self.txt_unidade)
        form.addRow("Capacidade:", self.txt_capacidade)
        form.addRow("Preço Padrão *:", self.spn_preco)

        layout.addLayout(form)

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _ao_mudar_tipo(self):
        tipo = self.cmb_tipo.currentData()
        if tipo == TIPO_PRODUTO_SERVICO and not self.txt_unidade.text().strip():
            self.txt_unidade.setText(UNIDADE_SERVICO)
        elif tipo == TIPO_PRODUTO_PECA and not self.txt_unidade.text().strip():
            self.txt_unidade.setText(UNIDADE_PECA)

    def _salvar(self):
        nome = self.txt_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Aviso", "O nome do produto é obrigatório.")
            return

        self.produto.nome = nome
        self.produto.tipo = self.cmb_tipo.currentData()
        self.produto.categoria = self.txt_categoria.text().strip() or None
        self.produto.unidade = self.txt_unidade.text().strip() or UNIDADE_PECA
        self.produto.capacidade = self.txt_capacidade.text().strip() or None
        self.produto.preco_padrao = round(self.spn_preco.value(), 2)

        self.accept()


class ProdutosView(QWidget):
    """View principal de listagem e controle de produtos e serviços."""

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._init_ui()
        self.carregar_dados()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar produtos por nome, categoria, tipo...")
        self.txt_busca.textChanged.connect(self._ao_filtrar)
        toolbar.addWidget(self.txt_busca)

        btn_novo = QPushButton("+ Novo Produto / Serviço")
        btn_novo.clicked.connect(self._novo_produto)
        toolbar.addWidget(btn_novo)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self._editar_produto)
        toolbar.addWidget(btn_editar)

        btn_excluir = QPushButton("Excluir")
        btn_excluir.clicked.connect(self._excluir_produto)
        toolbar.addWidget(btn_excluir)

        layout.addLayout(toolbar)

        self.table = DataTable()
        self.model = ProdutosTableModel()
        self.proxy = GenericFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.doubleClicked.connect(self._editar_produto)

        layout.addWidget(self.table)

    def _ao_filtrar(self, texto: str):
        self.proxy.set_filter_text(texto)

    def carregar_dados(self):
        produtos = listar_produtos(self.conn)
        self.model.set_produtos(produtos)

    def _obter_produto_selecionado(self) -> Optional[Produto]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        proxy_idx = indexes[0]
        source_idx = self.proxy.mapToSource(proxy_idx)
        return self.model.get_produto(source_idx.row())

    def _novo_produto(self):
        dialog = ProdutoDialog(parent=self)
        if dialog.exec():
            try:
                criar_produto(self.conn, dialog.produto)
                self.conn.commit()
                self.carregar_dados()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Erro de Validação", f"Já existe um produto cadastrado com o nome '{dialog.produto.nome}'.")

    def _editar_produto(self):
        produto = self._obter_produto_selecionado()
        if not produto:
            QMessageBox.information(self, "Aviso", "Selecione um produto para editar.")
            return

        dialog = ProdutoDialog(produto=produto, parent=self)
        if dialog.exec():
            try:
                atualizar_produto(self.conn, dialog.produto)
                self.conn.commit()
                self.carregar_dados()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Erro de Validação", f"Já existe outro produto cadastrado com o nome '{dialog.produto.nome}'.")

    def _excluir_produto(self):
        produto = self._obter_produto_selecionado()
        if not produto:
            QMessageBox.information(self, "Aviso", "Selecione um produto para excluir.")
            return

        resp = QMessageBox.question(
            self, "Confirmação",
            f"Deseja realmente excluir o produto '{produto.nome}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            excluir_produto(self.conn, produto.id)
            self.conn.commit()
            self.carregar_dados()
