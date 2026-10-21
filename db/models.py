"""Modelos de dados (dataclasses) do sistema."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Cliente:
    id: Optional[int] = None
    razao_social: str = ""
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    contato: Optional[str] = None
    prazo_pagamento: str = "30 dias"
    forma_pagamento: str = "Transferência bancária"
    prazo_entrega: str = "7 dias úteis"
    texto_impostos: str = "Impostos inclusos"
    ativo: int = 1
    created_at: Optional[str] = None


@dataclass
class Loja:
    id: Optional[int] = None
    cliente_id: int = 0
    codigo_loja: str = ""
    nome_site: str = ""
    cidade: str = ""
    uf: str = ""
    modelo_bandeira: str = ""
    vencimento: Optional[str] = None  # Formato 'YYYY-MM-01'
    observacao: Optional[str] = None
    notificada: int = 0  # 0 ou 1
    ativo: int = 1
    created_at: Optional[str] = None


@dataclass
class Produto:
    id: Optional[int] = None
    nome: str = ""
    categoria: Optional[str] = None
    tipo: str = "SERVICO"  # 'SERVICO' ou 'PECA'
    unidade: str = "UN"    # 'SV' ou 'UN'
    capacidade: Optional[str] = None
    preco_padrao: float = 0.0
    ativo: int = 1
    created_at: Optional[str] = None


@dataclass
class PrecoCliente:
    id: Optional[int] = None
    cliente_id: int = 0
    produto_id: int = 0
    preco: float = 0.0
    created_at: Optional[str] = None


@dataclass
class Pedido:
    id: Optional[int] = None
    cliente_id: int = 0
    loja_id: int = 0
    numero_pedido: str = ""
    data_emissao: str = ""   # 'YYYY-MM-DD'
    data_execucao: Optional[str] = None  # 'YYYY-MM-DD'
    status: str = "ABERTO"  # 'ABERTO', 'EXECUTADO', 'FATURADO', 'PAGO'
    observacoes: Optional[str] = None
    prazo_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    prazo_entrega: Optional[str] = None
    texto_impostos: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ItemPedido:
    id: Optional[int] = None
    pedido_id: int = 0
    produto_id: Optional[int] = None  # None se avulso
    secao: str = "SERVICO"            # 'SERVICO' ou 'PECA'
    descricao: str = ""
    quantidade: float = 0.0
    unidade: str = "UN"               # 'SV' ou 'UN'
    preco_unitario: float = 0.0
    valor_total: float = 0.0
    ordem: int = 0


@dataclass
class Ajuste:
    id: Optional[int] = None
    pedido_id: int = 0
    numero_ajuste: str = ""
    data_emissao: str = ""
    data_execucao: Optional[str] = None  # 'YYYY-MM-DD' (mês define o faturamento)
    modo_geracao: str = "DIFERENCA"  # 'DIFERENCA' ou 'INCREMENTADO'
    status: str = "PENDENTE"        # 'PENDENTE' ou 'FATURADO'
    faturamento_id: Optional[int] = None
    valor_cobrado: float = 0.0
    observacoes: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ItemAjuste:
    id: Optional[int] = None
    ajuste_id: int = 0
    produto_id: Optional[int] = None
    secao: str = "SERVICO"
    descricao: str = ""
    quantidade: float = 0.0
    unidade: str = "UN"
    preco_unitario: float = 0.0
    valor_total: float = 0.0
    ordem: int = 0


@dataclass
class Faturamento:
    id: Optional[int] = None
    cliente_id: int = 0
    mes_referencia: int = 1
    ano_referencia: int = 2026
    data_fechamento: Optional[str] = None
    total_geral: float = 0.0
    status: str = "ABERTO"  # 'ABERTO' ou 'FECHADO'
    observacoes: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class FaturamentoItem:
    id: Optional[int] = None
    faturamento_id: int = 0
    pedido_id: Optional[int] = None
    ajuste_id: Optional[int] = None
    valor_cobrado: float = 0.0
