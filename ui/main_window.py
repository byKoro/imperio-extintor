"""Janela Principal do Sistema Imperio Extintores."""

import sqlite3
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QStatusBar
)
from ui.views.clientes_view import ClientesView
from ui.views.lojas_view import LojasView
from ui.views.produtos_view import ProdutosView
from ui.views.precos_cliente_view import PrecosClienteDialog
from ui.views.pedidos_view import PedidosView


class MainWindow(QMainWindow):
    """Janela principal da aplicação com abas de navegação."""

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Império Extintores — Sistema de Gestão e Faturamento")
        self.resize(1100, 680)

        self._init_ui()

    def _init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 1. View de Clientes
        self.view_clientes = ClientesView(self.conn, self)
        self.view_clientes.abrir_lojas_solicitado.connect(self._navegar_para_lojas)
        self.view_clientes.abrir_precos_solicitado.connect(self._abrir_precos_cliente)
        self.tabs.addTab(self.view_clientes, "🏢 Clientes")

        # 2. View de Lojas
        self.view_lojas = LojasView(self.conn, self)
        self.tabs.addTab(self.view_lojas, "🏬 Lojas / Unidades")

        # 3. View de Produtos
        self.view_produtos = ProdutosView(self.conn, self)
        self.tabs.addTab(self.view_produtos, "🧯 Produtos e Serviços")

        # 4. View de Pedidos
        self.view_pedidos = PedidosView(self.conn, self)
        self.tabs.addTab(self.view_pedidos, "📋 Pedidos")

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Sistema pronto.")

        self.tabs.currentChanged.connect(self._ao_mudar_aba)

    def _ao_mudar_aba(self, index: int):
        if index == 0:
            self.view_clientes.carregar_dados()
        elif index == 1:
            self.view_lojas.carregar_clientes()
        elif index == 2:
            self.view_produtos.carregar_dados()
        elif index == 3:
            self.view_pedidos.recarregar_dados()

    def _navegar_para_lojas(self, cliente_id: int):
        self.tabs.setCurrentWidget(self.view_lojas)
        self.view_lojas.carregar_clientes(cliente_selecionado_id=cliente_id)

    def _abrir_precos_cliente(self, cliente_id: int):
        dialog = PrecosClienteDialog(self.conn, cliente_id, parent=self)
        dialog.exec()
