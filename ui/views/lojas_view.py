"""Tela de Gerenciamento de Lojas (CRUD) e Histórico de Atendimentos."""

import sqlite3
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QDialog, QFormLayout, QMessageBox, QDialogButtonBox,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from db.models import Loja, Cliente
from db.repositories import (
    listar_lojas_por_cliente, criar_loja, atualizar_loja,
    excluir_loja, listar_clientes, obter_historico_atendimentos_loja
)
from app.core.constants import MODELOS_BANDEIRA_PADRAO, STATUS_VENCIMENTO_VENCIDO
from app.core.expiration import (
    normalizar_vencimento_banco, formatar_vencimento_exibicao,
    calcular_status_vencimento
)
from ui.components.data_table import DataTable
from ui.components.proxy_model import GenericFilterProxyModel


class LojasTableModel(QAbstractTableModel):
    """Modelo de dados para a grade de lojas."""

    HEADERS = [
        "Código/ID", "Site", "Cidade", "UF", "Modelo / Bandeira",
        "Vencimento", "Status Vencimento", "Alerta", "Observações"
    ]

    def __init__(self, lojas: Optional[List[Loja]] = None):
        super().__init__()
        self._lojas = lojas or []

    def set_lojas(self, lojas: List[Loja]):
        self.beginResetModel()
        self._lojas = lojas
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._lojas)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        loja = self._lojas[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return loja.codigo_loja
            elif col == 1:
                return loja.nome_site
            elif col == 2:
                return loja.cidade
            elif col == 3:
                return loja.uf
            elif col == 4:
                return loja.modelo_bandeira
            elif col == 5:
                return formatar_vencimento_exibicao(loja.vencimento)
            elif col == 6:
                return calcular_status_vencimento(loja.vencimento)
            elif col == 7:
                return "NOTIFICADA" if loja.notificada else "Normal"
            elif col == 8:
                return loja.observacao or ""

        # Destaque visual para vencimento e alerta de notificação
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 6:
                status = calcular_status_vencimento(loja.vencimento)
                if status == STATUS_VENCIMENTO_VENCIDO:
                    from PySide6.QtGui import QColor
                    return QColor("#d32f2f")  # Vermelho para vencidos
            elif col == 7 and loja.notificada:
                from PySide6.QtGui import QColor
                return QColor("#e65100")  # Laranja para notificada

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def get_loja(self, row: int) -> Optional[Loja]:
        if 0 <= row < len(self._lojas):
            return self._lojas[row]
        return None


class LojaDialog(QDialog):
    """Diálogo para criação e edição de loja."""

    def __init__(self, cliente_id: int, loja: Optional[Loja] = None, parent=None):
        super().__init__(parent)
        self.cliente_id = cliente_id
        self.loja = loja or Loja(cliente_id=cliente_id)
        self.is_edicao = loja is not None and loja.id is not None
        self.setWindowTitle("Editar Loja" if self.is_edicao else "Nova Loja")
        self.setMinimumWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_codigo = QLineEdit(self.loja.codigo_loja)
        self.txt_site = QLineEdit(self.loja.nome_site)
        self.txt_cidade = QLineEdit(self.loja.cidade)
        self.txt_uf = QLineEdit(self.loja.uf)
        self.txt_uf.setMaxLength(2)

        self.cmb_modelo = QComboBox()
        self.cmb_modelo.setEditable(True)
        self.cmb_modelo.addItems(MODELOS_BANDEIRA_PADRAO)
        if self.loja.modelo_bandeira:
            self.cmb_modelo.setCurrentText(self.loja.modelo_bandeira)

        self.txt_vencimento = QLineEdit(formatar_vencimento_exibicao(self.loja.vencimento))
        self.txt_vencimento.setPlaceholderText("MM/AAAA (ex: 12/2026)")

        self.txt_observacao = QLineEdit(self.loja.observacao or "")
        self.chk_notificada = QCheckBox("Loja NOTIFICADA (chave de alerta)")
        self.chk_notificada.setChecked(bool(self.loja.notificada))

        form.addRow("Código / ID da Loja *:", self.txt_codigo)
        form.addRow("Nome do Site (Shopping / Local) *:", self.txt_site)
        form.addRow("Cidade *:", self.txt_cidade)
        form.addRow("UF *:", self.txt_uf)
        form.addRow("Modelo / Bandeira *:", self.cmb_modelo)
        form.addRow("Vencimento dos Extintores:", self.txt_vencimento)
        form.addRow("Observações Fixas:", self.txt_observacao)
        form.addRow("", self.chk_notificada)

        layout.addLayout(form)

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _salvar(self):
        codigo = self.txt_codigo.text().strip()
        site = self.txt_site.text().strip()
        cidade = self.txt_cidade.text().strip()
        uf = self.txt_uf.text().strip().upper()
        modelo = self.cmb_modelo.currentText().strip()

        if not codigo or not site or not cidade or not uf or not modelo:
            QMessageBox.warning(self, "Aviso", "Preencha todos os campos obrigatórios (Código, Site, Cidade, UF e Modelo).")
            return

        venc_banco = normalizar_vencimento_banco(self.txt_vencimento.text())

        self.loja.cliente_id = self.cliente_id
        self.loja.codigo_loja = codigo
        self.loja.nome_site = site
        self.loja.cidade = cidade
        self.loja.uf = uf
        self.loja.modelo_bandeira = modelo
        self.loja.vencimento = venc_banco
        self.loja.observacao = self.txt_observacao.text().strip() or None
        self.loja.notificada = 1 if self.chk_notificada.isChecked() else 0

        self.accept()


class HistoricoAtendimentosDialog(QDialog):
    """Diálogo para exibição do histórico de atendimentos de uma loja."""

    def __init__(self, conn: sqlite3.Connection, loja: Loja, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.loja = loja
        self.setWindowTitle(f"Histórico de Atendimentos — Loja {loja.codigo_loja} ({loja.nome_site})")
        self.resize(750, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        lbl_info = QLabel(
            f"<b>Loja:</b> {self.loja.codigo_loja} — {self.loja.nome_site} ({self.loja.cidade}/{self.loja.uf})<br>"
            f"<b>Vencimento cadastrado:</b> {formatar_vencimento_exibicao(self.loja.vencimento)} "
            f"({calcular_status_vencimento(self.loja.vencimento)})<br>"
            f"<i>Nota: Uma loja só é considerada atendida após o pedido ser FATURADO.</i>"
        )
        layout.addWidget(lbl_info)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Nº Pedido", "Data Emissão", "Data Execução", "Status Pedido", "Situação de Atendimento", "Valor Total"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self._carregar_dados()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)

    def _carregar_dados(self):
        if self.loja.id is None:
            return

        historico = obter_historico_atendimentos_loja(self.conn, self.loja.id)
        self.table.setRowCount(len(historico))

        for row, h in enumerate(historico):
            item_num = QTableWidgetItem(str(h["numero_pedido"]))
            item_emissao = QTableWidgetItem(str(h["data_emissao"] or ""))
            item_exec = QTableWidgetItem(str(h["data_execucao"] or "-"))
            item_status = QTableWidgetItem(str(h["status"]))
            item_sit = QTableWidgetItem(str(h["situacao_atendimento"]))
            item_val = QTableWidgetItem(f"R$ {h['valor_total']:.2f}".replace(".", ","))

            # Alinhamento
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Destaque para atendido vs pendente
            from PySide6.QtGui import QColor
            if h["atendido"]:
                item_sit.setForeground(QColor("#2e7d32"))  # Verde
            else:
                item_sit.setForeground(QColor("#d32f2f"))  # Vermelho/Pendente

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_emissao)
            self.table.setItem(row, 2, item_exec)
            self.table.setItem(row, 3, item_status)
            self.table.setItem(row, 4, item_sit)
            self.table.setItem(row, 5, item_val)


class LojasView(QWidget):
    """View principal de listagem e controle de lojas por cliente."""

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._init_ui()
        self.carregar_clientes()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Seletor de cliente e busca
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Cliente:"))
        self.cmb_clientes = QComboBox()
        self.cmb_clientes.currentIndexChanged.connect(self._ao_mudar_cliente)
        top_bar.addWidget(self.cmb_clientes, stretch=1)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por código, site, cidade, UF, modelo...")
        self.txt_busca.textChanged.connect(self._ao_filtrar)
        top_bar.addWidget(self.txt_busca, stretch=2)

        layout.addLayout(top_bar)

        # Barra de ações
        action_bar = QHBoxLayout()
        btn_nova = QPushButton("+ Nova Loja")
        btn_nova.clicked.connect(self._nova_loja)
        action_bar.addWidget(btn_nova)

        btn_editar = QPushButton("Editar")
        btn_editar.clicked.connect(self._editar_loja)
        action_bar.addWidget(btn_editar)

        btn_historico = QPushButton("Histórico de Atendimentos")
        btn_historico.clicked.connect(self._ver_historico)
        action_bar.addWidget(btn_historico)

        btn_excluir = QPushButton("Excluir")
        btn_excluir.clicked.connect(self._excluir_loja)
        action_bar.addWidget(btn_excluir)

        action_bar.addStretch()
        layout.addLayout(action_bar)

        # Tabela
        self.table = DataTable()
        self.model = LojasTableModel()
        self.proxy = GenericFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.doubleClicked.connect(self._editar_loja)

        layout.addWidget(self.table)

    def carregar_clientes(self, cliente_selecionado_id: Optional[int] = None):
        self.cmb_clientes.blockSignals(True)
        self.cmb_clientes.clear()
        clientes = listar_clientes(self.conn)
        target_idx = 0

        for i, c in enumerate(clientes):
            self.cmb_clientes.addItem(c.razao_social, c.id)
            if cliente_selecionado_id is not None and c.id == cliente_selecionado_id:
                target_idx = i

        self.cmb_clientes.blockSignals(False)

        if self.cmb_clientes.count() > 0:
            self.cmb_clientes.setCurrentIndex(target_idx)
            self._carregar_lojas_do_cliente_atual()
        else:
            self.model.set_lojas([])

    def selecionar_cliente(self, cliente_id: int):
        for i in range(self.cmb_clientes.count()):
            if self.cmb_clientes.itemData(i) == cliente_id:
                self.cmb_clientes.setCurrentIndex(i)
                break

    def _ao_mudar_cliente(self):
        self._carregar_lojas_do_cliente_atual()

    def _ao_filtrar(self, texto: str):
        self.proxy.set_filter_text(texto)

    def _obter_cliente_id_atual(self) -> Optional[int]:
        if self.cmb_clientes.currentIndex() >= 0:
            return self.cmb_clientes.currentData()
        return None

    def _carregar_lojas_do_cliente_atual(self):
        cliente_id = self._obter_cliente_id_atual()
        if cliente_id is None:
            self.model.set_lojas([])
            return
        lojas = listar_lojas_por_cliente(self.conn, cliente_id)
        self.model.set_lojas(lojas)

    def _obter_loja_selecionada(self) -> Optional[Loja]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        proxy_idx = indexes[0]
        source_idx = self.proxy.mapToSource(proxy_idx)
        return self.model.get_loja(source_idx.row())

    def _nova_loja(self):
        cliente_id = self._obter_cliente_id_atual()
        if cliente_id is None:
            QMessageBox.warning(self, "Aviso", "Selecione ou cadastre um cliente primeiro.")
            return

        dialog = LojaDialog(cliente_id=cliente_id, parent=self)
        if dialog.exec():
            try:
                criar_loja(self.conn, dialog.loja)
                self.conn.commit()
                self._carregar_lojas_do_cliente_atual()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Erro de Validação", f"Já existe uma loja com o código '{dialog.loja.codigo_loja}' para este cliente.")

    def _editar_loja(self):
        loja = self._obter_loja_selecionada()
        if not loja:
            QMessageBox.information(self, "Aviso", "Selecione uma loja para editar.")
            return

        dialog = LojaDialog(cliente_id=loja.cliente_id, loja=loja, parent=self)
        if dialog.exec():
            try:
                atualizar_loja(self.conn, dialog.loja)
                self.conn.commit()
                self._carregar_lojas_do_cliente_atual()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Erro de Validação", f"Já existe outra loja com o código '{dialog.loja.codigo_loja}' para este cliente.")

    def _excluir_loja(self):
        loja = self._obter_loja_selecionada()
        if not loja:
            QMessageBox.information(self, "Aviso", "Selecione uma loja para excluir.")
            return

        resp = QMessageBox.question(
            self, "Confirmação",
            f"Deseja realmente excluir a loja código '{loja.codigo_loja}' ({loja.nome_site})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            excluir_loja(self.conn, loja.id)
            self.conn.commit()
            self._carregar_lojas_do_cliente_atual()

    def _ver_historico(self):
        loja = self._obter_loja_selecionada()
        if not loja:
            QMessageBox.information(self, "Aviso", "Selecione uma loja para ver seu histórico de atendimentos.")
            return

        dialog = HistoricoAtendimentosDialog(self.conn, loja, parent=self)
        dialog.exec()
