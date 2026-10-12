"""Planeja ações IO com base em dados reais e validações econômicas externas.

Este módulo só produz propostas e JAMAIS invoca o jogo. A execução fica
a cargo do io_action_engine, inicialmente dry-run ou simulação local.

Não substituir o motor econômico que o usuário já construiu noutra branch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adaptive_strategy import Account, Measurement, rank_hunts
from app.io_action_engine import ActionRequest, ObservedIO


@dataclass(frozen=True)
class Proposed:
    status: str
    reason: str
    action: ActionRequest | None = None
    evidence: dict[str, Any] | None = None

    def as_dict(self) -> dict:
        result = {"status": self.status, "reason": self.reason}
        if self.action:
            result["action"] = {
                "request_id": self.action.request_id,
                "kind": self.action.kind,
                "target_id": self.action.target_id,
                "quantity": self.action.quantity,
                "price_gems": self.action.price_gems,
                "mode": "dry_run"
            }
        if self.evidence:
            result["evidence"] = self.evidence
        return result


@dataclass(frozen=True)
class MarketAssessment:
    """Apenas valores validados pelo motor econômico, nunca só preços anunciados."""
    asset_id: str
    comparable_completed_sales: int
    price_gems: int
    positive_expected_net: bool
    trade_allowed: bool
    market_evidence_verified: bool

    def __post_init__(self):
        if not isinstance(self.asset_id, str) or not 1 <= len(self.asset_id) <= 64:
            raise ValueError("Ativo inválido")
        if type(self.comparable_completed_sales) is not int or self.comparable_completed_sales < 0:
            raise ValueError("Vendas comparáveis inválidas")
        if type(self.price_gems) is not int or not 0 <= self.price_gems <= 1_000_000:
            raise ValueError("Preço inválido")
        if any(type(flag) is not bool for flag in (
                self.positive_expected_net, self.trade_allowed,
                self.market_evidence_verified)):
            raise ValueError("Indicador de avaliação inválido")


@dataclass(frozen=True)
class EvolutionAssessment:
    pokemon_id: str
    eligible: bool
    evolution_target: str
    costs_known: bool
    irreversible: bool = True

    def __post_init__(self):
        if not isinstance(self.pokemon_id, str) or not self.pokemon_id or len(self.pokemon_id)>64:
            raise ValueError("Identificador Pokémon inválido")
        if not isinstance(self.evolution_target,str) or len(self.evolution_target)>64:
            raise ValueError("Evolução inválida")
        if any(type(flag) is not bool for flag in (
                self.eligible, self.costs_known, self.irreversible)):
            raise ValueError("Avaliação inválida")


def _check_io(account: Account, state: ObservedIO):
    if account.game != "io" or state.game != "io":
        raise PermissionError("Operação de conta World proibida; apenas IO")
    if account.key != state.account_key:
        raise PermissionError("Estado pertence a outra conta ou perfil")


def _make(account: Account, kind: str, request_id: str,
          target: str = "", quantity: int = 1, price: int = 0) -> ActionRequest:
    return ActionRequest(request_id, "io", account.profile_id, account.account_id,
                         kind, target, quantity, price)


def plan_farm(account: Account, state: ObservedIO, measurements: list[Measurement],
              request_id: str, goal: str = "resources") -> Proposed:
    """Seleciona melhor hunt comparável e decide iniciar, parar ou aguardar.

    Nunca presume que uma hunt desbloqueada tenha liquidez em Gems.
    Objetivo financeiro requer integração de vendas reais (market_data_required).
    """
    _check_io(account,state)
    if account.active_pokemon_id is None:
        return Proposed("need_data", "Selecione o Pokémon ativo; não assumir espécie")
    selected = next((p for p in account.roster if p.id == account.active_pokemon_id), None)
    if selected is None:
        return Proposed("need_data", "Pokémon ativo não cadastrado")
    if selected.max_hp is not None and selected.hp is not None:
        if selected.hp / selected.max_hp < 0.25:
            if state.farming:
                return Proposed("proposed", "HP abaixo de 25%; propor parada segura",
                                _make(account, "stop_farm", request_id))
            return Proposed("blocked", "HP crítico: verifique recuperação antes de farmar")
    ranking = rank_hunts(account, measurements, goal)
    if ranking["status"] != "ranked":
        return Proposed("need_data", ranking.get("reason","Faltam medições reais"),
                        evidence={"status":ranking["status"]})
    best = ranking["ranked"][0]
    selected_id = best["hunt_id"]
    if state.hunt_id != selected_id:
        if state.farming:
            return Proposed("proposed", "Parar farm antes de mudar de hunt",
                            _make(account,"stop_farm",request_id),
                            evidence={"recommended_hunt_id":selected_id, "ranking":ranking["ranked"]})
        return Proposed("proposed", "Hunt de melhor desempenho medido para a meta escolhida",
                        _make(account, "select_hunt", request_id,selected_id),
                        evidence={"recommended_hunt_id":selected_id,"ranking":ranking["ranked"]})
    if state.farming is False:
        return Proposed("proposed", "Mapa selecionado; iniciar farm por função autorizada",
                        _make(account,"start_farm",request_id), evidence={"ranking":ranking["ranked"]})
    if state.farming is None:
        return Proposed("need_data", "Estado de farm ainda desconhecido")
    return Proposed("monitor", "Farm ativo na melhor hunt observada; continue medindo",
                    evidence={"ranking":ranking["ranked"]})


def plan_inventory(account: Account, state: ObservedIO,
                   request_id: str) -> Proposed:
    _check_io(account,state)
    return Proposed("proposed","Inspecionar inventário antes de vender, descartar ou comprar",
                    _make(account,"inspect_inventory",request_id))


def plan_pokemon(account: Account, state: ObservedIO,
                 request_id: str) -> Proposed:
    _check_io(account,state)
    return Proposed("proposed","Inspecionar Pokémon elegíveis e seus requisitos reais",
                    _make(account,"inspect_pokemon",request_id))


def plan_evolution(account: Account, state: ObservedIO, request_id: str,
                   assessment: EvolutionAssessment | None,
                   *, propose_commit: bool = False) -> Proposed:
    _check_io(account,state)
    if assessment is None:
        return Proposed("need_data","Inspecionar possibilidades de evolução na interface real")
    if assessment.pokemon_id not in {p.id for p in account.roster}:
        return Proposed("blocked","Pokémon não pertence à conta")
    if not assessment.eligible or not assessment.costs_known or not assessment.evolution_target:
        return Proposed("need_data","Evolução não confirmada ou custos desconhecidos")
    if not propose_commit:
        return Proposed("proposed","Avaliar custo/benefício e consequências antes de evoluir",
                        _make(account,"evaluate_evolution",request_id),
                        evidence={"pokemon_id":assessment.pokemon_id,
                                  "evolves_to":assessment.evolution_target})
    return Proposed("needs_human_approval",
                    "Evolução é potencialmente irreversível: revisão e aprovação específica obrigatórias",
                    _make(account,"evolve_pokemon",request_id,assessment.pokemon_id),
                    evidence={"evolves_to":assessment.evolution_target})


def plan_market(account: Account, state: ObservedIO, request_id: str,
                assessment: MarketAssessment, operation: str,
                quantity: int = 1) -> Proposed:
    """Compra/anúncio só serão propostos após vendas CONCLUÍDAS comparáveis.

    Não cria autorização financeira. Operações de compra e publicação
    requerem limites e confirmação no executor.
    """
    _check_io(account,state)
    if operation not in {"prepare_listing","publish_listing","buy_item","buy_pokemon"}:
        raise ValueError("Operação comercial desconhecida")
    if assessment.comparable_completed_sales < 3 or not assessment.market_evidence_verified:
        return Proposed("need_data","Exigir pelo menos 3 vendas concluídas comparáveis e verificadas")
    if not assessment.trade_allowed:
        return Proposed("blocked","Ativo não pode ser negociado pela regra atual")
    if not assessment.positive_expected_net:
        return Proposed("blocked","Benefício econômico esperado líquido não demonstrado")
    if assessment.price_gems < 1:
        return Proposed("need_data","Preço de mercado não validado")
    if operation in {"prepare_listing","publish_listing"} and (
            state.inventory.get(assessment.asset_id,0) < quantity):
        return Proposed("blocked","Ativo não disponível em quantidade suficiente")
    kind = operation
    proposed = _make(account,kind,request_id,assessment.asset_id,quantity,
                     assessment.price_gems if kind in {"publish_listing","buy_item","buy_pokemon"} else 0)
    return Proposed("needs_human_approval" if kind != "prepare_listing" else "proposed",
                    "Operação sujeita a limite e aprovação humana; NÃO é venda concluída",
                    proposed,
                    evidence={"completed_sales":assessment.comparable_completed_sales,
                              "price_gems":assessment.price_gems,
                              "expected_net_positive":True})


def plan_next(account: Account, state: ObservedIO, measurements: list[Measurement],
              request_id: str, goal: str = "resources") -> Proposed:
    """Orquestrador de farming. Outros subfluxos são chamados sob solicitação."""
    return plan_farm(account,state,measurements,request_id,goal)
