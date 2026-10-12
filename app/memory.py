"""Memória local SQLite para observações e decisões seguras.

Este módulo não recebe HTML, URLs, cookies, credenciais ou ações do navegador.
Ele persiste apenas o estado já validado pelo adaptador e decisões dry-run, para
que uma reinicialização do monitor não misture históricos de perfis.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path


class MemoryStore:
    """Armazenamento local, pequeno e separado por perfil e sessão."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY,
                    observed_at REAL NOT NULL,
                    profile_id TEXT NOT NULL,
                    game TEXT NOT NULL CHECK (game IN ('io', 'world')),
                    session_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    decision_json TEXT
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS observations_profile_session_time
                ON observations(profile_id, session_id, observed_at DESC)
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _json(value: dict | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("Registro de memória inválido")
        def validate(item: object) -> None:
            if isinstance(item, dict):
                for key, nested in item.items():
                    if not isinstance(key, str):
                        raise ValueError("Chave de memória inválida")
                    if re.search(r"(?:token|cookie|password|secret|authorization|email)",
                                 key, re.IGNORECASE):
                        raise ValueError("Dado sensível não pode ser persistido")
                    validate(nested)
            elif isinstance(item, list):
                for nested in item:
                    validate(nested)
            elif not isinstance(item, (str, int, float, bool, type(None))):
                raise ValueError("Valor de memória inválido")
        validate(value)
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 16_384:
            raise ValueError("Registro de memória grande demais")
        return encoded

    def record_observation(self, *, profile_id: str, game: str,
                           session_id: str, state: dict,
                           decision: dict | None = None,
                           observed_at: float | None = None) -> None:
        """Registra uma leitura já normalizada; não executa ação alguma."""
        if (not isinstance(profile_id, str) or not profile_id or
                not isinstance(session_id, str) or not session_id or
                game not in ("io", "world")):
            raise ValueError("Identidade de memória inválida")
        timestamp = time.time() if observed_at is None else observed_at
        if not isinstance(timestamp, (int, float)) or timestamp <= 0:
            raise ValueError("Data de observação inválida")
        state_json = self._json(state)
        decision_json = self._json(decision)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO observations
                   (observed_at, profile_id, game, session_id, state_json, decision_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (float(timestamp), profile_id, game, session_id,
                 state_json, decision_json),
            )

    def history(self, profile_id: str, session_id: str,
                limit: int = 100) -> list[dict]:
        """Retorna somente o histórico da sessão e perfil solicitados."""
        if (not isinstance(profile_id, str) or not isinstance(session_id, str)
                or not 1 <= limit <= 1000):
            raise ValueError("Consulta de memória inválida")
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """SELECT observed_at, game, session_id, state_json, decision_json
                   FROM observations WHERE profile_id = ? AND session_id = ?
                   ORDER BY observed_at DESC, id DESC LIMIT ?""",
                (profile_id, session_id, limit),
            ).fetchall()
        return [{"observed_at": row["observed_at"], "game": row["game"],
                 "session_id": row["session_id"],
                 "state": json.loads(row["state_json"]),
                 "decision": (json.loads(row["decision_json"])
                              if row["decision_json"] else None)}
                for row in rows]
