"""Ranking experimental, somente leitura, baseado em estimativas CSV."""
import argparse
import csv
from pathlib import Path

def rank_hunts(rows: list[dict]) -> list[dict]:
    ranked = []
    for row in rows:
        xp = float(row["xp_per_hour"])
        gems = float(row["estimated_gems_per_hour"])
        risk = float(row["failure_probability"])
        confidence = float(row["confidence"])
        if xp < 0 or gems < 0 or not 0 <= risk <= 1 or not 0 <= confidence <= 1:
            raise ValueError("XP/gemas >=0; risco/confiança entre 0 e 1")
        score = (xp / 1000 + gems * 10) * (1 - risk) * confidence
        ranked.append({"game": row["game"], "hunt": row["hunt"],
                       "score": round(score, 4), "confidence": confidence,
                       "source": row.get("source", "manual")})
    return sorted(ranked, key=lambda x: x["score"], reverse=True)

def main() -> int:
    parser = argparse.ArgumentParser(description="Classifica hunts pelo CSV")
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    for idx, row in enumerate(rank_hunts(rows), 1):
        print(f'{idx}. [{row["game"]}] {row["hunt"]} — score {row["score"]} (confiança {row["confidence"]})')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
