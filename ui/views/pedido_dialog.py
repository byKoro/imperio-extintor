"""Diálogo de criação, edição e visualização de pedidos."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QWidget, QDoubleSpinBox, QGroupBox
)
from db.models import Pedido, ItemPedido, Cliente, Loja, Produto
import db.repositories as repo
import app.core.order_service as service
from app.core.calculations import (
    calcular_subtotal_servicos, calcular_subtotal_pecas,
    calcular_total_pedido, calcular_total_item
)


def formatar_data_br_para_iso(data_br: str) -> str:
    """Converte 'dd/mm/aaaa' para 'YYYY-MM-DD', validando dias no calendário (rejeita 31/02/2026)."""
    data_limpa = data_br.strip() if data_br else ""
    if not data_limpa:
        raise ValueError("Data não informada.")
    try:
        dt = datetime.strptime(data_limpa, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Data inválida: '{data_limpa}'. Use o formato dd/mm/aaaa com uma data válida no calendário.")


def formatar_data_iso_para_br(data_iso: Optional[str]) -> str:
    """Converte 'YYYY-MM-DD' para 'dd/mm/aaaa'."""
    if not data_iso:
        return ""
    try:
        dt = datetime.strptime(data_iso.strip(), "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return data_iso


class ItemAvulsoDialog(QDialog):
    """Diálogo modal simples para adicionar item avulso."""

    def __init__(self, secao: str, parent=None):
        super().__init__(parent)
        self.secao = secao
        self.setWindowTitle(f"Adicionar Item Avulso — {secao.capitalize()}")
        self.setFixedWidth(420)

        layout = QFormLayout(self)

        self.txt_descricao = QLineEdit()
        self.txt_descricao.setPlaceholderText("Descrição livre do item avulso...")
        layout.addRow("Descrição *:", self.txt_descricao)

        self.spn_quantidade = QDoubleSpinBox()
        self.spn_quantidade.setRange(0.01, 999999.0)
        self.spn_quantidade.setValue(1.0)
        self.spn_quantidade.setDecimals(2)
        layout.addRow("Quantidade *:", self.spn_quantidade)

        self.cbo_unidade = QComboBox()
        self.cbo_unidade.addItems(["UN", "SV"])
        if secao == "SERVICO":
            self.cbo_unidade.setCurrentText("SV")
        layout.addRow("Unidade *:", self.cbo_unidade)

        self.spn_preco = QDoubleSpinBox()
        self.spn_preco.setRange(0.0, 999999.0)
        self.spn_preco.setValue(0.0)
        self.spn_preco.setDecimals(2)
        self.spn_preco.setPrefix("R$ ")
        layout.addRow("Preço Unitário *:", self.spn_preco)

        btn_box = QHBoxLayout()
        btn_salvar = QPushButton("Confirmar")
        btn_salvar.clicked.connect(self._confirmar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(btn_salvar)
        layout.addRow(btn_box)

        self.item: Optional[ItemPedido] = None

    def _confirmar(self):
        desc = self.txt_descricao.text().strip()
        if not desc:
            QMessageBox.warning(self, "Aviso", "A descrição do item avulso é obrigatória.")
            return

        self.item = ItemPedido(
            produto_id=None,
            secao=self.secao,
            descricao=desc,
            quantidade=float(self.spn_quantidade.value()),
            unidade=self.cbo_unidade.currentText(),
            preco_unitario=float(self.spn_preco.value()),
            valor_total=round(float(self.spn_quantidade.value()) * float(self.spn_preco.value()), 2)
        )
        self.accept()


class SelecionarCatalogoDialog(QDialog):
    """Diálogo modal para selecionar produtos ativos do catálogo com preço sugerido."""

    def __init__(self, conn: sqlite3.Connection, cliente_id: int, secao: str, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.cliente_id = cliente_id
        self.secao = secao
        self.setWindowTitle(f"Selecionar do Catálogo — {secao.capitalize()}")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(4)
        self.tabela.setHorizontalHeaderLabels(["ID", "Produto / Serviço", "Unidade", "Preço Sugerido"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabela)

        form_qtd = QFormLayout()
        self.spn_qtd = QDoubleSpinBox()
        self.spn_qtd.setRange(0.01, 999999.0)
        self.spn_qtd.setValue(1.0)
        self.spn_qtd.setDecimals(2)
        form_qtd.addRow("Quantidade a inserir:", self.spn_qtd)
        layout.addLayout(form_qtd)

        btn_box = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_adicionar = QPushButton("Adicionar ao Pedido")
        btn_adicionar.clicked.connect(self._adicionar)
        btn_box.addWidget(btn_cancelar)
        btn_box.addWidget(btn_adicionar)
        layout.addLayout(btn_box)

        self.produtos: List[Dict[str, Any]] = []
        self.item_selecionado: Optional[ItemPedido] = None
        self._carregar_produtos()

    def _carregar_produtos(self):
        # Busca produtos ativos com o tipo correspondente
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.id, p.nome, p.unidade, p.preco_padrao, pc.preco as preco_cliente
            FROM produtos p
            LEFT JOIN precos_cliente pc ON pc.produto_id = p.id AND pc.cliente_id = ?
            WHERE p.ativo = 1 AND p.tipo = ?
            ORDER BY p.nome
        """, (self.cliente_id, self.secao))

        rows = cursor.fetchall()
        self.tabela.setRowCount(len(rows))
        self.produtos.clear()

        for r_idx, row in enumerate(rows):
            p_id = row["id"]
            p_nome = row["nome"]
            p_unidade = row["unidade"]
            p_sugerido = float(row["preco_cliente"]) if row["preco_cliente"] is not None else float(row["preco_padrao"])

            self.produtos.append({
                "id": p_id,
                "nome": p_nome,
                "unidade": p_unidade,
                "preco": p_sugerido,
            })

            self.tabela.setItem(r_idx, 0, QTableWidgetItem(str(p_id)))
            self.tabela.setItem(r_idx, 1, QTableWidgetItem(p_nome))
            self.tabela.setItem(r_idx, 2, QTableWidgetItem(p_unidade))
            self.tabela.setItem(r_idx, 3, QTableWidgetItem(f"R$ {p_sugerido:.2f}".replace(".", ",")))

        if len(rows) > 0:
            self.tabela.selectRow(0)

    def _adicionar(self):
        sel = self.tabela.currentRow()
        if sel < 0 or sel >= len(self.produtos):
            QMessageBox.warning(self, "Aviso", "Selecione um produto da lista.")
            return

        prod = self.produtos[sel]
        qtd = float(self.spn_qtd.value())
        preco = float(prod["preco"])

        self.item_selecionado = ItemPedido(
            produto_id=prod["id"],
            secao=self.secao,
            descricao=prod["nome"],
            quantidade=qtd,
            unidade=prod["unidade"],
            preco_unitario=preco,
            valor_total=round(qtd * preco, 2)
        )
        self.accept()


class PedidoDialog(QDialog):
    """Diálogo principal para criação e edição de pedidos com seções Serviços/Peças."""

    def __init__(self, conn: sqlite3.Connection, pedido_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.pedido_id = pedido_id
        self.pedido: Optional[Pedido] = None
        self.itens: List[ItemPedido] = []

        self.setWindowTitle("Novo Pedido" if pedido_id is None else f"Pedido #{pedido_id}")
        self.resize(950, 680)

        self._criar_ui()
        self._carregar_dados()

    def _criar_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Cabeçalho do Pedido
        grp_cabecalho = QGroupBox("Dados do Pedido")
        grid_cab = QGridLayout(grp_cabecalho)

        grid_cab.addWidget(QLabel("Cliente *:"), 0, 0)
        self.cbo_cliente = QComboBox()
        self.cbo_cliente.currentIndexChanged.connect(self._on_cliente_alterado)
        grid_cab.addWidget(self.cbo_cliente, 0, 1)

        grid_cab.addWidget(QLabel("Loja *:"), 0, 2)
        self.cbo_loja = QComboBox()
        grid_cab.addWidget(self.cbo_loja, 0, 3)

        grid_cab.addWidget(QLabel("Nº Pedido *:"), 1, 0)
        self.txt_numero = QLineEdit()
        self.txt_numero.setPlaceholderText("Ex: 2026101")
        grid_cab.addWidget(self.txt_numero, 1, 1)

        grid_cab.addWidget(QLabel("Status:"), 1, 2)
        self.lbl_status = QLabel("ABERTO")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #1976d2;")
        grid_cab.addWidget(self.lbl_status, 1, 3)

        grid_cab.addWidget(QLabel("Data Emissão * (dd/mm/aaaa):"), 2, 0)
        self.txt_data_emissao = QLineEdit()
        self.txt_data_emissao.setPlaceholderText("dd/mm/aaaa")
        grid_cab.addWidget(self.txt_data_emissao, 2, 1)

        grid_cab.addWidget(QLabel("Data Execução (dd/mm/aaaa):"), 2, 2)
        self.txt_data_execucao = QLineEdit()
        self.txt_data_execucao.setPlaceholderText("dd/mm/aaaa (obrigatória se Executado)")
        grid_cab.addWidget(self.txt_data_execucao, 2, 3)

        main_layout.addWidget(grp_cabecalho)

        # 2. Abas: Itens (Serviços / Peças) e Condições Comerciais
        self.tabs = QTabWidget()

        # Aba de Serviços
        tab_servicos = QWidget()
        lay_serv = QVBoxLayout(tab_servicos)
        self.tab_servicos_widget = self._criar_tabela_itens()
        lay_serv.addWidget(self.tab_servicos_widget)
        lay_serv.addLayout(self._criar_botoes_itens("SERVICO"))
        self.tabs.addTab(tab_servicos, "🛠️ Serviços")

        # Aba de Peças
        tab_pecas = QWidget()
        lay_pecas = QVBoxLayout(tab_pecas)
        self.tab_pecas_widget = self._criar_tabela_itens()
        lay_pecas.addWidget(self.tab_pecas_widget)
        lay_pecas.addLayout(self._criar_botoes_itens("PECA"))
        self.tabs.addTab(tab_pecas, "🔩 Peças")

        # Aba de Condições Comerciais
        tab_condicoes = QWidget()
        lay_cond = QFormLayout(tab_condicoes)
        self.txt_prazo_pagamento = QLineEdit()
        self.txt_forma_pagamento = QLineEdit()
        self.txt_prazo_entrega = QLineEdit()
        self.txt_texto_impostos = QLineEdit()
        self.txt_observacoes = QTextEdit()
        self.txt_observacoes.setPlaceholderText("Observações gerais do pedido...")

        lay_cond.addRow("Prazo de Pagamento:", self.txt_prazo_pagamento)
        lay_cond.addRow("Forma de Pagamento:", self.txt_forma_pagamento)
        lay_cond.addRow("Prazo de Entrega:", self.txt_prazo_entrega)
        lay_cond.addRow("Texto de Impostos:", self.txt_texto_impostos)
        lay_cond.addRow("Observações:", self.txt_observacoes)
        self.tabs.addTab(tab_condicoes, "📝 Condições Comerciais")

        main_layout.addWidget(self.tabs)

        # 3. Painel de Totais
        grp_totais = QGroupBox("Totais do Pedido")
        lay_totais = QHBoxLayout(grp_totais)

        self.lbl_subtotal_servicos = QLabel("Subtotal Serviços: R$ 0,00")
        self.lbl_subtotal_pecas = QLabel("Subtotal Peças: R$ 0,00")
        self.lbl_total_geral = QLabel("TOTAL GERAL: R$ 0,00")
        self.lbl_total_geral.setStyleSheet("font-size: 14px; font-weight: bold; color: #2e7d32;")

        lay_totais.addWidget(self.lbl_subtotal_servicos)
        lay_totais.addSpacing(20)
        lay_totais.addWidget(self.lbl_subtotal_pecas)
        lay_totais.addStretch()
        lay_totais.addWidget(self.lbl_total_geral)
        main_layout.addWidget(grp_totais)

        # 4. Botões de Ação
        bar_botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_salvar = QPushButton("Salvar Pedido")
        self.btn_salvar.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_salvar.clicked.connect(self._salvar)

        bar_botoes.addStretch()
        bar_botoes.addWidget(self.btn_cancelar)
        bar_botoes.addWidget(self.btn_salvar)
        main_layout.addLayout(bar_botoes)

    def _criar_tabela_itens(self) -> QTableWidget:
        tabela = QTableWidget()
        tabela.setColumnCount(5)
        tabela.setHorizontalHeaderLabels(["Descrição", "Qtd", "Unid", "Preço Unit.", "Total"])
        tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return tabela

    def _criar_botoes_itens(self, secao: str) -> QHBoxLayout:
        box = QHBoxLayout()
        btn_catalogo = QPushButton(f"Adicionar do Catálogo")
        btn_catalogo.clicked.connect(lambda: self._adicionar_do_catalogo(secao))

        btn_avulso = QPushButton(f"Adicionar Avulso")
        btn_avulso.clicked.connect(lambda: self._adicionar_avulso(secao))

        btn_remover = QPushButton("Remover Item Selecionado")
        btn_remover.clicked.connect(lambda: self._remover_item(secao))

        box.addWidget(btn_catalogo)
        box.addWidget(btn_avulso)
        box.addStretch()
        box.addWidget(btn_remover)
        return box

    def _carregar_dados(self):
        if self.pedido_id is None:
            # Novo pedido: lista apenas clientes ativos
            clientes = repo.listar_clientes_ativos(self.conn)
            for c in clientes:
                self.cbo_cliente.addItem(c.razao_social, c.id)

            # Data de emissão pré-preenchida com a data de hoje no formato BR
            hoje_br = datetime.now().strftime("%d/%m/%Y")
            self.txt_data_emissao.setText(hoje_br)
            self.lbl_status.setText("ABERTO")
        else:
            # Edição / visualização de pedido existente
            self.pedido = repo.buscar_pedido_por_id(self.conn, self.pedido_id)
            if not self.pedido:
                QMessageBox.critical(self, "Erro", "Pedido não encontrado.")
                self.reject()
                return

            # Garante que o cliente do pedido seja exibido mesmo se inativo
            cli_pedido = repo.buscar_cliente_por_id(self.conn, self.pedido.cliente_id)
            clientes = repo.listar_clientes_ativos(self.conn)
            cli_ids = [c.id for c in clientes]
            if cli_pedido and cli_pedido.id not in cli_ids:
                clientes.insert(0, cli_pedido)

            for c in clientes:
                self.cbo_cliente.addItem(c.razao_social, c.id)

            idx_cli = self.cbo_cliente.findData(self.pedido.cliente_id)
            if idx_cli >= 0:
                self.cbo_cliente.setCurrentIndex(idx_cli)

            self.txt_numero.setText(self.pedido.numero_pedido)
            self.lbl_status.setText(self.pedido.status)
            self.txt_data_emissao.setText(formatar_data_iso_para_br(self.pedido.data_emissao))
            self.txt_data_execucao.setText(formatar_data_iso_para_br(self.pedido.data_execucao))

            self.txt_prazo_pagamento.setText(self.pedido.prazo_pagamento or "")
            self.txt_forma_pagamento.setText(self.pedido.forma_pagamento or "")
            self.txt_prazo_entrega.setText(self.pedido.prazo_entrega or "")
            self.txt_texto_impostos.setText(self.pedido.texto_impostos or "")
            self.txt_observacoes.setText(self.pedido.observacoes or "")

            # Carrega itens existentes
            self.itens = repo.listar_itens_pedido(self.conn, self.pedido_id)
            self._atualizar_tabelas_itens()

            # Bloqueio estrito se FATURADO ou PAGO
            if self.pedido.status in ("FATURADO", "PAGO"):
                self._aplicar_bloqueio_somente_leitura()

    def _on_cliente_alterado(self):
        cliente_id = self.cbo_cliente.currentData()
        if cliente_id is None:
            self.cbo_loja.clear()
            return

        # Carrega lojas do cliente
        incluir_loja = self.pedido.loja_id if (self.pedido and self.pedido.cliente_id == cliente_id) else None
        lojas = repo.listar_lojas_por_cliente(self.conn, cliente_id, incluir_loja_id=incluir_loja)

        self.cbo_loja.clear()
        for l in lojas:
            label = f"{l.codigo_loja} — {l.nome_site} ({l.cidade}/{l.uf})"
            self.cbo_loja.addItem(label, l.id)

        if self.pedido and self.pedido.cliente_id == cliente_id:
            idx_l = self.cbo_loja.findData(self.pedido.loja_id)
            if idx_l >= 0:
                self.cbo_loja.setCurrentIndex(idx_l)

        # Se for NOVO pedido, copia as condições comerciais padrão do cliente
        if self.pedido_id is None:
            cli = repo.buscar_cliente_por_id(self.conn, cliente_id)
            if cli:
                self.txt_prazo_pagamento.setText(cli.prazo_pagamento or "30 dias")
                self.txt_forma_pagamento.setText(cli.forma_pagamento or "Transferência bancária")
                self.txt_prazo_entrega.setText(cli.prazo_entrega or "7 dias úteis")
                self.txt_texto_impostos.setText(cli.texto_impostos or "Impostos inclusos")

    def _adicionar_do_catalogo(self, secao: str):
        cliente_id = self.cbo_cliente.currentData()
        if not cliente_id:
            QMessageBox.warning(self, "Aviso", "Selecione o cliente antes de adicionar itens.")
            return

        dlg = SelecionarCatalogoDialog(self.conn, cliente_id, secao, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.item_selecionado:
            self.itens.append(dlg.item_selecionado)
            self._atualizar_tabelas_itens()

    def _adicionar_avulso(self, secao: str):
        dlg = ItemAvulsoDialog(secao, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.item:
            self.itens.append(dlg.item)
            self._atualizar_tabelas_itens()

    def _remover_item(self, secao: str):
        tabela = self.tab_servicos_widget if secao == "SERVICO" else self.tab_pecas_widget
        row = tabela.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione um item da tabela para remover.")
            return

        # Filtra os itens da seção para descobrir o índice no self.itens
        itens_secao = [it for it in self.itens if it.secao == secao]
        if row < len(itens_secao):
            item_remover = itens_secao[row]
            self.itens.remove(item_remover)
            self._atualizar_tabelas_itens()

    def _atualizar_tabelas_itens(self):
        servicos = [it for it in self.itens if it.secao == "SERVICO"]
        pecas = [it for it in self.itens if it.secao == "PECA"]

        self._preencher_tabela(self.tab_servicos_widget, servicos)
        self._preencher_tabela(self.tab_pecas_widget, pecas)

        # Atualiza totais usando cálculos centralizados
        sub_serv = calcular_subtotal_servicos(self.itens)
        sub_pec = calcular_subtotal_pecas(self.itens)
        total_geral = calcular_total_pedido(self.itens)

        self.lbl_subtotal_servicos.setText(f"Subtotal Serviços: R$ {sub_serv:.2f}".replace(".", ","))
        self.lbl_subtotal_pecas.setText(f"Subtotal Peças: R$ {sub_pec:.2f}".replace(".", ","))
        self.lbl_total_geral.setText(f"TOTAL GERAL: R$ {total_geral:.2f}".replace(".", ","))

    def _preencher_tabela(self, tabela: QTableWidget, itens: List[ItemPedido]):
        tabela.setRowCount(len(itens))
        for r, it in enumerate(itens):
            tabela.setItem(r, 0, QTableWidgetItem(it.descricao))
            tabela.setItem(r, 1, QTableWidgetItem(f"{it.quantidade:.2f}"))
            tabela.setItem(r, 2, QTableWidgetItem(it.unidade))
            tabela.setItem(r, 3, QTableWidgetItem(f"R$ {it.preco_unitario:.2f}".replace(".", ",")))
            tabela.setItem(r, 4, QTableWidgetItem(f"R$ {it.valor_total:.2f}".replace(".", ",")))

    def _aplicar_bloqueio_somente_leitura(self):
        """Bloqueia todos os campos e ações para pedidos FATURADO ou PAGO."""
        self.cbo_cliente.setEnabled(False)
        self.cbo_loja.setEnabled(False)
        self.txt_numero.setReadOnly(True)
        self.txt_data_emissao.setReadOnly(True)
        self.txt_data_execucao.setReadOnly(True)
        self.txt_prazo_pagamento.setReadOnly(True)
        self.txt_forma_pagamento.setReadOnly(True)
        self.txt_prazo_entrega.setReadOnly(True)
        self.txt_texto_impostos.setReadOnly(True)
        self.txt_observacoes.setReadOnly(True)

        # Desabilita botões de adicionar e remover
        for w in self.findChildren(QPushButton):
            if w not in (self.btn_cancelar,):
                w.setEnabled(False)

        self.btn_salvar.setVisible(False)
        self.btn_cancelar.setText("Fechar")

    def _salvar(self):
        cliente_id = self.cbo_cliente.currentData()
        if not cliente_id:
            QMessageBox.warning(self, "Aviso", "Selecione um cliente.")
            return

        loja_id = self.cbo_loja.currentData()
        if not loja_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma loja.")
            return

        numero = self.txt_numero.text().strip()
        if not numero:
            QMessageBox.warning(self, "Aviso", "Informe o número do pedido.")
            return

        # Validação de unicidade do número
        try:
            service.validar_numero_pedido(self.conn, cliente_id, numero, exceto_pedido_id=self.pedido_id)
        except ValueError as e:
            QMessageBox.warning(self, "Erro de Validação", str(e))
            return

        # Conversão e validação rigorosa de datas (rejeita 31/02/2026)
        try:
            data_emissao_iso = formatar_data_br_para_iso(self.txt_data_emissao.text())
        except ValueError as e:
            QMessageBox.warning(self, "Data de Emissão Inválida", str(e))
            return

        data_exec_iso = None
        data_exec_txt = self.txt_data_execucao.text().strip()
        if data_exec_txt:
            try:
                data_exec_iso = formatar_data_br_para_iso(data_exec_txt)
            except ValueError as e:
                QMessageBox.warning(self, "Data de Execução Inválida", str(e))
                return

        status_atual = self.lbl_status.text()
        if status_atual == "EXECUTADO" and not data_exec_iso:
            QMessageBox.warning(self, "Aviso", "A data de execução é obrigatória para pedidos com status EXECUTADO.")
            return

        # Se for edição, verifica se não está bloqueado
        if self.pedido:
            try:
                service.verificar_permissao_edicao(self.pedido)
            except PermissionError as e:
                QMessageBox.critical(self, "Bloqueio", str(e))
                return

        # Monta objeto Pedido
        pedido_salvar = Pedido(
            id=self.pedido_id,
            cliente_id=cliente_id,
            loja_id=loja_id,
            numero_pedido=numero,
            data_emissao=data_emissao_iso,
            data_execucao=data_exec_iso,
            status=status_atual,
            observacoes=self.txt_observacoes.toPlainText().strip() or None,
            prazo_pagamento=self.txt_prazo_pagamento.text().strip() or None,
            forma_pagamento=self.txt_forma_pagamento.text().strip() or None,
            prazo_entrega=self.txt_prazo_entrega.text().strip() or None,
            texto_impostos=self.txt_texto_impostos.text().strip() or None,
        )

        try:
            repo.salvar_pedido_completo(self.conn, pedido_salvar, self.itens)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Ocorreu um erro ao salvar o pedido:\n{e}")
