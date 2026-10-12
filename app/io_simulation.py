"""Campanha local determinística para validar o ciclo operacional do IO.

Não abre navegador nem usa endpoints do jogo. Reutiliza o planejador e o
executor de produção com ``FakeIOAdapter`` e um relógio virtual.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from app.adaptive_strategy import Account, Measurement
from app.io_action_engine import ActionRequest, Engine, FakeIOAdapter, Policy
from app.io_operation_planner import plan_farm, plan_inventory
from app.memory import MemoryStore


def _account(profile_id: str = "sim-profile", account_id: str = "sim-account") -> Account:
    return Account.parse({
        "game": "io", "profile_id": profile_id, "account_id": account_id,
        "trainer_level": 20, "active_pokemon_id": "starter",
        "roster": [{"id": "starter", "species": "Espécie simulada", "level": 20,
                    "hp": 100, "max_hp": 100}],
        "hunts": [{"id": "starter", "label": "Inicial", "unlocked": True},
                  {"id": "forest", "label": "Floresta", "unlocked": True},
                  {"id": "lake", "label": "Lago", "unlocked": True}],
    })


def _measurements(account: Account) -> list[Measurement]:
    rows = [("forest", 300, 250), ("lake", 800, 700)]
    return [Measurement.parse({
        "game": "io", "profile_id": account.profile_id, "account_id": account.account_id,
        "pokemon_id": "starter", "hunt_id": hunt, "minutes": 60,
        "xp_gained": xp, "resources_gained": resources, "resources_spent": 0,
        "defeats": 0, "source": "manual",
    }) for hunt, xp, resources in rows]


def _state_payload(state) -> dict:
    """Persist only normalized, non-sensitive state used by the simulation."""
    return {"hunt_id": state.hunt_id, "farming": state.farming,
            "team_defeated": state.team_defeated, "scene": state.scene,
            "inventory": dict(state.inventory)}


def run_campaign(cycles: int = 100, state_path: Path | None = None) -> dict:
    """Run a virtual-time observe→plan→simulate→verify→learn campaign.

    Controlled inconsistencies intentionally produce blocked decisions. They do
    not get retried as gameplay actions. ``state_path`` is only executor
    idempotency state; callers normally use a temporary directory.
    """
    if type(cycles) is not int or not 1 <= cycles <= 1000:
        raise ValueError("cycles deve estar entre 1 e 1000")
    account = _account()
    adapter = FakeIOAdapter(account.profile_id, account.account_id)
    engine = Engine(Policy(max_actions=cycles + 10), state_path=state_path)
    proposed = simulated = blocked = monitored = 0
    fault_cycles = {20: "farm_unknown", 40: "team_defeated", 60: "session_conflict"}

    with TemporaryDirectory() as directory:
        memory = MemoryStore(Path(directory) / "simulation.sqlite3")
        for cycle in range(cycles):
            original = adapter.state
            fault = fault_cycles.get(cycle)
            if fault == "farm_unknown":
                adapter.state = replace(original, farming=None)
            elif fault == "team_defeated":
                adapter.state = replace(original, team_defeated=True, scene="pokemon_center")
            elif fault == "session_conflict":
                adapter.state = replace(original, session_farming=not bool(original.farming))

            state = adapter.observe()
            decision = plan_farm(account, state, _measurements(account), f"farm-{cycle}")
            if decision.status == "proposed" and decision.action:
                proposed += 1
                result = engine.execute(decision.action, adapter, mode="simulation")
                if result["status"] == "simulated":
                    simulated += 1
                else:
                    blocked += 1
            elif decision.status == "monitor":
                monitored += 1
            else:
                blocked += 1

            # A safe inspection exercises the same executor and postcondition
            # path repeatedly without changing account/gameplay state.
            if cycle % 10 == 5 and not fault:
                inspection = plan_inventory(account, adapter.observe(), f"inventory-{cycle}")
                proposed += 1
                result = engine.execute(inspection.action, adapter, mode="simulation")
                if result["status"] == "simulated":
                    simulated += 1
                else:
                    blocked += 1

            latest = adapter.observe()
            memory.record_observation(
                profile_id=account.profile_id, game="io", session_id="campaign",
                state=_state_payload(latest), decision=decision.as_dict(),
                observed_at=1_700_000_000 + cycle,
            )
            adapter.state = original if fault else adapter.state

        history = memory.history(account.profile_id, "campaign", limit=cycles)
    return {
        "environment": "local_simulation_only", "cycles": cycles,
        "proposed": proposed, "simulated": simulated, "blocked": blocked,
        "monitored": monitored, "history_records": len(history),
        "final_farming": adapter.observe().farming,
        "faults": sorted(fault_cycles.values()),
        "engine_emergency": engine.emergency,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Campanha IO simulada e isolada")
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run_campaign(args.cycles), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
