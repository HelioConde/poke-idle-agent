"""Painel offline inspirado no PokeGrid: 1..N contas e Pokémon, SEM acesso ao World.

Este módulo analisa somente JSON preenchido manualmente ou demonstrativo.
Poke Idle World exige autorização de staff para qualquer programa de
terceiros conectado ao jogo: https://poke.idleworld.online/rules
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

COUNTERS = ("xp_total", "gold_total", "kills_total", "captures_total", "shiny_total")
STOCK = ("potions", "pokeballs")
FIELDS = {"profile_id", "account_id", "pokemon_id", "hunt_id", "recorded_at", *COUNTERS, *STOCK}
MAX_SNAPSHOTS = 2000

def _alias(value, name):
    if not isinstance(value, str) or not 1 <= len(value) <= 64 or "@" in value or any(ord(c) < 32 for c in value):
        raise ValueError(name + " deve ser apelido local, sem dados pessoais")
    return value.strip()

def _amount(value, key):
    if type(value) is not int or not 0 <= value <= 10**15:
        raise ValueError(key + ": número inteiro não negativo necessário")
    return value

def parse_snapshot(raw: dict) -> dict:
    if not isinstance(raw, dict) or set(raw) != FIELDS:
        raise ValueError("Campos inesperados/ausentes. Não informe credenciais.")
    row = {key: _alias(raw[key], key) for key in ("profile_id","account_id","pokemon_id","hunt_id")}
    try:
        stamp = datetime.fromisoformat(raw["recorded_at"])
    except (ValueError, TypeError) as exc:
        raise ValueError("Data inválida; ISO 8601 com fuso horário") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Data precisa de fuso explícito")
    row["recorded_at"] = stamp
    for key in COUNTERS + STOCK:
        row[key] = _amount(raw[key], key)
    return row

def compare_pair(before: dict, after: dict) -> dict:
    """Compara counters da mesma conta + Pokémon + hunt, sem extrapolar drops."""
    hours = (after["recorded_at"] - before["recorded_at"]).total_seconds() / 3600
    if not .5 <= hours <= 720:
        return {"status":"measure_more", "reason":"Exija 30 minutos até 30 dias de observação"}
    delta = {key: after[key] - before[key] for key in COUNTERS}
    if any(delta[key] < 0 for key in ("xp_total","kills_total","captures_total","shiny_total")):
        return {"status":"inconsistent", "reason":"Contador reiniciou ou XP caiu; não calcular eficiência"}
    net_gold = delta["gold_total"]
    result = {
        "status":"measured", "hours":round(hours,3),
        "xp_per_hour":round(delta["xp_total"]/hours,2),
        "net_gold_per_hour":round(net_gold/hours,2),
        "kills_per_hour":round(delta["kills_total"]/hours,2),
        "captures_per_hour":round(delta["captures_total"]/hours,2),
        "new_shiny_marked_manually":delta["shiny_total"],
        "warnings":[],
        "stocks":{}
    }
    if net_gold < 0:
        result["warnings"].append("Gold líquido caiu; pode haver despesas. Não inferir lucro ou dinheiro real.")
    if delta["shiny_total"] > 0:
        result["warnings"].append("Shiny registrado manualmente! Confirmar dentro do jogo.")
    if delta["kills_total"] == 0:
        result["warnings"].append("Sem kills entre medições: verificar manualmente se o farm parou.")
    for resource in STOCK:
        left, used = after[resource], max(0,before[resource]-after[resource])
        use_hour = used / hours
        eta = round(left/use_hour,2) if use_hour > 0 else None
        result["stocks"][resource] = {"remaining":left,"consumed_per_hour_observed":round(use_hour,2),
                                      "estimated_hours_left":eta}
        if left <= 10:
            result["warnings"].append(f"{resource}: estoque baixo ({left})")
        if eta is not None and eta <= 1:
            result["warnings"].append(f"{resource}: até 1h restante se o consumo continuar")
    return result

def rank_manual_hunts(groups: list[dict], priority: str = "balanced") -> list[dict]:
    """Rankings por perfil/conta/Pokémon, nunca dados entre perfis."""
    if priority not in ("xp", "gold", "balanced"):
        raise ValueError("Prioridade inválida")
    by_identity = defaultdict(list)
    for group in groups:
        if group["status"] != "measured":
            continue
        key = (group["profile_id"],group["account_id"],group["pokemon_id"])
        by_identity[key].append(group)
    ranked = []
    for (profile,account,pokemon),rows in sorted(by_identity.items()):
        if len(rows) < 2:
            continue
        max_xp=max(0.0,*(r["xp_per_hour"] for r in rows))
        max_gold=max(0.0,*(r["net_gold_per_hour"] for r in rows))
        scores=[]
        for row in rows:
            x=row["xp_per_hour"]/max_xp if max_xp else 0.0
            g=max(0,row["net_gold_per_hour"])/max_gold if max_gold else 0.0
            score=x if priority=="xp" else g if priority=="gold" else (x+g)/2
            scores.append({"hunt_id":row["hunt_id"],"score":round(score,4),
                           "xp_per_hour":row["xp_per_hour"],
                           "net_gold_per_hour":row["net_gold_per_hour"]})
        scores.sort(key=lambda row:(row["score"],row["hunt_id"]),reverse=True)
        ranked.append({"profile_id":profile,"account_id":account,
                       "pokemon_id":pokemon,"priority":priority,"hunts":scores,
                       "note":"Somente dados anotados; nenhuma hunt foi executada pelo agente."})
    return ranked


def analyze(payload: dict, priority: str = "balanced") -> dict:
    if not isinstance(payload,dict) or set(payload) != {"game","source","snapshots"}:
        raise ValueError("Formato do relatório inválido")
    if payload["game"] != "world":
        raise ValueError("Relatório específico do World; não misturar economias")
    if payload["source"] not in ("manual","demo"):
        raise ValueError("Somente manual ou demo: integração externa não autorizada")
    readings = payload["snapshots"]
    if not isinstance(readings,list) or len(readings) > MAX_SNAPSHOTS:
        raise ValueError("Lista de snapshots inválida ou muito grande")
    parsed = [parse_snapshot(s) for s in readings]
    by_scope = defaultdict(list)
    for item in parsed:
        key=(item["profile_id"],item["account_id"],item["pokemon_id"],item["hunt_id"])
        by_scope[key].append(item)
    results = []
    for (profile,account,pokemon,hunt),rows in sorted(by_scope.items()):
        rows.sort(key=lambda row: row["recorded_at"])
        distinct = len({row["recorded_at"] for row in rows}) == len(rows)
        comparison = (compare_pair(rows[0],rows[-1]) if len(rows)>=2 and distinct
                      else {"status":"measure_more","reason":"Pelo menos duas observações com horários diferentes"})
        results.append({"profile_id":profile,"account_id":account,"pokemon_id":pokemon,"hunt_id":hunt,
                        "samples":len(rows),**comparison})
    return {"game":"world","mode":"manual_offline","source":payload["source"],
            "is_demo":payload["source"]=="demo","groups":results,
            "rankings":rank_manual_hunts(results, priority),
            "revenue_usdt":None,
            "note":"XP/gold/estoques medidos a partir de anotação manual; não equivale a ganhos reais, nem autoriza automação."}

def analyze_file(path: Path, priority: str = "balanced") -> dict:
    if path.stat().st_size > 1024*1024:
        raise ValueError("Arquivo maior que 1 MB")
    return analyze(json.loads(path.read_text(encoding="utf-8-sig")), priority)

def main():
    parser=argparse.ArgumentParser(description="PokeGrid Analytics: manual, sem automação do World")
    parser.add_argument("--file",required=True,type=Path)
    parser.add_argument("--priority",choices=("xp","gold","balanced"),default="balanced")
    args=parser.parse_args()
    print(json.dumps(analyze_file(args.file,args.priority),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
