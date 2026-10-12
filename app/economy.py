"""Cálculos locais para oportunidades do Community Market.

Valores em Gems só representam receita potencial. USDT é contabilizado apenas
após saque manualmente confirmado; este módulo não abre, compra ou altera
anúncios.
"""
from __future__ import annotations

from dataclasses import dataclass

ITEM_FEE = 0.15
WITHDRAWAL_RATE_USD = 0.007
MIN_WITHDRAWAL_GEMS = 1_000


def pokemon_fee(gross_gems: float) -> float:
    """Taxa progressiva: 13%/10%/7,5% por faixa de valor."""
    if gross_gems < 0:
        raise ValueError("Preço não pode ser negativo")
    remaining = gross_gems
    fee = min(remaining, 500) * 0.13
    remaining = max(0.0, remaining - 500)
    fee += min(remaining, 4_500) * 0.10
    remaining = max(0.0, remaining - 4_500)
    fee += remaining * 0.075
    return round(fee, 4)


def net_gems(gross_gems: float, category: str, status: str) -> float | None:
    """Retorna Gems líquidas apenas para venda concluída no Market."""
    if gross_gems < 0 or category not in ("item", "pokemon"):
        raise ValueError("Venda inválida")
    if status != "completed":
        return None
    fee = gross_gems * ITEM_FEE if category == "item" else pokemon_fee(gross_gems)
    return round(gross_gems - fee, 4)


def confirmed_withdrawal_usd(net_balance_gems: float, confirmed: bool) -> float | None:
    """Nunca trata saldo de Gems ou saque pendente como receita real."""
    if net_balance_gems < 0:
        raise ValueError("Saldo inválido")
    if not confirmed:
        return None
    if net_balance_gems < MIN_WITHDRAWAL_GEMS:
        raise ValueError("Saldo abaixo do saque mínimo")
    return round(net_balance_gems * WITHDRAWAL_RATE_USD, 2)


def first_withdrawal_goal(completed_sale_net_gems: list[float],
                          withdrawal_confirmed: bool = False) -> dict:
    """Progresso da meta experimental sem converter saldo em receita fictícia."""
    if any(not isinstance(value, (int, float)) or value < 0
           for value in completed_sale_net_gems):
        raise ValueError("Vendas concluídas inválidas")
    net_gems = round(sum(completed_sale_net_gems), 4)
    eligible = net_gems >= MIN_WITHDRAWAL_GEMS
    if withdrawal_confirmed and not eligible:
        raise ValueError("Não há Gems líquidas suficientes para o saque mínimo")
    return {
        "goal_net_gems": MIN_WITHDRAWAL_GEMS,
        "completed_sale_net_gems": net_gems,
        "remaining_net_gems": round(max(0.0, MIN_WITHDRAWAL_GEMS - net_gems), 4),
        "withdrawal_eligible": eligible,
        "confirmed_usdt": (confirmed_withdrawal_usd(MIN_WITHDRAWAL_GEMS, True)
                           if withdrawal_confirmed else None),
        "status": ("confirmed" if withdrawal_confirmed else
                   "eligible_for_manual_withdrawal" if eligible else "in_progress"),
    }


@dataclass(frozen=True)
class Opportunity:
    name: str
    xp_per_hour: float
    expected_net_gems_per_hour: float
    sale_probability: float
    confidence: float
    comparable_completed_sales: int


def recommend(opportunities: list[Opportunity], minimum_sales: int = 3) -> dict:
    """Escolhe valor líquido realizável, não XP; sem dados, pede medição."""
    if minimum_sales < 1:
        raise ValueError("Amostra mínima inválida")
    eligible = []
    for item in opportunities:
        if (item.xp_per_hour < 0 or item.expected_net_gems_per_hour < 0 or
                not 0 <= item.sale_probability <= 1 or
                not 0 <= item.confidence <= 1 or item.comparable_completed_sales < 0):
            raise ValueError("Oportunidade inválida")
        if item.comparable_completed_sales >= minimum_sales:
            score = item.expected_net_gems_per_hour * item.sale_probability * item.confidence
            eligible.append((score, item))
    if not eligible:
        return {"action": "measure_more", "reason": "Sem vendas concluídas comparáveis suficientes."}
    score, best = max(eligible, key=lambda item: item[0])
    return {"action": "prioritize", "name": best.name,
            "provisional_net_gems_per_hour": round(score, 4),
            "reason": "Ranking por Gems líquidas esperadas, liquidez e confiança; não é USDT realizado."}
