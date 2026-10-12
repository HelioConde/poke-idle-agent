"""Fonte LOCAL, independente do adaptador, para ações reais do Poke Idle IO.

Deny-by-default: NÃO há controles reais auditados e autorizados nesta versão.
O adaptador/LLM/telemetria não podem adicionar controles a esta lista por API.

Para liberar uma ação no futuro, somente após validação REAL na interface
autorizada, revisão humana, registro de evidência e commit de código revisado.
Nenhuma aprovação desta lista autoriza transações, login, CAPTCHAs, depósitos,
saques, nem invalida o bloqueio específico do comando Desistir.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping


@dataclass(frozen=True)
class LocalControlEvidence:
    """Prova auditável para um controle específico do IO, incorporada no código.

    Um nome de ação declarado pelo adaptador nunca basta para aprovar live.
    """
    action: str
    route: str
    control_id: str
    validation_commit: str
    evidence_report: str
    review_ticket: str
    verified_checks: tuple[str, ...]

    def is_complete_for(self, action: str) -> bool:
        if self.action != action or self.route != "/app":
            return False
        if not self.control_id or not self.evidence_report or not self.review_ticket:
            return False
        if len(self.validation_commit) != 40:
            return False
        if any(char not in "0123456789abcdef" for char in self.validation_commit.lower()):
            return False
        required = {"read_before", "expected_control", "read_after",
                    "risk_review", "human_approval", "emergency_stop"}
        return required.issubset(self.verified_checks)


# NÃO acrescentar controles com base em testes simulados, vídeos de terceiros,
# resposta da IA, atributo verified_actions, flags de ambiente ou configurações
# locais alteráveis. Exige evidência autenticada + revisão humana explícita.
#
# O primeiro teste REAL de stop_farm/Desistir teve derrota e perda de XP.
# Nenhum controle passou o ciclo de verificação exigido.
#
# MappingProxyType impede edição no processo através da API do registro.
# Não é uma sandbox contra edição maliciosa do próprio Python-fonte.
LOCAL_IO_LIVE_CONTROLS: Final[Mapping[str, LocalControlEvidence]] = MappingProxyType({})


def locally_verified_control(action: str) -> LocalControlEvidence | None:
    """Exige comprovação local e estática, separada do adaptador.

    A prova NÃO substitui aprovação humana individual nem os demais gates.
    """
    if not isinstance(action, str):
        return None
    proof = LOCAL_IO_LIVE_CONTROLS.get(action)
    if proof is None or not proof.is_complete_for(action):
        return None
    return proof
