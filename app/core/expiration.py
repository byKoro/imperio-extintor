"""Regras de cálculo de status de vencimento dos extintores."""

from datetime import date, datetime
from typing import Optional
from app.core.constants import STATUS_VENCIMENTO_VALIDO, STATUS_VENCIMENTO_VENCIDO


def normalizar_vencimento_banco(valor: Optional[str]) -> Optional[str]:
    """Converte formatos de mês/ano (ex.: '05/2026', '5/2026', '2026-05') para 'YYYY-MM-01'.
    
    Regra confirmada: o vencimento é mês/ano e guardado no banco como dia 1.
    """
    if not valor or not str(valor).strip():
        return None

    limpo = str(valor).strip()

    # Formato MM/YYYY ou M/YYYY
    if "/" in limpo:
        partes = limpo.split("/")
        if len(partes) == 2:
            mes, ano = int(partes[0]), int(partes[1])
            if ano < 100:
                ano += 2000
            return f"{ano:04d}-{mes:02d}-01"
        elif len(partes) == 3:
            # Caso venha dd/mm/aaaa
            _, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
            return f"{ano:04d}-{mes:02d}-01"

    # Formato ISO YYYY-MM ou YYYY-MM-DD
    if "-" in limpo:
        partes = limpo.split("-")
        if len(partes) >= 2:
            ano, mes = int(partes[0]), int(partes[1])
            return f"{ano:04d}-{mes:02d}-01"

    return None


def formatar_vencimento_exibicao(vencimento_iso: Optional[str]) -> str:
    """Converte 'YYYY-MM-01' para exibição amigável 'MM/YYYY'."""
    if not vencimento_iso:
        return ""
    try:
        dt = datetime.strptime(vencimento_iso[:10], "%Y-%m-%d")
        return dt.strftime("%m/%Y")
    except ValueError:
        return vencimento_iso


def calcular_status_vencimento(
    vencimento_iso: Optional[str],
    data_referencia: Optional[date] = None
) -> str:
    """Calcula se o extintor está NA VALIDADE ou VENCIDO.
    
    Regra 10: O status de cada loja (VENCIDO ou NA VALIDADE) é calculado
    comparando a data de vencimento com a data atual.
    Vencimento é no nível mês/ano. Se o mês/ano de vencimento já passou em relação
    à data de referência, considera-se VENCIDO.
    """
    if not vencimento_iso:
        return STATUS_VENCIMENTO_VALIDO

    ref = data_referencia or date.today()

    try:
        dt_venc = datetime.strptime(vencimento_iso[:10], "%Y-%m-%d").date()
    except ValueError:
        return STATUS_VENCIMENTO_VALIDO

    # Compara ano e mês
    if (dt_venc.year, dt_venc.month) < (ref.year, ref.month):
        return STATUS_VENCIMENTO_VENCIDO

    return STATUS_VENCIMENTO_VALIDO
