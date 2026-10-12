import tempfile
import json
import subprocess
import sys
import unittest
from pathlib import Path

from app.financial_ledger import FinancialLedger


class FinancialLedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.ledger = FinancialLedger(Path(self.directory.name) / "finance.sqlite3")
        self.identity = {"game": "io", "profile_id": "profile-a", "account_id": "account-a"}

    def tearDown(self):
        self.directory.cleanup()

    def test_five_states_are_separate_and_only_received_is_revenue(self):
        for stage in ("acquired", "listed", "withdrawal_requested"):
            self.ledger.record(**self.identity, asset_name="Token", stage=stage, source="manual")
        self.ledger.record(**self.identity, asset_name="Token", stage="sold", source="observed",
                           gross_gems=100, category="item")
        before = self.ledger.summary(**self.identity)
        self.assertEqual(before["completed_sale_net_gems"], 85)
        self.assertEqual(before["confirmed_usdt_received"], 0)
        self.assertFalse(before["real_revenue_confirmed"])
        self.ledger.record(**self.identity, asset_name="Saque", stage="received", source="manual",
                           usdt_received=7, manual_confirmation=True, operating_cost_usdt=1)
        after = self.ledger.summary(**self.identity)
        self.assertEqual(after["confirmed_usdt_received"], 7)
        self.assertEqual(after["proven_net_profit_usdt"], 6)

    def test_ledger_isolated_by_account_and_demo_never_counts(self):
        self.ledger.record(**self.identity, asset_name="Item", stage="sold", source="demo",
                           gross_gems=1000, category="item")
        self.ledger.record(game="io", profile_id="profile-b", account_id="account-b",
                           asset_name="Item", stage="sold", source="manual",
                           gross_gems=1000, category="item")
        self.assertEqual(self.ledger.summary(**self.identity)["completed_sale_net_gems"], 0)
        self.assertEqual(self.ledger.summary(game="io", profile_id="profile-b", account_id="account-b")
                         ["completed_sale_net_gems"], 850)

    def test_rejects_unconfirmed_or_non_io_money_claims(self):
        with self.assertRaises(ValueError):
            self.ledger.record(game="io", profile_id="email@example.com", account_id="a",
                               asset_name="Item", stage="acquired", source="manual")
        with self.assertRaises(ValueError):
            self.ledger.record(**self.identity, asset_name="Saque", stage="received", source="manual",
                               usdt_received=7)
        with self.assertRaises(ValueError):
            self.ledger.record(game="world", profile_id="p", account_id="a", asset_name="Saque",
                               stage="received", source="manual", usdt_received=7,
                               manual_confirmation=True)
        with self.assertRaises(ValueError):
            self.ledger.record(**self.identity, asset_name="Item", stage="listed", source="manual",
                               gross_gems=5, category="item")

    def test_cli_records_sale_and_never_marks_it_as_usdt(self):
        root = Path(__file__).resolve().parents[1]
        ledger_path = Path(self.directory.name) / "cli.sqlite3"
        command = [sys.executable, "-m", "app.financial_ledger", "--ledger", str(ledger_path),
                   "record", "--game", "io", "--profile", "profile-a", "--account", "account-a",
                   "--asset", "Item", "--stage", "sold", "--gross-gems", "100", "--category", "item"]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["completed_sale_net_gems"], 85)
        self.assertEqual(data["confirmed_usdt_received"], 0)


if __name__ == "__main__":
    unittest.main()
