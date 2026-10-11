"""Comparador local de Poke Idle World / IO baseado em CSV fornecido pelo usuário."""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

GAME_NAMES = {"world": "Poke Idle World", "io": "Poke Idle IO"}
USD_PER_IO_GEM = 0.007  # Cotação anunciada, NÃO confirma saque real.

@dataclass(frozen=True)
class Session:
    game: str
    minutes: float
    xp: float
    coins: float
    gems_received_net: float
    listings: int
    sales: int
    withdrawn_usd: float
    operating_cost_brl: float
    source: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Session":
        game = row["game"].strip().lower()
        if game not in GAME_NAMES:
            raise ValueError(f"Jogo inválido: {game}")
        numbers = {"minutes": float, "xp": float, "coins": float,
                   "gems_received_net": float, "listings": int, "sales": int,
                   "withdrawn_usd": float, "operating_cost_brl": float}
        values = {k: cast(row[k]) for k, cast in numbers.items()}
        if values["minutes"] <= 0 or any(v < 0 for k, v in values.items() if k != "minutes"):
            raise ValueError("Duração deve ser >0 e valores não podem ser negativos")
        if values["sales"] > values["listings"]:
            raise ValueError("Vendas excedem o número de anúncios")
        return cls(game=game, **values, source=row.get("source", "real").strip().lower() or "real")

def load_sessions(path: Path) -> list[Session]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [Session.from_row(row) for row in csv.DictReader(file)]

def aggregate(sessions: list[Session]) -> list[dict]:
    output = []
    for code, name in GAME_NAMES.items():
        subset = [row for row in sessions if row.game == code]
        if not subset:
            continue
        hours = sum(x.minutes for x in subset) / 60
        gems = sum(x.gems_received_net for x in subset)
        paid = sum(x.withdrawn_usd for x in subset if x.source != "demo")
        output.append({
            "game": code, "name": name, "hours": round(hours, 3),
            "sessions": len(subset),
            "source": "DEMONSTRAÇÃO" if any(x.source == "demo" for x in subset) else "REGISTRADO",
            "xp_per_hour": round(sum(x.xp for x in subset) / hours, 2),
            "coins_per_hour": round(sum(x.coins for x in subset) / hours, 2),
            "gems_net_per_hour": round(gems / hours, 2),
            "sold_items": sum(x.sales for x in subset),
            "withdrawn_usd": round(paid, 2),
            "withdrawn_usd_per_hour": round(paid / hours, 4),
            "indicative_io_gems_usd": round(gems * USD_PER_IO_GEM, 2) if code == "io" else None,
            "operating_cost_brl": round(sum(x.operating_cost_brl for x in subset), 2)
        })
    return output

def markdown_report(result: list[dict]) -> str:
    lines = ["# Poke Idle Lab — comparação de sessões", "",
             "DEMONSTRAÇÃO significa dados fictícios. Gemas não são saques.", "",
             "| Métrica | World | IO |", "|---|---:|---:|"]
    indexed = {item["game"]: item for item in result}
    metrics = [
        ("source", "Origem"), ("hours", "Horas"),
        ("xp_per_hour", "XP/h"), ("coins_per_hour", "Coins/h"),
        ("gems_net_per_hour", "Gemas líquidas/h"), ("sold_items", "Vendas concluídas"),
        ("withdrawn_usd", "US$ sacados"), ("withdrawn_usd_per_hour", "US$ sacados/h"),
        ("indicative_io_gems_usd", "US$ indicativos IO NÃO sacados"),
        ("operating_cost_brl", "Custo R$")]
    for key, label in metrics:
        def display(game):
            value = indexed.get(game, {}).get(key)
            return "—" if value is None else str(value)
        lines.append(f"| {label} | {display('world')} | {display('io')} |")
    lines.extend(["", "Atenção: renda depende de saques confirmados e custos em mesma moeda."])
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Compara sessões em CSV local")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = aggregate(load_sessions(args.csv))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else markdown_report(result))

if __name__ == "__main__":
    main()
