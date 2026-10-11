"""Agente determinístico para um jogo SIMULADO; não acessa servidores reais."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict, dataclass

@dataclass
class State:
    turn: int = 0
    energy: int = 4
    inventory: int = 0
    coins: int = 0

class IdleSandbox:
    def __init__(self) -> None:
        self.state = State()

    def observe(self) -> State:
        return State(**asdict(self.state))

    def act(self, action: str) -> State:
        if action not in ("gather", "rest", "sell"):
            raise ValueError("Ação inválida")
        state = self.state
        if action == "gather" and state.energy > 0:
            state.energy -= 1
            state.inventory += 1
        elif action == "rest":
            state.energy = min(4, state.energy + 2)
        elif action == "sell" and state.inventory > 0:
            state.coins += 2 * state.inventory
            state.inventory = 0
        state.turn += 1
        return self.observe()

def choose_action(state: State) -> str:
    """Política ilustrativa; ainda não é um modelo treinado."""
    if state.inventory >= 3:
        return "sell"
    if state.energy == 0:
        return "rest"
    return "gather"

def run(steps: int = 15) -> dict:
    if not 1 <= steps <= 1000:
        raise ValueError("steps deve estar entre 1 e 1000")
    game = IdleSandbox()
    history = []
    for _ in range(steps):
        action = choose_action(game.observe())
        after = game.act(action)
        history.append({"turn": after.turn, "action": action,
                        "energy": after.energy, "inventory": after.inventory, "coins": after.coins})
    return {"environment": "local_sandbox_only", "summary": asdict(game.observe()), "events": history}

def main() -> None:
    parser = argparse.ArgumentParser(description="Ambiente de jogo simulado")
    parser.add_argument("--steps", type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(run(args.steps), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
