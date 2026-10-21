"""Cálculos puros de totais, subtotais e ajustes."""

from typing import Iterable, Protocol, List, Dict, Any
from app.core.constants import SECAO_SERVICOS, SECAO_PECAS, MODO_AJUSTE_DIFERENCA, MODO_AJUSTE_INCREMENTADO


class Calculavel(Protocol):
    secao: str
    quantidade: float
    preco_unitario: float


def calcular_total_item(quantidade: float, preco_unitario: float) -> float:
    """Calcula o total do item: quantidade * preco_unitario arredondado para 2 casas."""
    return round(float(quantidade) * float(preco_unitario), 2)


def calcular_subtotal_servicos(itens: Iterable[Calculavel]) -> float:
    """Calcula a soma dos totais da seção de Serviços."""
    total = sum(
        calcular_total_item(it.quantidade, it.preco_unitario)
        for it in itens
        if it.secao == SECAO_SERVICOS
    )
    return round(total, 2)


def calcular_subtotal_pecas(itens: Iterable[Calculavel]) -> float:
    """Calcula a soma dos totais da seção de Peças."""
    total = sum(
        calcular_total_item(it.quantidade, it.preco_unitario)
        for it in itens
        if it.secao == SECAO_PECAS
    )
    return round(total, 2)


def calcular_total_pedido(itens: Iterable[Calculavel]) -> float:
    """Calcula o valor total do pedido (Soma de Serviços + Peças).
    
    Regra de negócio 5.3: O total do pedido é o valor a ser cobrado.
    Nenhum desconto, acréscimo ou fórmula oculta é aplicado.
    """
    total = sum(
        calcular_total_item(it.quantidade, it.preco_unitario)
        for it in itens
    )
    return round(total, 2)


def calcular_totais_completos(itens: Iterable[Calculavel]) -> Dict[str, float]:
    """Retorna dicionário com os subtotais e total geral calculados."""
    sub_servicos = calcular_subtotal_servicos(itens)
    sub_pecas = calcular_subtotal_pecas(itens)
    total_geral = round(sub_servicos + sub_pecas, 2)
    return {
        "subtotal_servicos": sub_servicos,
        "subtotal_pecas": sub_pecas,
        "total_geral": total_geral,
    }


def calcular_ajuste_diferenca(itens_ajuste: Iterable[Calculavel]) -> float:
    """Modo 1 do ajuste: Somente a diferença.
    
    O valor a cobrar é a soma dos itens acrescentados.
    """
    return calcular_total_pedido(itens_ajuste)


def calcular_ajuste_incrementado(
    itens_originais: List[Calculavel],
    itens_ajuste: List[Calculavel]
) -> Dict[str, Any]:
    """Modo 2 do ajuste: Valores incrementados.
    
    Mantém apenas o comparativo de quantidades e totais:
    - quantidade original
    - quantidade acrescentada
    - quantidade final
    - total final
    """
    total_original = calcular_total_pedido(itens_originais)
    
    # Mapeia itens originais por descrição/chave para consolidar
    consolidado: Dict[str, Dict[str, Any]] = {}
    
    for it in itens_originais:
        chave = (it.secao, getattr(it, "descricao", ""), it.preco_unitario)
        consolidado[chave] = {
            "secao": it.secao,
            "descricao": getattr(it, "descricao", ""),
            "preco_unitario": it.preco_unitario,
            "qtd_original": it.quantidade,
            "qtd_acrescentada": 0.0,
            "qtd_final": it.quantidade,
            "total_final": calcular_total_item(it.quantidade, it.preco_unitario)
        }
        
    for it in itens_ajuste:
        chave = (it.secao, getattr(it, "descricao", ""), it.preco_unitario)
        if chave in consolidado:
            consolidado[chave]["qtd_acrescentada"] += it.quantidade
            consolidado[chave]["qtd_final"] = consolidado[chave]["qtd_original"] + consolidado[chave]["qtd_acrescentada"]
            consolidado[chave]["total_final"] = calcular_total_item(
                consolidado[chave]["qtd_final"],
                consolidado[chave]["preco_unitario"]
            )
        else:
            consolidado[chave] = {
                "secao": it.secao,
                "descricao": getattr(it, "descricao", ""),
                "preco_unitario": it.preco_unitario,
                "qtd_original": 0.0,
                "qtd_acrescentada": it.quantidade,
                "qtd_final": it.quantidade,
                "total_final": calcular_total_item(it.quantidade, it.preco_unitario)
            }
            
    itens_tabela = list(consolidado.values())
    total_final_acumulado = round(sum(it["total_final"] for it in itens_tabela), 2)
    
    return {
        "itens": itens_tabela,
        "total_original": total_original,
        "total_final": total_final_acumulado,
    }


def calcular_valor_a_cobrar_ajuste_incrementado(
    total_final: float,
    total_original: float
) -> float:
    """Valor a cobrar no modo 'valores incrementados': total final menos o já faturado.

    Regra confirmada pelo usuário (pendência 5 do to-do). Valores negativos são
    recusados em billing_service, não aqui.
    """
    return round(float(total_final) - float(total_original), 2)


def calcular_total_acumulado_pedido(valor_original: float, valores_ajustes: Iterable[float]) -> float:
    """Calcula o valor total acumulado do pedido (valor original + todos os ajustes realizados)."""
    return round(float(valor_original) + sum(float(v) for v in valores_ajustes), 2)
