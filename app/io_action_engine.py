"""Executor modular do Poke Idle IO: dry-run, simulação e integração real BLOQUEADA.

Sem seletores autenticados verificados, este módulo nunca opera uma conta real.
Nenhum socket/HTTP/browser é usado aqui. World não é executável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
import secrets
import time
from pathlib import Path
from typing import Protocol

SAFE_ACTIONS = frozenset({
    "select_hunt", "start_farm", "stop_farm",
    "inspect_inventory", "inspect_pokemon", "evaluate_evolution",
    "prepare_listing"
})
CONFIRM_ACTIONS = frozenset({
    "evolve_pokemon", "publish_listing", "buy_item", "buy_pokemon",
    "sell_npc", "cancel_listing"
})
ACTIONS = SAFE_ACTIONS | CONFIRM_ACTIONS
PRICE_ACTIONS = frozenset({"publish_listing", "buy_item", "buy_pokemon"})
ITEM_ACTIONS = frozenset({"prepare_listing", "publish_listing", "buy_item",
                           "buy_pokemon", "sell_npc", "cancel_listing"})
STATE_CHECKS = frozenset({"select_hunt", "start_farm", "stop_farm",
                           "evolve_pokemon", "publish_listing", "buy_item",
                           "buy_pokemon", "sell_npc", "cancel_listing"})


def _alias(value: str, label: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise ValueError(f"{label}: apelido inválido")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{label}: contém controle")
    return value


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    game: str
    profile_id: str
    account_id: str
    kind: str
    target_id: str = ""
    quantity: int = 1
    price_gems: int = 0

    def __post_init__(self):
        for name in ("request_id", "profile_id", "account_id"):
            _alias(getattr(self, name), name)
        if self.kind not in ACTIONS:
            raise ValueError("Ação não suportada")
        if self.game != "io":
            raise PermissionError("Somente Poke Idle IO: World bloqueado")
        if type(self.quantity) is not int or not 1 <= self.quantity <= 100:
            raise ValueError("Quantidade inválida")
        if type(self.price_gems) is not int or not 0 <= self.price_gems <= 1_000_000:
            raise ValueError("Preço inválido")
        if self.kind in {"select_hunt", "evolve_pokemon"} | ITEM_ACTIONS:
            _alias(self.target_id, "Alvo")
        if self.kind in PRICE_ACTIONS and self.price_gems < 1:
            raise ValueError("Preço em Gems deve ser positivo")
        if self.kind not in PRICE_ACTIONS and self.price_gems:
            raise ValueError("Preço inesperado nesta ação")

    @property
    def account_key(self) -> tuple[str, str, str]:
        return (self.game, self.profile_id, self.account_id)

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Policy:
    max_spend_gems: int = 0
    max_listing_gems: int = 0
    max_quantity: int = 10
    max_actions: int = 100

    def __post_init__(self):
        vals = (self.max_spend_gems, self.max_listing_gems,
                self.max_quantity, self.max_actions)
        if any(type(v) is not int or v < 0 for v in vals):
            raise ValueError("Limites inválidos")
        if self.max_quantity < 1 or self.max_actions < 1:
            raise ValueError("Limites de quantidade ou ações inválidos")

    def validate(self, request: ActionRequest):
        if request.quantity > self.max_quantity:
            raise PermissionError("Quantidade supera limite")
        if request.kind in {"buy_item", "buy_pokemon"}:
            if request.price_gems * request.quantity > self.max_spend_gems:
                raise PermissionError("Compra excede teto financeiro; padrão é 0 Gems")
        if request.kind == "publish_listing":
            if request.price_gems > self.max_listing_gems:
                raise PermissionError("Anúncio excede teto de preço; padrão é 0 Gems")


@dataclass(frozen=True)
class ObservedIO:
    """Somente estado já validado do adaptador; sem dados privados."""
    game: str
    profile_id: str
    account_id: str
    hunt_id: str | None = None
    farming: bool | None = None
    inventory: dict[str, int] = field(default_factory=dict)
    pokemon_species: dict[str, str] = field(default_factory=dict)
    listings: dict[str, int] = field(default_factory=dict)
    gems_balance: int | None = None

    @property
    def account_key(self):
        return self.game, self.profile_id, self.account_id


class IOAdapter(Protocol):
    """Um adaptador real FUTURO precisa comprovar cada ação e observação."""
    is_simulation: bool
    verified_actions: frozenset[str]

    def observe(self) -> ObservedIO: ...
    def perform(self, request: ActionRequest) -> None: ...


class ApprovalRegistry:
    """Tokens efêmeros, de uso único e vinculados ao pedido exato.

    issue() deve ser acionado EXCLUSIVAMENTE após confirmação explícita no
    painel ou console local; jamais por telemetria, site ou decisão da IA.
    """
    def __init__(self):
        self._pending: dict[str, str] = {}

    def issue(self, request: ActionRequest) -> str:
        token = secrets.token_urlsafe(32)
        self._pending[token] = request.fingerprint
        return token

    def consume(self, token: str | None, request: ActionRequest) -> bool:
        if not token or not isinstance(token, str):
            return False
        digest = self._pending.pop(token, None)
        return digest == request.fingerprint


class Engine:
    def __init__(self, policy: Policy | None = None, approvals: ApprovalRegistry | None = None,
                 state_path: Path | None = None):
        self.policy = policy or Policy()
        self.approvals = approvals or ApprovalRegistry()
        self.paused = False
        self.emergency = False
        self.history: list[dict] = []
        self.state_path = Path(state_path) if state_path else None
        self.completed = self._load_completed()

    def _load_completed(self) -> set[str]:
        """Carrega apenas ids concluídos; aprovações jamais são persistidas."""
        if self.state_path is None or not self.state_path.exists():
            return set()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Estado de idempotência inválido") from exc
        ids = payload.get("completed_request_ids") if isinstance(payload, dict) else None
        if not isinstance(ids, list) or len(ids) > self.policy.max_actions:
            raise ValueError("Estado de idempotência inválido")
        if any(not isinstance(value, str) or not 1 <= len(value) <= 64 for value in ids):
            raise ValueError("Estado de idempotência inválido")
        return set(ids)

    def _save_completed(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        payload = {"completed_request_ids": sorted(self.completed)}
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def pause(self):
        self.paused = True

    def resume(self):
        if self.emergency:
            raise PermissionError("Parada de emergência ativa")
        self.paused = False

    def emergency_stop(self):
        self.emergency = True
        self.paused = True

    def _log(self, req: ActionRequest, status: str, message: str):
        record = {"request_id": req.request_id, "kind": req.kind,
                  "game": req.game, "profile_id": req.profile_id,
                  "account_id": req.account_id, "status": status,
                  "message": message, "timestamp": round(time.time(), 3)}
        self.history.append(record)
        return record

    def execute(self, req: ActionRequest, adapter: IOAdapter | None = None,
                mode: str = "dry_run", approval_token: str | None = None) -> dict:
        if self.emergency or self.paused:
            return self._log(req, "blocked", "Pausado/parada de emergência")
        if req.request_id in self.completed:
            return self._log(req, "blocked", "Requisição já executada")
        if mode not in ("dry_run", "simulation", "live"):
            raise ValueError("Modo inválido")
        if len(self.completed) >= self.policy.max_actions:
            return self._log(req, "blocked", "Limite de ações atingido")
        try:
            self.policy.validate(req)
        except PermissionError as exc:
            return self._log(req, "blocked", str(exc))
        if mode == "dry_run":
            return self._log(req, "dry_run", "Proposta apenas; nenhuma ação foi executada")
        if adapter is None:
            return self._log(req, "blocked", "Falta adaptador")
        if mode == "simulation" and not adapter.is_simulation:
            return self._log(req, "blocked", "Simulação exige adaptador fictício")
        if mode == "live" and adapter.is_simulation:
            return self._log(req, "blocked", "Adaptador fictício não opera contas reais")
        if req.kind not in adapter.verified_actions:
            return self._log(req, "blocked", "Ação não validada no adaptador")
        try:
            before = adapter.observe()
            if before.account_key != req.account_key:
                return self._log(req, "blocked", "Conta/perfil observados não correspondem")
            precondition = check_precondition(req, before)
            if precondition:
                return self._log(req, "blocked", precondition)
            if mode == "live" and not self.approvals.consume(approval_token, req):
                return self._log(req, "blocked", "Confirmação humana única necessária")
            adapter.perform(req)
            after = adapter.observe()
            if after.account_key != req.account_key:
                self.emergency_stop()
                return self._log(req, "uncertain", "Conta mudou durante execução: parada de emergência")
            if not verify_transition(req, before, after):
                self.emergency_stop()
                return self._log(req, "uncertain", "Resultado não verificado: parada de emergência")
            self.completed.add(req.request_id)
            self._save_completed()
            status = "simulated" if mode == "simulation" else "verified"
            return self._log(req, status, "Estado pós-ação verificado")
        except Exception as exc:
            self.emergency_stop()
            return self._log(req, "uncertain", f"Falha de adaptação ({type(exc).__name__}); parada de emergência")



def check_precondition(req: ActionRequest, state: ObservedIO) -> str | None:
    """Nunca realizar ações em estado desconhecido ou incompatível."""
    if state.game != "io" or state.account_key != req.account_key:
        return "Conta incompatível"
    if req.kind == "select_hunt":
        if state.farming is not False:
            return "Pare o farm e confirme o estado antes de trocar a hunt"
        if state.hunt_id == req.target_id:
            return "Hunt já selecionada"
    if req.kind == "start_farm" and (state.farming is not False or not state.hunt_id):
        return "Hunt ou status de farm desconhecidos; não é seguro iniciar"
    if req.kind == "stop_farm" and state.farming is not True:
        return "Farm não está comprovadamente ativo"
    if req.kind == "evolve_pokemon" and req.target_id not in state.pokemon_species:
        return "Pokémon não encontrado no estado observado"
    if req.kind in {"publish_listing","sell_npc"}:
        if state.inventory.get(req.target_id,0) < req.quantity:
            return "Estoque insuficiente ou desconhecido"
    if req.kind == "cancel_listing" and state.listings.get(req.target_id,0) < req.quantity:
        return "Anúncio não encontrado"
    if req.kind in {"buy_item","buy_pokemon"}:
        total = req.price_gems * req.quantity
        if state.gems_balance is None or state.gems_balance < total:
            return "Gems insuficientes ou saldo desconhecido"
    return None


def verify_transition(req: ActionRequest, before: ObservedIO, after: ObservedIO) -> bool:
    """Verificação pós-condição, nunca supõe sucesso por ausência de erro."""
    if before.account_key != req.account_key or after.account_key != req.account_key:
        return False
    if req.kind == "select_hunt":
        return after.hunt_id == req.target_id
    if req.kind == "start_farm":
        return before.farming is False and after.farming is True
    if req.kind == "stop_farm":
        return before.farming is True and after.farming is False
    if req.kind == "evolve_pokemon":
        return (req.target_id in before.pokemon_species and
                req.target_id in after.pokemon_species and
                before.pokemon_species[req.target_id] != after.pokemon_species[req.target_id])
    if req.kind == "publish_listing":
        return (after.listings.get(req.target_id, 0) - before.listings.get(req.target_id, 0) == req.quantity and
                before.inventory.get(req.target_id, 0) - after.inventory.get(req.target_id, 0) == req.quantity)
    if req.kind in {"buy_item", "buy_pokemon"}:
        return (before.gems_balance is not None and after.gems_balance is not None and
                before.gems_balance - after.gems_balance == req.price_gems * req.quantity and
                after.inventory.get(req.target_id, 0) - before.inventory.get(req.target_id, 0) == req.quantity)
    if req.kind == "sell_npc":
        return before.inventory.get(req.target_id, 0) - after.inventory.get(req.target_id, 0) == req.quantity
    if req.kind == "cancel_listing":
        return (before.listings.get(req.target_id, 0) - after.listings.get(req.target_id, 0) == req.quantity and
                after.inventory.get(req.target_id, 0) - before.inventory.get(req.target_id, 0) == req.quantity)
    if req.kind in {"inspect_inventory", "inspect_pokemon", "evaluate_evolution",
                    "prepare_listing"}:
        return True  # Apenas avaliação: nenhuma transação.
    return False


class FakeIOAdapter:
    """Simulador local, nunca conectado ao jogo ou mercado."""
    is_simulation = True
    verified_actions = frozenset(ACTIONS)

    def __init__(self, profile_id="demo", account_id="demo"):
        self.state = ObservedIO("io", profile_id, account_id, hunt_id="starter",
                                farming=False, inventory={"stone": 3, "potion": 1},
                                pokemon_species={"poke1": "Charmander"},
                                listings={}, gems_balance=200)

    def observe(self) -> ObservedIO:
        s = self.state
        return ObservedIO(s.game,s.profile_id,s.account_id,s.hunt_id,s.farming,
                          dict(s.inventory),dict(s.pokemon_species),dict(s.listings),
                          s.gems_balance)

    def perform(self, req: ActionRequest):
        s = self.state
        inventory = dict(s.inventory)
        pokemon = dict(s.pokemon_species)
        listings = dict(s.listings)
        hunt = s.hunt_id
        farming = s.farming
        balance = s.gems_balance
        if req.kind == "select_hunt":
            hunt = req.target_id
        elif req.kind == "start_farm":
            farming = True
        elif req.kind == "stop_farm":
            farming = False
        elif req.kind == "evolve_pokemon":
            if req.target_id not in pokemon:
                raise ValueError("Pokémon não encontrado")
            pokemon[req.target_id] = "Evolução simulada"
        elif req.kind == "publish_listing":
            if inventory.get(req.target_id,0) < req.quantity:
                raise ValueError("Estoque insuficiente")
            inventory[req.target_id] -= req.quantity
            listings[req.target_id] = listings.get(req.target_id,0) + req.quantity
        elif req.kind in {"buy_item","buy_pokemon"}:
            total = req.price_gems * req.quantity
            if balance is None or balance < total:
                raise ValueError("Gems insuficientes")
            balance -= total
            inventory[req.target_id] = inventory.get(req.target_id,0)+req.quantity
        elif req.kind == "sell_npc":
            if inventory.get(req.target_id,0) < req.quantity:
                raise ValueError("Estoque insuficiente")
            inventory[req.target_id]-=req.quantity
        elif req.kind == "cancel_listing":
            if listings.get(req.target_id,0) < req.quantity:
                raise ValueError("Anúncio não encontrado")
            listings[req.target_id]-=req.quantity
            inventory[req.target_id]=inventory.get(req.target_id,0)+req.quantity
        self.state=ObservedIO(s.game,s.profile_id,s.account_id,hunt,farming,
                              inventory,pokemon,listings,balance)


def demo() -> list[dict]:
    engine = Engine(Policy(max_spend_gems=25, max_listing_gems=100))
    adapter = FakeIOAdapter()
    actions = [
        ActionRequest("01","io","demo","demo","select_hunt","forest"),
        ActionRequest("02","io","demo","demo","start_farm"),
        ActionRequest("03","io","demo","demo","inspect_inventory"),
        ActionRequest("04","io","demo","demo","publish_listing","stone",1,50),
        ActionRequest("05","io","demo","demo","buy_item","potion",2,10),
        ActionRequest("06","io","demo","demo","stop_farm"),
    ]
    return [engine.execute(req,adapter,mode="simulation") for req in actions]


if __name__ == "__main__":
    print(json.dumps(demo(),ensure_ascii=False,indent=2))
