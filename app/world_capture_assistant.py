"""Assistente de captura World para contas GRATUITAS (dados manuais/offline).

IMPORTANTE:
- Nunca interage com o jogo, extensão, navegador, API ou Tampermonkey.
- Auto-Catch oficial é somente VIP. Scripts externos e auto-clickers sem
  aprovação da equipe violam as regras públicas do Poke Idle World.
- Conta de outro jogo nunca pode entrar aqui.
- Não incorpora código de PollitoScripts (repositório sem licença declarada).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_NORMAL = ("Poke Ball", "Great Ball", "Super Ball", "Ultra Ball")
DEFAULT_SHINY = ("Idle Ball", "Ultra Ball", "Super Ball", "Great Ball", "Poke Ball")
ACCOUNT_KEYS = {
    "profile_id", "account_id", "vip", "inventory", "shiny_reserves",
    "normal_priority", "shiny_priority", "encounter", "attempts"
}
ENCOUNTER_KEYS = {"species", "shiny", "confirmed"}
ATTEMPT_KEYS = {"species", "shiny", "ball", "captured", "source"}
MAX_ACCOUNTS = 4
MAX_ATTEMPTS = 500
MAX_STOCK = 1_000_000_000
MAX_FILE_SIZE = 1024 * 1024


def _alias(value, field, *, max_len=64):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= max_len:
        raise ValueError(f"{field}: apelido inválido")
    if any(ord(ch) < 32 for ch in value) or "@" in value:
        raise ValueError(f"{field}: não use e-mail ou caracteres de controle")
    return value.strip()


def _int(value, field):
    if type(value) is not int or not 0 <= value <= MAX_STOCK:
        raise ValueError(f"{field}: quantidade inteira não negativa obrigatória")
    return value


def _flags(value, field):
    if type(value) is not bool:
        raise ValueError(f"{field}: valor deve ser booleano")
    return value


def _mapping(value, field, *, max_items=30):
    if not isinstance(value, dict) or len(value) > max_items:
        raise ValueError(f"{field}: dicionário inválido")
    out = {}
    for ball, stock in value.items():
        name = _alias(ball, field, max_len=40)
        if name in out:
            raise ValueError(f"{field}: nome duplicado")
        out[name] = _int(stock, f"{field}/{name}")
    return out


def _priority(value, field, defaults):
    if value is None:
        return list(defaults)
    if not isinstance(value, list) or not 1 <= len(value) <= 30:
        raise ValueError(f"{field}: prioridades inválidas")
    result = [_alias(b, field, max_len=40) for b in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{field}: repetição de Pokébola")
    return result


def _encounter(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != ENCOUNTER_KEYS:
        raise ValueError("encounter: campos ausentes ou desconhecidos")
    return {"species": _alias(raw["species"], "Espécie"),
            "shiny": _flags(raw["shiny"], "shiny"),
            "confirmed": _flags(raw["confirmed"], "confirmed")}


def _attempts(value):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ATTEMPTS:
        raise ValueError("attempts: histórico inválido")
    out = []
    for item in value:
        if not isinstance(item, dict) or set(item) != ATTEMPT_KEYS:
            raise ValueError("attempts: campos ausentes/desconhecidos")
        if item["source"] not in ("manual", "demo"):
            raise ValueError("attempts: somente fonte manual/demo")
        out.append({"species": _alias(item["species"], "Espécie"),
                    "ball": _alias(item["ball"], "Pokébola", max_len=40),
                    "shiny": _flags(item["shiny"], "shiny"),
                    "captured": _flags(item["captured"], "captured"),
                    "source": item["source"]})
    return out


def analyze_account(account: dict, source: str = "manual"):
    """Gera UMA recomendação consultiva para UMA conta independente."""
    if not isinstance(account, dict) or not {"profile_id", "account_id", "vip", "inventory"}.issubset(account):
        raise ValueError("Conta sem campos obrigatórios")
    if not set(account).issubset(ACCOUNT_KEYS):
        raise ValueError("Campos desconhecidos (credenciais proibidas)")
    profile = _alias(account["profile_id"], "profile_id")
    alias = _alias(account["account_id"], "account_id")
    vip = _flags(account["vip"], "vip")
    inventory = _mapping(account["inventory"], "inventory")
    reserves = _mapping(account.get("shiny_reserves", {}), "shiny_reserves")
    normal = _priority(account.get("normal_priority"), "normal_priority", DEFAULT_NORMAL)
    shiny = _priority(account.get("shiny_priority"), "shiny_priority", DEFAULT_SHINY)
    encounter = _encounter(account.get("encounter"))
    attempts = _attempts(account.get("attempts"))
    if any(x["source"] != source for x in attempts):
        raise ValueError("Não misture tentativas demo e manual")
    total = len(attempts)
    wins = sum(1 for x in attempts if x["captured"])
    history = {"attempts": total, "captures": wins,
               "shiny_captures": sum(1 for x in attempts if x["captured"] and x["shiny"]),
               "success_rate": round(wins / total, 4) if total else None,
               "source": source}
    row = {"game": "world", "profile_id": profile, "account_id": alias,
           "vip_reported_manually": vip, "capture_execution": "disabled",
           "allowed_method": "official_auto_catch" if vip else "manual_throw",
           "source": source, "history": history,
           "recommended_ball": None, "alternatives": [],
           "status": "", "reason": "",
           "stock": inventory}
    if encounter is None or not encounter["confirmed"]:
        row.update(status="await_manual_encounter",
                   reason="Anote uma aparição confirmada; não há leitura automática do World.")
        return row
    row["encounter"] = {"species": encounter["species"], "shiny": encounter["shiny"]}
    if vip:
        row.update(status="use_official_feature",
                   reason="VIP informado manualmente. Configure Auto-Catch dentro do próprio jogo; nenhuma ação externa.")
        return row
    priorities = shiny if encounter["shiny"] else normal
    available = []
    for ball in priorities:
        stock = inventory.get(ball, 0)
        reserved = 0 if encounter["shiny"] else reserves.get(ball, 0)
        if stock > reserved:
            available.append(ball)
    if not available:
        row.update(status="no_ball",
                   reason="Sem Pokébolas disponíveis acima das reservas; não tentar captura.")
        return row
    row["recommended_ball"] = available[0]
    row["alternatives"] = available[1:]
    row["status"] = "manual_throw_recommended"
    row["reason"] = (
        f"Aparição {encounter['species']}: sugiro {available[0]} para "
        f"lançamento MANUAL no jogo. "
        + ("Prioridade shiny ativada." if encounter["shiny"] else
           "Reservas para shiny preservadas.")
    )
    return row


def analyze(payload):
    if not isinstance(payload, dict) or set(payload) != {"game", "source", "accounts"}:
        raise ValueError("Formato não suportado")
    if payload["game"] != "world":
        raise ValueError("Não misture Poke Idle IO com World")
    source = payload["source"]
    if source not in ("manual", "demo"):
        raise ValueError("Somente dados manuais ou demonstrativos")
    accounts = payload["accounts"]
    if not isinstance(accounts, list) or len(accounts) > MAX_ACCOUNTS:
        raise ValueError("Máximo de 4 contas World sem autorização especial da equipe")
    result = [analyze_account(item, source) for item in accounts]
    keys = [(item["profile_id"], item["account_id"]) for item in result]
    if len(set(keys)) != len(keys):
        raise ValueError("Conta duplicada no mesmo perfil")
    return {"game": "world", "mode": "offline_manual_only", "source": source,
            "is_demo": source == "demo", "accounts": result,
            "external_auto_catch_enabled": False, "usdt_revenue": None,
            "notes": [
                "Pokébolas não são lançadas por este programa.",
                "VIP é informado pelo usuário, não verificado na conta.",
                "Scripts externos e auto-clickers exigem autorização expressa da equipe do World.",
                "As estatísticas manuais não comprovam valor financeiro."
            ]}


def analyze_file(path: Path):
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("JSON maior que 1 MB")
    return analyze(json.loads(path.read_text(encoding="utf-8-sig")))


def main():
    parser = argparse.ArgumentParser(description="Poke Idle World: captura assistida manual e gratuita")
    parser.add_argument("--file", type=Path, required=True,
                        help="Arquivo manual em data/ ou demonstrativo em examples/")
    args = parser.parse_args()
    print(json.dumps(analyze_file(args.file), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
