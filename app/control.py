"""Planejamento e execução segura, sem integração com jogos reais.

O executor só aceita o ambiente simulado. Poke Idle IO e World não possuem
ações liberadas aqui: qualquer pedido para eles é registrado como bloqueado,
sem enviar clique, tecla, requisição ou comando ao navegador.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from time import monotonic

from app.policy import action_policy


SIMULATED_ACTIONS = frozenset({"gather", "rest", "sell"})
GAME_ACTIONS = {"simulated": SIMULATED_ACTIONS, "io": frozenset(),
                "world": frozenset()}


@dataclass(frozen=True)
class ActionRequest:
    game: str
    action: str
    parameters: dict
    mode: str = "dry_run"


@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    executed: bool
    reason: str
    action: str
    mode: str


class RiskManager:
    """Limites locais, pausa e parada de emergência por processo."""

    def __init__(self, max_actions_per_minute: int = 12):
        if not 1 <= max_actions_per_minute <= 120:
            raise ValueError("Limite de ações inválido")
        self.max_actions_per_minute = max_actions_per_minute
        self.paused = False
        self.emergency_stopped = False
        self._attempts: list[float] = []

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        if not self.emergency_stopped:
            self.paused = False

    def emergency_stop(self) -> None:
        self.emergency_stopped = True
        self.paused = True

    def allow_attempt(self, now: float | None = None) -> tuple[bool, str]:
        if self.emergency_stopped:
            return False, "Parada de emergência ativa"
        if self.paused:
            return False, "Executor pausado"
        current = monotonic() if now is None else now
        self._attempts = [item for item in self._attempts if current - item < 60]
        if len(self._attempts) >= self.max_actions_per_minute:
            return False, "Limite de frequência atingido"
        self._attempts.append(current)
        return True, "Permitido"


class DryRunExecutor:
    """Valida pedidos e retorna planos; jamais acessa uma aba ou servidor."""

    def __init__(self, risk_manager: RiskManager | None = None):
        self.risk_manager = risk_manager or RiskManager()
        self.log: list[dict] = []

    def execute(self, request: ActionRequest, now: float | None = None) -> ExecutionResult:
        if request.game not in GAME_ACTIONS:
            raise ValueError("Adaptador de jogo inválido")
        policy = action_policy(request.game, request.action)
        if request.mode != "dry_run":
            result = ExecutionResult(False, False, "Modo real desabilitado", request.action,
                                     request.mode)
        elif not isinstance(request.parameters, dict):
            result = ExecutionResult(False, False, "Parâmetros inválidos", request.action,
                                     request.mode)
        elif (request.action not in GAME_ACTIONS[request.game] and
              (policy is None or not policy.dry_run_allowed)):
            result = ExecutionResult(False, False,
                                     "Ação não autorizada para este adaptador",
                                     request.action, request.mode)
        else:
            allowed, reason = self.risk_manager.allow_attempt(now)
            if request.game == "io" and policy and policy.requires_confirmation:
                reason = "Plano simulado; confirmação humana será exigida antes de qualquer execução"
            result = ExecutionResult(allowed, False,
                                     "Plano simulado aceito" if allowed else reason,
                                     request.action, request.mode)
        self.log.append(asdict(result))
        return result
