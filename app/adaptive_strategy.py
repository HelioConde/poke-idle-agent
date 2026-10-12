"""Motor universal de planejamento: múltiplos perfis, contas, Pokémon e estágios.

Este módulo NÃO interage com navegador, site, servidores do jogo nem executa
comandos. Os registros são fornecidos pelo usuário ou por adaptadores
autorizados. World = planejamento manual; IO = observação/dry-run.

O Charizard 110 é somente um caso de teste, não uma configuração fixa.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GAMES = frozenset({"world", "io"})
OBJECTIVES = frozenset({"balanced", "xp", "resources", "monetization"})
SOURCES = frozenset({"manual", "observed", "demo"})
MAX_RECORDS = 1000
MAX_FIELD_LENGTH = 64
MIN_HUNT_MINUTES = 30


def _fields(raw: Any, required: set[str], optional: set[str], label: str) -> dict:
    if not isinstance(raw, dict) or not required.issubset(raw) or not set(raw).issubset(required | optional):
        raise ValueError(f"{label}: campos ausentes ou não permitidos")
    return raw


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_FIELD_LENGTH:
        raise ValueError(f"{name}: identificador inválido")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name}: caracteres inválidos")
    return value.strip()


def _number(value: Any, name: str, maximum: float = 1e15, *, positive: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name}: número inválido")
    if not (0 < value <= maximum if positive else 0 <= value <= maximum):
        raise ValueError(f"{name}: fora do intervalo")
    return float(value)


def _level(value: Any, name: str) -> int:
    if type(value) is not int or not 1 <= value <= 100000:
        raise ValueError(f"{name}: nível inválido")
    return value


@dataclass(frozen=True)
class Pokemon:
    id: str
    species: str
    level: int
    hp: float | None = None
    max_hp: float | None = None

    @classmethod
    def parse(cls, raw: dict) -> "Pokemon":
        _fields(raw, {"id", "species", "level"}, {"hp", "max_hp"}, "Pokémon")
        hp = None if raw.get("hp") is None else _number(raw["hp"], "hp")
        maximum = None if raw.get("max_hp") is None else _number(raw["max_hp"], "max_hp", positive=True)
        if hp is not None and maximum is not None and hp > maximum:
            raise ValueError("HP maior que o máximo")
        return cls(_identifier(raw["id"], "Pokémon ID"), _identifier(raw["species"], "Espécie"),
                   _level(raw["level"], "Nível do Pokémon"), hp, maximum)


@dataclass(frozen=True)
class Hunt:
    id: str
    label: str
    unlocked: bool | None
    required_trainer_level: int | None = None

    @classmethod
    def parse(cls, raw: dict) -> "Hunt":
        _fields(raw, {"id", "label", "unlocked"}, {"required_trainer_level"}, "Hunt")
        if raw["unlocked"] is not None and type(raw["unlocked"]) is not bool:
            raise ValueError("Desbloqueio deve ser true/false/null")
        required = raw.get("required_trainer_level")
        if required is not None:
            required = _level(required, "Requisito de treinador")
        return cls(_identifier(raw["id"], "Hunt ID"), _identifier(raw["label"], "Nome da hunt"),
                   raw["unlocked"], required)


@dataclass(frozen=True)
class Account:
    profile_id: str
    account_id: str
    game: str
    trainer_level: int | None
    roster: tuple[Pokemon, ...]
    active_pokemon_id: str | None
    hunts: tuple[Hunt, ...]

    @property
    def key(self) -> tuple[str, str, str]:
        return self.game, self.profile_id, self.account_id

    @classmethod
    def parse(cls, raw: dict) -> "Account":
        _fields(raw, {"game", "profile_id", "account_id", "trainer_level",
                      "roster", "active_pokemon_id", "hunts"}, set(), "Conta")
        game = raw["game"]
        if game not in GAMES:
            raise ValueError("Jogo não suportado")
        level = raw["trainer_level"]
        if level is not None:
            level = _level(level, "Nível do treinador")
        if not isinstance(raw["roster"], list) or len(raw["roster"]) > 100:
            raise ValueError("Equipe inválida")
        roster = tuple(Pokemon.parse(p) for p in raw["roster"])
        if len({p.id for p in roster}) != len(roster):
            raise ValueError("Pokémon duplicados na mesma conta")
        active = raw["active_pokemon_id"]
        if active is not None and active not in {p.id for p in roster}:
            raise ValueError("Pokémon ativo não pertence à conta")
        if not isinstance(raw["hunts"], list) or len(raw["hunts"]) > 200:
            raise ValueError("Hunts inválidas")
        hunts = tuple(Hunt.parse(h) for h in raw["hunts"])
        if len({h.id for h in hunts}) != len(hunts):
            raise ValueError("Hunts duplicadas")
        return cls(_identifier(raw["profile_id"], "Perfil"),
                   _identifier(raw["account_id"], "Conta"),
                   game, level, roster, active, hunts)


@dataclass(frozen=True)
class Measurement:
    profile_id: str
    account_id: str
    game: str
    pokemon_id: str
    hunt_id: str
    minutes: float
    xp_gained: float
    resources_gained: float
    resources_spent: float
    defeats: int
    source: str

    @classmethod
    def parse(cls, raw: dict) -> "Measurement":
        _fields(raw, {"profile_id", "account_id", "game", "pokemon_id",
                      "hunt_id", "minutes", "xp_gained", "resources_gained",
                      "resources_spent", "defeats", "source"}, set(), "Medição")
        if raw["game"] not in GAMES or raw["source"] not in SOURCES:
            raise ValueError("Jogo/origem inválidos")
        defeats = raw["defeats"]
        if type(defeats) is not int or not 0 <= defeats <= 1000000:
            raise ValueError("Número de derrotas inválido")
        return cls(
            _identifier(raw["profile_id"], "Perfil"), _identifier(raw["account_id"], "Conta"),
            raw["game"], _identifier(raw["pokemon_id"], "Pokémon"),
            _identifier(raw["hunt_id"], "Hunt"),
            _number(raw["minutes"], "Minutos", 1440, positive=True),
            _number(raw["xp_gained"], "XP"),
            _number(raw["resources_gained"], "Recursos recebidos"),
            _number(raw["resources_spent"], "Recursos gastos"),
            defeats, raw["source"])


def rank_hunts(account: Account, measurements: list[Measurement],
               goal: str = "balanced") -> dict:
    """Compara APENAS dados da mesma conta e do mesmo Pokémon ativo.

    Não calcula receita real. Comparações exigem >=2 hunts, pelo menos 30
    minutos por hunt, fonte manual/observed e acesso confirmado.
    """
    if goal not in OBJECTIVES:
        raise ValueError("Objetivo inválido")
    if goal == "monetization":
        return {"status": "market_data_required", "ranked": [],
                "reason": "Sem vendas concluídas e liquidez não existe ranking de renda realizável"}
    unlocked = {h.id for h in account.hunts if h.unlocked is True}
    groups: dict[str, dict] = {}
    for sample in measurements:
        if (sample.game, sample.profile_id, sample.account_id) != account.key:
            continue
        if (sample.pokemon_id != account.active_pokemon_id or sample.hunt_id not in unlocked):
            continue
        if sample.source == "demo" or (account.game == "world" and sample.source != "manual"):
            continue
        g = groups.setdefault(sample.hunt_id, {"minutes": 0.0, "xp": 0.0,
                                               "net": 0.0, "defeats": 0, "samples": 0})
        g["minutes"] += sample.minutes
        g["xp"] += sample.xp_gained
        g["net"] += sample.resources_gained - sample.resources_spent
        g["defeats"] += sample.defeats
        g["samples"] += 1
    sufficient = {k: v for k, v in groups.items() if v["minutes"] >= MIN_HUNT_MINUTES}
    if len(sufficient) < 2:
        return {"status": "measure_more", "ranked": [],
                "reason": "Meça duas hunts desbloqueadas por 30 minutos cada com o mesmo Pokémon ativo",
                "eligible_hunts": sorted(unlocked)}
    ranked = []
    for hunt in account.hunts:
        if hunt.id not in sufficient:
            continue
        g = sufficient[hunt.id]
        hours = g["minutes"] / 60
        ranked.append({"hunt_id": hunt.id, "hunt": hunt.label,
                       "pokemon_id": account.active_pokemon_id,
                       "xp_per_hour": round(g["xp"] / hours, 2),
                       "net_resources_per_hour": round(g["net"] / hours, 2),
                       "defeats_per_hour": round(g["defeats"] / hours, 3),
                       "minutes": round(g["minutes"], 2), "samples": g["samples"]})
    best_xp = max(0.0, *(r["xp_per_hour"] for r in ranked))
    best_net = max(0.0, *(r["net_resources_per_hour"] for r in ranked))
    for row in ranked:
        xp = row["xp_per_hour"] / best_xp if best_xp else 0.0
        net = max(0.0, row["net_resources_per_hour"]) / best_net if best_net else 0.0
        base = xp if goal == "xp" else net if goal == "resources" else (xp + net) / 2
        row["score"] = round(base / (1 + row["defeats_per_hour"]), 4)
    ranked.sort(key=lambda x: (x["score"], x["minutes"], x["hunt_id"]), reverse=True)
    return {"status": "ranked", "ranked": ranked, "priority": goal,
            "note": "Recursos do jogo não são dinheiro recebido; nenhuma ação foi executada"}


def plan(account: Account, measurements: list[Measurement],
         objective: str = "balanced") -> dict:
    if objective not in OBJECTIVES:
        raise ValueError("Objetivo inválido")
    # Capacidade baseada no jogo, jamais no nível ou espécie.
    permissions = {
        "world": {"gameplay_execution": "forbidden_without_explicit_authorization",
                  "mode": "manual_advice", "cashout": "unverified"},
        "io": {"gameplay_execution": "dry_run_only",
               "mode": "dry_run", "cashout": "verify_manually"}
    }[account.game]
    base = {"profile_id": account.profile_id, "account_id": account.account_id,
            "game": account.game, "trainer_level": account.trainer_level,
            "pokemon_count": len(account.roster),
            "active_pokemon_id": account.active_pokemon_id,
            "capabilities": permissions, "objective": objective}
    def result(stage: str, action: str, why: str, **extra) -> dict:
        return {**base, "stage": stage, "action": action, "reason": why, **extra}

    if not account.roster:
        return result("onboarding", "inspect_starter",
                      "Conta sem Pokémon cadastrado; registrar a equipe inicial antes de planejar")
    if account.active_pokemon_id is None:
        return result("team_setup", "choose_active",
                      "Selecione Pokémon ativo; não assumir que o de maior nível é melhor")
    active = next(p for p in account.roster if p.id == account.active_pokemon_id)
    base["active_pokemon"] = {"species": active.species, "level": active.level}
    if active.max_hp is not None and active.hp is not None:
        if active.hp / active.max_hp < 0.25:
            return result("survival", "review_recovery",
                          "HP abaixo de 25%; verificar opções oficiais de recuperação")
    if account.trainer_level is None:
        return result("discovery", "record_trainer_level",
                      "Nível do treinador desconhecido; não presumir hunts desbloqueadas")
    if account.game == "world" and objective == "monetization":
        return result("unsupported", "review_goal",
                      "World não possui saque oficial comprovado; não converter gold ou diamantes em USDT")
    unlocked = [h for h in account.hunts if h.unlocked is True]
    if not unlocked:
        locked = sorted((h.required_trainer_level for h in account.hunts
                         if h.unlocked is False and h.required_trainer_level
                         and h.required_trainer_level > account.trainer_level))
        return result("unlock", "inspect_hunt_access",
                      "Nenhuma hunt confirmada como acessível; verificar desbloqueios do jogo",
                      next_declared_trainer_milestone=locked[0] if locked else None)
    ranking = rank_hunts(account, measurements, objective)
    if ranking["status"] == "market_data_required":
        return result("market_research", "measure_sales",
                      "Objetivo financeiro exige vendas concluídas e dados de liquidez, não XP",
                      evaluation=ranking)
    if ranking["status"] == "measure_more":
        return result("measurement", "measure_hunts",
                      ranking["reason"], evaluation=ranking)
    return result("optimization", "review_hunt",
                  "Comparação realizada para a conta e Pokémon ativos; validar sobrevivência e custos",
                  recommended_hunt_id=ranking["ranked"][0]["hunt_id"],
                  evaluation=ranking)


def plan_many(accounts: list[Account], measurements: list[Measurement],
              objective: str = "balanced") -> list[dict]:
    if len(accounts) > MAX_RECORDS or len(measurements) > MAX_RECORDS:
        raise ValueError("Registros excedem o limite")
    keys = [a.key for a in accounts]
    if len(set(keys)) != len(keys):
        raise ValueError("Conta duplicada no mesmo jogo/perfil")
    return [plan(account, measurements, objective) for account in accounts]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Planejador universal offline: qualquer conta ou Pokémon")
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--measurements", type=Path)
    parser.add_argument("--objective", choices=sorted(OBJECTIVES), default="balanced")
    args = parser.parse_args()
    accounts_data = json.loads(args.accounts.read_text(encoding="utf-8-sig"))
    measurements_data = (json.loads(args.measurements.read_text(encoding="utf-8-sig"))
                         if args.measurements else [])
    if not isinstance(accounts_data, list) or not isinstance(measurements_data, list):
        parser.error("Arquivos precisam conter listas JSON")
    accounts = [Account.parse(a) for a in accounts_data]
    samples = [Measurement.parse(m) for m in measurements_data]
    print(json.dumps(plan_many(accounts, samples, args.objective),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
