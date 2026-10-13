"""Testes das regras de cálculo (totais, subtotais, modos de ajuste e acumulados)."""

import pytest
from app.core.constants import SECAO_SERVICOS, SECAO_PECAS
from app.core.calculations import (
    calcular_total_item,
    calcular_subtotal_servicos,
    calcular_subtotal_pecas,
    calcular_total_pedido,
    calcular_totais_completos,
    calcular_ajuste_diferenca,
    calcular_ajuste_incrementado,
    calcular_valor_a_cobrar_ajuste_incrementado,
    calcular_total_acumulado_pedido,
)
from db.models import ItemPedido, ItemAjuste


def test_calcular_total_item():
    """Testa arredondamento e multiplicação de item."""
    assert calcular_total_item(3, 50.0) == 150.00
    assert calcular_total_item(2.5, 33.33) == 83.32
    assert calcular_total_item(0, 100.0) == 0.00


def test_subtotais_servicos_e_pecas():
    """Testa se os subtotais separam corretamente serviços e peças."""
    itens = [
        ItemPedido(secao=SECAO_SERVICOS, descricao="Recarga AP 10L", quantidade=4, preco_unitario=50.0),
        ItemPedido(secao=SECAO_SERVICOS, descricao="Recarga CO2 6KG", quantidade=2, preco_unitario=160.0),
        ItemPedido(secao=SECAO_PECAS, descricao="Manômetro", quantidade=3, preco_unitario=12.5),
        ItemPedido(secao=SECAO_PECAS, descricao="Válvula", quantidade=1, preco_unitario=95.0),
    ]

    # Serviços: (4 * 50) + (2 * 160) = 200 + 320 = 520.00
    assert calcular_subtotal_servicos(itens) == 520.00

    # Peças: (3 * 12.5) + (1 * 95) = 37.50 + 95 = 132.50
    assert calcular_subtotal_pecas(itens) == 132.50

    # Total Geral = 520.00 + 132.50 = 652.50
    assert calcular_total_pedido(itens) == 652.50

    totais = calcular_totais_completos(itens)
    assert totais["subtotal_servicos"] == 520.00
    assert totais["subtotal_pecas"] == 132.50
    assert totais["total_geral"] == 652.50


def test_modo_ajuste_diferenca():
    """Testa o Modo 1 do ajuste: Somente a diferença cobrada."""
    itens_ajuste = [
        ItemAjuste(secao=SECAO_SERVICOS, descricao="Recarga AP 10L adicional", quantidade=2, preco_unitario=50.0),
        ItemAjuste(secao=SECAO_PECAS, descricao="Manômetro extra", quantidade=1, preco_unitario=15.0),
    ]
    # Total a cobrar: (2 * 50) + (1 * 15) = 115.00
    valor_a_cobrar = calcular_ajuste_diferenca(itens_ajuste)
    assert valor_a_cobrar == 115.00


def test_modo_ajuste_valores_incrementados():
    """Testa o Modo 2 do ajuste: Valores incrementados."""
    itens_originais = [
        ItemPedido(secao=SECAO_SERVICOS, descricao="Recarga AP 10L", quantidade=4, preco_unitario=50.0),
        ItemPedido(secao=SECAO_PECAS, descricao="Manômetro", quantidade=2, preco_unitario=15.0),
    ]
    # Total original: 200 + 30 = 230.00

    itens_ajuste = [
        ItemAjuste(secao=SECAO_SERVICOS, descricao="Recarga AP 10L", quantidade=2, preco_unitario=50.0),
        ItemAjuste(secao=SECAO_PECAS, descricao="Válvula Nova", quantidade=1, preco_unitario=90.0),
    ]
    # Acréscimo: (2 * 50) + (1 * 90) = 190.00
    # Final: Recarga 6 * 50 = 300, Manômetro 2 * 15 = 30, Válvula 1 * 90 = 90 -> Total Final = 420.00
    # Valor a cobrar = 420.00 - 230.00 = 190.00

    resultado = calcular_ajuste_incrementado(itens_originais, itens_ajuste)
    assert resultado["total_original"] == 230.00
    assert resultado["total_final"] == 420.00
    assert "valor_a_cobrar" not in resultado
    assert len(resultado["itens"]) == 3

    # A pendência 5 do to-do não foi confirmada; a função de cobrança deve levantar NotImplementedError
    with pytest.raises(NotImplementedError, match="Pendente de confirmação: pendência 5 do to-do"):
        calcular_valor_a_cobrar_ajuste_incrementado(resultado["total_final"], resultado["total_original"])


def test_total_acumulado_pedido():
    """Testa histórico acumulado de pedido com múltiplos ajustes."""
    valor_original = 500.00
    ajustes = [100.00, 55.50]
    total_acumulado = calcular_total_acumulado_pedido(valor_original, ajustes)
    assert total_acumulado == 655.50
