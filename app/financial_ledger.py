"""Livro-caixa local e auditável para o funil econômico do agente.

Este módulo não acessa o jogo, carteira, e-mail ou navegador. Ele apenas
registra fatos que o usuário informou ou que uma fonte autorizada observou.
Gems, anúncios e saques pendentes permanecem separados de USDT recebido.
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from pathlib import Path

from app.economy import MIN_WITHDRAWAL_GEMS, net_gems


STAGES = frozenset({"acquired", "listed", "sold", "withdrawal_requested", "received"})
SOURCES = frozenset({"manual", "observed", "demo"})


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise ValueError(f"{label} inválido")
    if "@" in value:
        raise ValueError(f"{label} não pode conter e-mail")
    return value.strip()


def _amount(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float) or value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{label} inválido")
    number = float(value)
    if number < 0 or (positive and number == 0):
        raise ValueError(f"{label} inválido")
    return number


class FinancialLedger:
    """Persiste eventos financeiros isolados por `(game, profile_id, account_id)`."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS financial_events (
                    id INTEGER PRIMARY KEY,
                    recorded_at REAL NOT NULL,
                    game TEXT NOT NULL CHECK (game IN ('io', 'world')),
                    profile_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    asset_name TEXT NOT NULL,
                    stage TEXT NOT NULL CHECK (stage IN
                        ('acquired', 'listed', 'sold', 'withdrawal_requested', 'received')),
                    source TEXT NOT NULL CHECK (source IN ('manual', 'observed', 'demo')),
                    gross_gems REAL NOT NULL DEFAULT 0,
                    net_gems REAL NOT NULL DEFAULT 0,
                    usdt_received REAL NOT NULL DEFAULT 0,
                    operating_cost_usdt REAL NOT NULL DEFAULT 0,
                    category TEXT,
                    manual_confirmation INTEGER NOT NULL DEFAULT 0
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS financial_events_account_time
                ON financial_events(game, profile_id, account_id, recorded_at DESC)
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, *, game: str, profile_id: str, account_id: str,
               asset_name: str, stage: str, source: str, gross_gems: float = 0,
               category: str | None = None, usdt_received: float = 0,
               operating_cost_usdt: float = 0, manual_confirmation: bool = False,
               recorded_at: float | None = None) -> None:
        """Registra um fato; somente ``received`` confirmado conta como receita real."""
        if game not in ("io", "world") or stage not in STAGES or source not in SOURCES:
            raise ValueError("Jogo, estado ou origem inválidos")
        profile_id = _identifier(profile_id, "Perfil")
        account_id = _identifier(account_id, "Conta")
        asset_name = _identifier(asset_name, "Ativo")
        gross_gems = _amount(gross_gems, "Gems brutas")
        usdt_received = _amount(usdt_received, "USDT recebido")
        operating_cost_usdt = _amount(operating_cost_usdt, "Custo operacional")
        timestamp = time.time() if recorded_at is None else _amount(recorded_at, "Data", positive=True)
        if type(manual_confirmation) is not bool:
            raise ValueError("Confirmação manual inválida")
        if stage == "sold":
            if game != "io" or category not in ("item", "pokemon") or gross_gems <= 0:
                raise ValueError("Venda exige IO, categoria e preço em Gems")
            calculated_net_gems = net_gems(gross_gems, category, "completed")
        else:
            if category is not None or gross_gems:
                raise ValueError("Somente venda concluída aceita Gems")
            calculated_net_gems = 0.0
        if stage == "received":
            if game != "io" or source == "demo" or not manual_confirmation or usdt_received <= 0:
                raise ValueError("Recebimento exige confirmação manual de USDT no IO")
        elif usdt_received:
            raise ValueError("USDT só pode ser registrado como recebido")
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                INSERT INTO financial_events
                (recorded_at, game, profile_id, account_id, asset_name, stage, source,
                 gross_gems, net_gems, usdt_received, operating_cost_usdt, category,
                 manual_confirmation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, game, profile_id, account_id, asset_name, stage, source,
                  gross_gems, calculated_net_gems, usdt_received, operating_cost_usdt,
                  category, int(manual_confirmation)))

    def summary(self, *, game: str, profile_id: str, account_id: str) -> dict:
        """Resume cinco estados sem converter saldo ou pendência em dinheiro real."""
        if game not in ("io", "world"):
            raise ValueError("Jogo inválido")
        profile_id = _identifier(profile_id, "Perfil")
        account_id = _identifier(account_id, "Conta")
        with closing(self._connect()) as connection, connection:
            rows = connection.execute("""
                SELECT stage, source, net_gems, usdt_received, operating_cost_usdt
                FROM financial_events
                WHERE game = ? AND profile_id = ? AND account_id = ?
            """, (game, profile_id, account_id)).fetchall()
        actual = [row for row in rows if row["source"] != "demo"]
        count = lambda stage: sum(row["stage"] == stage for row in actual)
        completed_net_gems = round(sum(row["net_gems"] for row in actual
                                       if row["stage"] == "sold"), 4)
        confirmed_usdt = round(sum(row["usdt_received"] for row in actual
                                   if row["stage"] == "received"), 4)
        costs = round(sum(row["operating_cost_usdt"] for row in actual), 4)
        return {
            "game": game, "profile_id": profile_id, "account_id": account_id,
            "assets_obtained": count("acquired"), "listings": count("listed"),
            "completed_sales": count("sold"), "completed_sale_net_gems": completed_net_gems,
            "withdrawal_requests": count("withdrawal_requested"),
            "withdrawal_eligible": game == "io" and completed_net_gems >= MIN_WITHDRAWAL_GEMS,
            "confirmed_usdt_received": confirmed_usdt,
            "operating_cost_usdt": costs,
            "proven_net_profit_usdt": round(confirmed_usdt - costs, 4),
            "real_revenue_confirmed": confirmed_usdt > 0,
        }
