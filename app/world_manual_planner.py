"""Planejador OFFLINE para Poke Idle World; nunca faz login, leitura ou clique no jogo."""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Hunt:
    name: str
    minutes: float
    xp: float
    gold: float
    cost: float
    source: str = "manual"

    @classmethod
    def parse(cls, row: dict) -> "Hunt":
        name = str(row["hunt"]).strip()
        minutes = float(row["minutes"])
        xp, gold = float(row["xp_gained"]), float(row["gold_gained"])
        cost = float(row.get("expenses_gold") or 0)
        source = (row.get("source") or "manual").lower().strip()
        if (not name or len(name)>100 or not 0 < minutes <= 1440 or
                any(not 0 <= x <= 1e15 for x in (xp,gold,cost)) or
                source not in ("manual","demo")):
            raise ValueError("Hunt inválida; use números positivos e source manual/demo")
        return cls(name,minutes,xp,gold,cost,source)

def load(path: Path) -> list[Hunt]:
    with path.open(encoding="utf-8-sig",newline="") as stream:
        records=list(csv.DictReader(stream))
    if len(records)>500:
        raise ValueError("Máximo de 500 medições")
    return [Hunt.parse(row) for row in records]

def compare(rows: list[Hunt], priority: str="balanced") -> dict:
    if priority not in ("xp","gold","balanced"):
        raise ValueError("Prioridade inválida")
    if not rows or any(row.source != "manual" for row in rows):
        return {"status":"measure_more","reason":"Nenhuma medição real; exemplos são fictícios","ranked":[]}
    groups: dict[str,dict]={}
    for row in rows:
        g=groups.setdefault(row.name,{"minutes":0.,"xp":0.,"gold":0.,"cost":0.,"samples":0})
        g["minutes"]+=row.minutes
        g["xp"]+=row.xp
        g["gold"]+=row.gold
        g["cost"]+=row.cost
        g["samples"]+=1
    if len(groups)<2 or any(g["minutes"]<30 for g in groups.values()):
        return {"status":"measure_more","reason":"Meça pelo menos duas hunts por 30 minutos cada","ranked":[]}
    ranked=[]
    for name,g in groups.items():
        hours=g["minutes"]/60
        ranked.append({"hunt":name,"minutes":round(g["minutes"],2),
                       "xp_per_hour":round(g["xp"]/hours,2),
                       "net_gold_per_hour":round((g["gold"]-g["cost"])/hours,2),
                       "samples":g["samples"]})
    high_xp=max(0.,*(r["xp_per_hour"] for r in ranked))
    high_gold=max(0.,*(r["net_gold_per_hour"] for r in ranked))
    for r in ranked:
        x=r["xp_per_hour"]/high_xp if high_xp else 0
        g=max(0,r["net_gold_per_hour"])/high_gold if high_gold else 0
        r["score"]=round(x if priority=="xp" else g if priority=="gold" else (x+g)/2,4)
    ranked.sort(key=lambda r:(r["score"],r["minutes"]),reverse=True)
    return {"status":"ranked","priority":priority,"ranked":ranked,
            "note":"XP e gold World NÃO são USDT ou reais sacados"}

def advise(species: str, pokemon_level: int, trainer_level: int|None) -> list[str]:
    if not 1 <= pokemon_level <= 10000 or (trainer_level is not None and not 1 <= trainer_level <= 10000):
        raise ValueError("Nível inválido")
    notes=[
        "Use somente rotinas nativas oficiais do World, não programas de automação externa.",
        "Nível de Pokémon e de treinador são independentes.",
        "Compare gold líquido/h e XP/h manualmente; não são rendimentos em R$."
    ]
    if species.casefold().strip() in ("charmander","charmeleon") and pokemon_level>=40:
        notes.append("Evoluir de graça reinicia no nível 1! Com pedras de evolução corretas preserva nível. Confira o modal em Cerulean.")
    if species.casefold().strip() == "charizard":
        notes.append("Charizard é Fogo/Voador: verifique se as fraquezas a Pedra, Água e Elétrico seguem as regras específicas deste jogo; não assuma vantagem apenas pelo nível.")
    if pokemon_level>=100:
        notes.append("Avalie hunts acessíveis entre níveis 80–150 e eficiência de tipos; não escolha somente XP bruto.")
    if trainer_level is None:
        notes.append("Informe também o nível do TREINADOR para avaliar acesso às hunts.")
    return notes

def main():
    parser=argparse.ArgumentParser(description="Analisador OFFLINE World")
    parser.add_argument("--species",default="Charizard")
    parser.add_argument("--pokemon-level",type=int,default=110)
    parser.add_argument("--trainer-level",type=int)
    parser.add_argument("--csv",type=Path)
    parser.add_argument("--priority",choices=("xp","gold","balanced"),default="balanced")
    args=parser.parse_args()
    output={"game":"world","mode":"manual_offline","species":args.species,
            "pokemon_level":args.pokemon_level,"trainer_level":args.trainer_level,
            "recommendations":advise(args.species,args.pokemon_level,args.trainer_level)}
    if args.csv:
        output["comparison"]=compare(load(args.csv),args.priority)
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
