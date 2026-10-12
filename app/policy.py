"""Política explícita de ações por adaptador.

Reflete os termos públicos do IO conferidos em 2026-10-11. Permissão de regra
não equivale a habilitação técnica: ações reais continuam desativadas até
validação autenticada de seletor, pré-condição e verificação.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionPolicy:
    name: str
    game: str
    dry_run_allowed: bool
    real_enabled: bool
    requires_confirmation: bool
    reason: str


IO_POLICIES = {
    "select_hunt": ActionPolicy("select_hunt", "io", True, False, False,
                                 "Aguardando validação do controle e verificação de resultado."),
    "review_inventory": ActionPolicy("review_inventory", "io", True, False, False,
                                      "Leitura de interface ainda não foi validada em conta."),
    "market_list": ActionPolicy("market_list", "io", True, False, True,
                                "Cria operação financeira; confirmação humana é obrigatória."),
    "market_cancel": ActionPolicy("market_cancel", "io", True, False, True,
                                  "Altera anúncio; confirmação humana é obrigatória."),
    "withdraw": ActionPolicy("withdraw", "io", False, False, True,
                             "Saque nunca é automatizado."),
    "purchase": ActionPolicy("purchase", "io", False, False, True,
                             "Compra com dinheiro real nunca é automatizada."),
}


def action_policy(game: str, action: str) -> ActionPolicy | None:
    if game == "io":
        return IO_POLICIES.get(action)
    return None
