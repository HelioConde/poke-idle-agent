"""Validação e recomendações somente consultivas para o Poke Idle IO.

Inspirado no loop observe→decide→act→learn de agentes de jogos.
Nesta etapa act é DRY-RUN; nenhum comando é enviado ao jogo.
"""
from __future__ import annotations
import math

ALLOWED = {
    "level": 10_000,
    "xp_current": 1e15,
    "xp_max": 1e15,
    "hp_current": 1e15,
    "hp_max": 1e15,
    "coins": 1e15,
    "gems": 1e15,
}

def sanitize(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("source") != "dom":
        raise ValueError("Telemetria não autorizada")
    stats = value.get("stats")
    if not isinstance(stats, dict) or len(stats) > len(ALLOWED):
        raise ValueError("Estatísticas inválidas")
    cleaned: dict[str, float] = {}
    for key, val in stats.items():
        if key not in ALLOWED or type(val) not in (float, int):
            raise ValueError("Campo não permitido ou valor inválido")
        if not math.isfinite(val) or val < 0 or val > ALLOWED[key]:
            raise ValueError("Estatística fora dos limites")
        cleaned[key] = val
    if ("hp_current" in cleaned and "hp_max" in cleaned and
            cleaned["hp_current"] > cleaned["hp_max"]):
        raise ValueError("HP maior que máximo")
    if ("xp_current" in cleaned and "xp_max" in cleaned and
            cleaned["xp_current"] > cleaned["xp_max"]):
        raise ValueError("XP maior que máximo")
    return {"source": "dom", "stats": cleaned, "available": bool(cleaned)}


def dry_run_decision(stats: dict | None, xp_per_hour: float | None = None) -> dict:
    """Descreve o próximo passo possível sem executar clique/tecla/transação."""
    stats = stats or {}
    if not stats:
        return {"mode": "dry_run", "action": "observe",
                "reason": "Sem estatísticas legíveis no DOM; talvez a cena seja Canvas."}
    hp, maxhp = stats.get("hp_current"), stats.get("hp_max")
    if maxhp and hp is not None and hp / maxhp < 0.25:
        return {"mode": "dry_run", "action": "review_health",
                "reason": "HP abaixo de 25%; verificar cura/segurança manualmente."}
    if xp_per_hour is not None and xp_per_hour >= 0:
        return {"mode": "dry_run", "action": "track_farm",
                "reason": f"XP/h observado entre amostras: {xp_per_hour:.0f}. Compare hunts antes de mudar."}
    return {"mode": "dry_run", "action": "collect_more",
            "reason": "Telemetria parcial; aguardar novas amostras sem interagir com o jogo."}


def measured_xp_per_hour(previous: dict | None, current: dict,
                         elapsed_seconds: float) -> float | None:
    """Mede diferença de XP no mesmo nível; não infere valores ausentes."""
    if not previous or elapsed_seconds < 5 or elapsed_seconds > 600:
        return None
    for key in ("level", "xp_current"):
        if key not in previous or key not in current:
            return None
    if previous["level"] != current["level"]:
        return None
    delta = current["xp_current"] - previous["xp_current"]
    if delta < 0:
        return None
    return round(delta / elapsed_seconds * 3600, 2)


DIAGNOSTIC_STATUSES = frozenset({
    "landing", "other_route", "reader_unavailable", "no_matches", "metrics"
})


def sanitize_observation(value: object) -> dict:
    """Aceita somente status e contagens. Nada de URL, HTML ou identificadores."""
    if not isinstance(value, dict) or set(value) != {
            "status", "canvas", "iframes", "candidates"}:
        raise ValueError("Diagnóstico inválido")
    if value["status"] not in DIAGNOSTIC_STATUSES:
        raise ValueError("Status de diagnóstico inválido")
    for key in ("canvas", "iframes", "candidates"):
        maximum = 3500 if key == "candidates" else 99
        if type(value[key]) is not int or not 0 <= value[key] <= maximum:
            raise ValueError("Contagem de diagnóstico inválida")
    return dict(value)
