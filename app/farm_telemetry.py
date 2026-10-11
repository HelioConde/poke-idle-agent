"""Métricas de farm derivadas somente de contadores e eventos observados."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class FarmSample:
    observed_at: float
    xp_total: float | None = None
    coins_total: float | None = None
    kills_total: int | None = None
    damage_taken_total: float | None = None
    healing_used_total: float | None = None
    defeats_total: int | None = None
    items_found_total: int | None = None


def _delta(samples: list[FarmSample], field: str) -> float | None:
    first = getattr(samples[0], field)
    last = getattr(samples[-1], field)
    if first is None or last is None or last < first:
        return None
    return float(last - first)


def summarize(samples: list[FarmSample]) -> dict:
    """Calcula taxas sem estimar o que a fonte não disponibilizou."""
    if len(samples) < 2:
        return {"data_status": "insufficient", "duration_seconds": None}
    times = [sample.observed_at for sample in samples]
    if any(not isinstance(item, (int, float)) for item in times):
        raise ValueError("Datas de amostra inválidas")
    counters = ("xp_total", "coins_total", "kills_total", "damage_taken_total",
                "healing_used_total", "defeats_total", "items_found_total")
    if any(getattr(sample, field) is not None and getattr(sample, field) < 0
           for sample in samples for field in counters):
        raise ValueError("Contadores não podem ser negativos")
    if any(after <= before for before, after in zip(times, times[1:])):
        raise ValueError("Amostras devem estar em ordem crescente")
    duration = float(times[-1] - times[0])
    result = {"data_status": "measured", "duration_seconds": duration}
    for field, name, factor in (
        ("xp_total", "xp_per_hour", 3600),
        ("coins_total", "coins_per_hour", 3600),
        ("kills_total", "kills_per_hour", 3600),
        ("kills_total", "kills_per_minute", 60),
    ):
        change = _delta(samples, field)
        result[name] = round(change / duration * factor, 2) if change is not None else None
    for field, name in (
        ("damage_taken_total", "damage_taken"),
        ("healing_used_total", "healing_used"),
        ("defeats_total", "defeats"),
        ("items_found_total", "items_found"),
    ):
        result[name] = _delta(samples, field)
    return result


def overkill_evidence(kill_times: list[float], respawn_seconds: float,
                      min_intervals: int = 3) -> dict:
    """Sinaliza gargalo de respawn apenas quando há eventos suficientes.

    É evidência, não uma afirmação de rentabilidade: a cadência de abates deve
    estar no limite do respawn informado pelo adaptador para haver sinalização.
    """
    if respawn_seconds <= 0 or min_intervals < 1:
        raise ValueError("Configuração de respawn inválida")
    if len(kill_times) < min_intervals + 1:
        return {"status": "insufficient", "overkill": None,
                "mean_kill_interval": None}
    intervals = [after - before for before, after in zip(kill_times, kill_times[1:])]
    if any(interval <= 0 for interval in intervals):
        raise ValueError("Eventos de abate inválidos")
    interval = round(mean(intervals), 2)
    return {"status": "measured", "overkill": interval <= respawn_seconds,
            "mean_kill_interval": interval}
