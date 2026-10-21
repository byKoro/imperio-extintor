"""Testes da Fase 6: Destaque de vencidos e alerta NOTIFICADA na tela de lojas."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from datetime import date
import sqlite3
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from db.models import Loja, Cliente
from db.repositories import criar_cliente, criar_loja
from app.core.constants import STATUS_VENCIMENTO_VALIDO, STATUS_VENCIMENTO_VENCIDO
from app.core.expiration import calcular_status_vencimento
from ui.views.lojas_view import LojasTableModel, LojasView


def test_fronteira_regra_vencimento_funcao_pura():
    vencimento_10_2026 = "2026-10-01"
    status_31_10 = calcular_status_vencimento(vencimento_10_2026, data_referencia=date(2026, 10, 31))
    assert status_31_10 == STATUS_VENCIMENTO_VALIDO
    status_01_11 = calcular_status_vencimento(vencimento_10_2026, data_referencia=date(2026, 11, 1))
    assert status_01_11 == STATUS_VENCIMENTO_VENCIDO


def test_cores_foreground_role_lojas_table_model():
    loja_vencida_e_notificada = Loja(
        codigo_loja="LJ-01", nome_site="Shopping Vencido", cidade="São Paulo", uf="SP",
        modelo_bandeira="MODA", vencimento="2020-01-01", notificada=1,
    )
    loja_valida_e_normal = Loja(
        codigo_loja="LJ-02", nome_site="Shopping Na Validade", cidade="São Paulo", uf="SP",
        modelo_bandeira="CASA", vencimento="2035-12-01", notificada=0,
    )
    model = LojasTableModel([loja_vencida_e_notificada, loja_valida_e_normal])

    cor_venc_0 = model.data(model.index(0, 6), Qt.ItemDataRole.ForegroundRole)
    assert isinstance(cor_venc_0, QColor)
    assert cor_venc_0.name() == "#d32f2f"
    cor_alert_0 = model.data(model.index(0, 7), Qt.ItemDataRole.ForegroundRole)
    assert isinstance(cor_alert_0, QColor)
    assert cor_alert_0.name() == "#e65100"

    assert model.data(model.index(1, 6), Qt.ItemDataRole.ForegroundRole) is None
    assert model.data(model.index(1, 7), Qt.ItemDataRole.ForegroundRole) is None


def test_fronteira_vencimento_modelo_lojas_com_data_simulada(monkeypatch):
    import app.core.expiration as exp

    loja = Loja(
        codigo_loja="LJ-FRONTEIRA", nome_site="Shopping Fronteira", cidade="São Paulo", uf="SP",
        modelo_bandeira="FAN LAB", vencimento="2026-10-01", notificada=0,
    )
    model = LojasTableModel([loja])
    idx_venc = model.index(0, 6)

    MockDate31 = type("MockDate31", (date,), {"today": classmethod(lambda cls: date(2026, 10, 31))})
    monkeypatch.setattr(exp, "date", MockDate31)
    cor_em_31_10 = model.data(idx_venc, Qt.ItemDataRole.ForegroundRole)
    texto_em_31_10 = model.data(idx_venc, Qt.ItemDataRole.DisplayRole)
    assert texto_em_31_10 == "NA VALIDADE"
    assert cor_em_31_10 is None

    MockDate01 = type("MockDate01", (date,), {"today": classmethod(lambda cls: date(2026, 11, 1))})
    monkeypatch.setattr(exp, "date", MockDate01)
    cor_em_01_11 = model.data(idx_venc, Qt.ItemDataRole.ForegroundRole)
    texto_em_01_11 = model.data(idx_venc, Qt.ItemDataRole.DisplayRole)
    assert texto_em_01_11 == "VENCIDO"
    assert isinstance(cor_em_01_11, QColor)
    assert cor_em_01_11.name() == "#d32f2f"


def test_destaque_visual_integrado_lojas_view(qtbot, conn: sqlite3.Connection):
    c_id = criar_cliente(conn, Cliente(razao_social="CLIENTE FASE 6 LTDA"))
    criar_loja(conn, Loja(
        cliente_id=c_id, codigo_loja="LJ-01-VENC", nome_site="Site Vencido", cidade="São Paulo",
        uf="SP", modelo_bandeira="MODA", vencimento="2020-05-01", notificada=1,
    ))
    criar_loja(conn, Loja(
        cliente_id=c_id, codigo_loja="LJ-02-OK", nome_site="Site Válido", cidade="São Paulo",
        uf="SP", modelo_bandeira="CASA", vencimento="2035-10-01", notificada=0,
    ))
    conn.commit()

    view = LojasView(conn)
    qtbot.addWidget(view)
    view.carregar_clientes(cliente_selecionado_id=c_id)
    model = view.model

    assert model.rowCount() == 2
    assert model.data(model.index(0, 6), Qt.ItemDataRole.ForegroundRole).name() == "#d32f2f"
    assert model.data(model.index(0, 7), Qt.ItemDataRole.ForegroundRole).name() == "#e65100"
    assert model.data(model.index(1, 6), Qt.ItemDataRole.ForegroundRole) is None
    assert model.data(model.index(1, 7), Qt.ItemDataRole.ForegroundRole) is None
