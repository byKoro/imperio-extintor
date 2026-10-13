"""Diálogo e controle da Tabela de Preços por Cliente."""

import sqlite3
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt
from db.models import Cliente
from db.repositories import (
    buscar_cliente_por_id, listar_precos_por_cliente,
    definir_preco_cliente, remover_preco_cliente
)


class PrecosClienteDialog(QDialog):
    """Diálogo para configurar tabela de preços customizada para um cliente."""

    def __init__(self, conn: sqlite3.Connection, cliente_id: int, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.cliente_id = cliente_id
        self.cliente = buscar_cliente_por_id(self.conn, cliente_id)
        nome_cliente = self.cliente.razao_social if self.cliente else f"ID {cliente_id}"
        self.setWindowTitle(f"Tabela de Preços — {nome_cliente}")
        self.resize(750, 480)
        self._init_ui()
        self.carregar_dados()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        lbl_info = QLabel(
            "Configure preços específicos para este cliente. "
            "Caso um produto não tenha preço customizado, o sistema utiliza o <b>preço padrão</b> da tabela geral."
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # Barra de busca
        search_bar = QHBoxLayout()
        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Filtrar produtos por nome ou categoria...")
        self.txt_busca.textChanged.connect(self._filtrar)
        search_bar.addWidget(self.txt_busca)
        layout.addLayout(search_bar)

        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Produto / Serviço", "Tipo", "Preço Padrão", "Preço Customizado", "Preço Efetivo"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Barra de ações
        action_bar = QHBoxLayout()
        btn_definir = QPushButton("Definir / Alterar Preço")
        btn_definir.clicked.connect(self._definir_preco)
        action_bar.addWidget(btn_definir)

        btn_remover = QPushButton("Restaurar Preço Padrão")
        btn_remover.clicked.connect(self._remover_preco)
        action_bar.addWidget(btn_remover)

        action_bar.addStretch()
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        action_bar.addWidget(btn_fechar)

        layout.addLayout(action_bar)

    def carregar_dados(self):
        self._dados = listar_precos_por_cliente(self.conn, self.cliente_id)
        self._atualizar_grade(self._dados)

    def _atualizar_grade(self, itens: List[Dict[str, Any]]):
        self.table.setRowCount(len(itens))

        for row, item in enumerate(itens):
            item_id = QTableWidgetItem(str(item["produto_id"]))
            item_nome = QTableWidgetItem(item["nome"])
            item_tipo = QTableWidgetItem("Serviço" if item["tipo"] == "SERVICO" else "Peça")
            item_padrao = QTableWidgetItem(f"R$ {item['preco_padrao']:.2f}".replace(".", ","))

            # Preço customizado
            if item["tem_personalizacao"]:
                item_custom = QTableWidgetItem(f"R$ {item['preco_cliente']:.2f}".replace(".", ","))
                from PySide6.QtGui import QColor
                item_custom.setForeground(QColor("#1565c0"))  # Azul para indicar personalização
            else:
                item_custom = QTableWidgetItem("- (Padrão)")

            item_efetivo = QTableWidgetItem(f"R$ {item['preco_efetivo']:.2f}".replace(".", ","))

            # Alinhamentos
            item_padrao.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_custom.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_efetivo.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_nome)
            self.table.setItem(row, 2, item_tipo)
            self.table.setItem(row, 3, item_padrao)
            self.table.setItem(row, 4, item_custom)
            self.table.setItem(row, 5, item_efetivo)

            # Guarda o produto_id na linha
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, item)

    def _filtrar(self, texto: str):
        t = texto.strip().lower()
        if not t:
            self._atualizar_grade(self._dados)
            return

        filtrados = [
            it for it in self._dados
            if t in it["nome"].lower() or t in (it["categoria"] or "").lower()
        ]
        self._atualizar_grade(filtrados)

    def _obter_item_selecionado(self) -> Optional[Dict[str, Any]]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item_widget = self.table.item(row, 0)
        if item_widget:
            return item_widget.data(Qt.ItemDataRole.UserRole)
        return None

    def _definir_preco(self):
        item = self._obter_item_selecionado()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecione um produto para definir o preço.")
            return

        dialog = DefinirPrecoDialog(item["nome"], item["preco_padrao"], item["preco_cliente"], parent=self)
        if dialog.exec():
            novo_preco = dialog.spn_preco.value()
            definir_preco_cliente(self.conn, self.cliente_id, item["produto_id"], novo_preco)
            self.conn.commit()
            self.carregar_dados()

    def _remover_preco(self):
        item = self._obter_item_selecionado()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecione um produto para restaurar o preço padrão.")
            return

        if not item["tem_personalizacao"]:
            QMessageBox.information(self, "Aviso", "Este produto já está utilizando o preço padrão da tabela.")
            return

        remover_preco_cliente(self.conn, self.cliente_id, item["produto_id"])
        self.conn.commit()
        self.carregar_dados()


class DefinirPrecoDialog(QDialog):
    """Mini diálogo para informar o novo preço customizado do produto."""

    def __init__(self, nome_produto: str, preco_padrao: float, preco_atual: Optional[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preço Diferenciado")
        self.setFixedWidth(350)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Produto:</b> {nome_produto}"))
        layout.addWidget(QLabel(f"Preço padrão atual: R$ {preco_padrao:.2f}".replace(".", ",")))

        layout.addWidget(QLabel("Informe o preço específico para este cliente:"))
        self.spn_preco = QDoubleSpinBox()
        self.spn_preco.setPrefix("R$ ")
        self.spn_preco.setMaximum(999999.99)
        self.spn_preco.setDecimals(2)
        self.spn_preco.setValue(preco_atual if preco_atual is not None else preco_padrao)
        layout.addWidget(self.spn_preco)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Salvar Preço")
        btn_ok.clicked.connect(self.accept)
        btn_canc = QPushButton("Cancelar")
        btn_canc.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_canc)
        layout.addLayout(btns)
