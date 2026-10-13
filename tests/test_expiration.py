"""Testes para o cálculo de status de vencimento dos extintores."""

from datetime import date
from app.core.constants import STATUS_VENCIMENTO_VALIDO, STATUS_VENCIMENTO_VENCIDO
from app.core.expiration import (
    normalizar_vencimento_banco,
    formatar_vencimento_exibicao,
    calcular_status_vencimento,
)


def test_normalizacao_e_formatacao_vencimento():
    """Testa armazenamento como dia 1 e exibição como MM/YYYY."""
    assert normalizar_vencimento_banco("10/2026") == "2026-10-01"
    assert normalizar_vencimento_banco("5/2026") == "2026-05-01"
    assert normalizar_vencimento_banco("2026-11") == "2026-11-01"
    assert normalizar_vencimento_banco("") is None

    assert formatar_vencimento_exibicao("2026-10-01") == "10/2026"
    assert formatar_vencimento_exibicao(None) == ""


def test_calculo_status_vencimento():
    """Testa status NA VALIDADE vs VENCIDO comparado à data de referência."""
    data_ref = date(2026, 10, 13)

    # Mês anterior já venceu
    assert calcular_status_vencimento("2026-09-01", data_ref) == STATUS_VENCIMENTO_VENCIDO
    assert calcular_status_vencimento("2025-12-01", data_ref) == STATUS_VENCIMENTO_VENCIDO

    # Mês atual ainda é considerado válido no mês
    assert calcular_status_vencimento("2026-10-01", data_ref) == STATUS_VENCIMENTO_VALIDO

    # Mês futuro é válido
    assert calcular_status_vencimento("2026-11-01", data_ref) == STATUS_VENCIMENTO_VALIDO
    assert calcular_status_vencimento("2027-05-01", data_ref) == STATUS_VENCIMENTO_VALIDO

    # Sem data cadastrada
    assert calcular_status_vencimento(None, data_ref) == STATUS_VENCIMENTO_VALIDO
