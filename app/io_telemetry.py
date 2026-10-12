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
    def result(action: str, objective: str, reason: str, confidence: str,
               risk: str, preconditions: list[str], expected: str) -> dict:
        return {
            "mode": "dry_run", "action": action, "objective": objective,
            "reason": reason, "data_used": sorted(stats), "confidence": confidence,
            "risk": risk, "preconditions": preconditions,
            "expected_result": expected,
            "verification_plan": "Comparar a próxima observação validada; não agir se ela divergir.",
            "permission_required": False,
        }
    stats = stats or {}
    if not stats:
        return result("observe", "Observar mais amostras",
                      "Sem estatísticas legíveis no DOM; talvez a cena seja Canvas.",
                      "baixa", "baixo", ["Leitura DOM ou diagnóstico disponível"],
                      "Diagnóstico mais preciso, sem interação.")
    hp, maxhp = stats.get("hp_current"), stats.get("hp_max")
    if maxhp and hp is not None and hp / maxhp < 0.25:
        return result("review_health", "Revisar segurança",
                      "HP abaixo de 25%; verificar cura/segurança manualmente.",
                      "alta", "médio", ["HP atual e máximo validados"],
                      "Usuário avalia cura; nenhum item é usado automaticamente.")
    if xp_per_hour is not None and xp_per_hour >= 0:
        return result("track_farm", "Medir eficiência de farm",
                      f"XP/h observado entre amostras: {xp_per_hour:.0f}. Compare hunts antes de mudar.",
                      "média", "baixo", ["Duas amostras válidas no mesmo nível"],
                      "Mais dados comparáveis, sem mudança automática de hunt.")
    return result("collect_more", "Completar telemetria",
                  "Telemetria parcial; aguardar novas amostras sem interagir com o jogo.",
                  "baixa", "baixo", ["Leitura parcial validada"],
                  "Amostras suficientes para uma recomendação futura.")


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
    "landing", "other_route", "reader_unavailable", "no_matches", "metrics", "legacy_protocol"
})

XP_REASONS = frozenset({
    "trainer_xp_scoped", "trainer_panel_missing", "trainer_level_missing",
    "trainer_xp_missing", "trainer_xp_ambiguous", "not_on_app", "unknown", "reader_unavailable",
})

TELEMETRY_PROTOCOL_VERSION = 2
DOM_READER_VERSIONS = frozenset({"trainer-xp-scoped-v1", "unknown"})
CONTENT_STATES = frozenset({"responded", "unavailable", "outdated", "not_app"})


def sanitize_observation(value: object) -> dict:
    """Aceita somente status e contagens. Nada de URL, HTML ou identificadores."""
    basic = {"status", "canvas", "iframes", "candidates"}
    legacy_extra = {"xp_candidates", "xp_ambiguous"}
    scoped_extra = legacy_extra | {"xp_trainer_scoped"}
    current_extra = scoped_extra | {"xp_reason"}
    versioned_extra = current_extra | {"telemetry_protocol", "reader_version", "content_state"}
    if (not isinstance(value, dict) or not basic.issubset(value) or
            (set(value) - basic) not in (set(), legacy_extra, scoped_extra, current_extra, versioned_extra)):
        raise ValueError("Diagnóstico inválido")
    if not isinstance(value["status"], str) or value["status"] not in DIAGNOSTIC_STATUSES:
        raise ValueError("Status de diagnóstico inválido")
    for key in ("canvas", "iframes", "candidates"):
        maximum = 3500 if key == "candidates" else 99
        if type(value[key]) is not int or not 0 <= value[key] <= maximum:
            raise ValueError("Contagem de diagnóstico inválida")
    if legacy_extra.issubset(value):
        scoped = value.get("xp_trainer_scoped", False)
        if (type(value["xp_candidates"]) is not int or
                not 0 <= value["xp_candidates"] <= 20 or
                type(value["xp_ambiguous"]) is not bool or
                type(scoped) is not bool or
                (scoped and value["xp_candidates"] == 0) or
                value["xp_ambiguous"] != (value["xp_candidates"] > 1 and not scoped)):
            raise ValueError("Contagem de XP inválida")
        if "xp_reason" in value and (
                not isinstance(value["xp_reason"], str) or
                value["xp_reason"] not in XP_REASONS or
                (scoped and value["xp_reason"] != "trainer_xp_scoped")):
            raise ValueError("Motivo de XP inválido")
    if versioned_extra.issubset(value):
        if (value["telemetry_protocol"] != TELEMETRY_PROTOCOL_VERSION or
                value["reader_version"] not in DOM_READER_VERSIONS or
                value["content_state"] not in CONTENT_STATES):
            raise ValueError("Versão de telemetria inválida")
        if (value["content_state"] == "responded") != (value["reader_version"] == "trainer-xp-scoped-v1"):
            raise ValueError("Estado do leitor incompatível")
    return dict(value)
