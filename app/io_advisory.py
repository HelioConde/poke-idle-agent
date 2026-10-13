"""Sugestões supervisionadas IO baseadas SOMENTE em observações validadas.

Não produz comandos, seletores, destinos de hunt ou permissões de execução.
A identidade da aba NÃO equivale à identidade comprovada do treinador.
"""
from __future__ import annotations

import math


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def build_io_advisory(stats: dict | None, windows: dict | None,
                      audit: dict | None) -> list[dict]:
    """Fila de no máximo três recomendações consultivas, sem efeitos colaterais."""
    stats, windows, audit = stats or {}, windows or {}, audit or {}
    result: list[dict] = []

    def add(kind: str, priority: str, message: str):
        result.append({"kind": kind, "priority": priority,
                       "status": "review_only", "message": message,
                       "action_authorized": False})

    hp, maximum = stats.get("hp_current"), stats.get("hp_max")
    if _number(hp) and _number(maximum) and maximum > 0 and hp / maximum < 0.25:
        add("review_health", "high",
            "HP observado abaixo de 25%. Verifique a equipe manualmente; não utilizar Desistir.")

    if audit.get("farm_state") != "active":
        add("confirm_farm", "normal",
            "Farm não confirmado na auditoria. Verifique o estado no jogo antes de qualquer decisão.")

    short, medium = windows.get("5m"), windows.get("15m")
    if _number(short) and _number(medium) and medium >= 100:
        if short < 0.7 * medium:
            add("investigate_xp_drop", "normal",
                "XP/h nos últimos 5 min abaixo de 70% da média de 15 min. "
                "Investigue a causa; não trocar hunt automaticamente.")
        else:
            add("monitor_trend", "info",
                "Médias de 5 e 15 min disponíveis. Continue observando antes de alterar a hunt.")
    elif not _number(short) or not _number(medium):
        add("collect_longer_window", "info",
            "Aguardando janelas confiáveis de 5 e 15 min para comparar a tendência.")

    # O monitor observa perfis e abas, mas não uma identidade validada de hunt.
    # Nunca propor select_hunt como executável com essa evidência.
    if len(result) < 3:
        add("verify_hunt_manually", "info",
            "Hunt e identidade da conta não comprovadas pela telemetria; "
            "comparações de caçadas permanecem consultivas.")

    return result[:3]
