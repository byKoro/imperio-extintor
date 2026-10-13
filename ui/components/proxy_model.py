"""Modelo proxy para filtragem e ordenação em tabelas QTableView."""

from PySide6.QtCore import QSortFilterProxyModel, Qt, QModelIndex


class GenericFilterProxyModel(QSortFilterProxyModel):
    """Proxy model que suporta busca por texto livre em qualquer coluna e ordenação adequada."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._filter_text = ""

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._filter_text:
            return True

        model = self.sourceModel()
        if not model:
            return True

        col_count = model.columnCount(source_parent)
        for col in range(col_count):
            idx = model.index(source_row, col, source_parent)
            data = model.data(idx, Qt.ItemDataRole.DisplayRole)
            if data is not None and self._filter_text in str(data).lower():
                return True

        return False
