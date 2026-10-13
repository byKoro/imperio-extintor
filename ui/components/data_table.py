"""Widget de QTableView padronizado para o sistema."""

from PySide6.QtWidgets import QTableView, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt


class DataTable(QTableView):
    """Tabela padrão baseada em QTableView com estilo limpo, seleção por linha e ordenação."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
