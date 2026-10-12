import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from app.financial_ledger import FinancialLedger


ROOT = Path(__file__).resolve().parents[1]


class DashboardFinanceTests(unittest.TestCase):
    def _server(self, port: int, *extra: str) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, "dashboard.py", "--port", str(port), *extra],
                                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                text=True)

    def _get_json(self, process: subprocess.Popen, port: int) -> dict:
        for _ in range(30):
            if process.poll() is not None:
                self.fail(process.stderr.read())
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/finance", timeout=1) as response:
                    return json.loads(response.read())
            except OSError:
                time.sleep(.05)
        self.fail("Painel não iniciou")

    @staticmethod
    def _stop(process: subprocess.Popen) -> None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
        if process.stderr is not None:
            process.stderr.close()

    def test_finance_endpoint_is_disabled_without_ledger_configuration(self):
        process = self._server(18767)
        try:
            payload = self._get_json(process, 18767)
        finally:
            self._stop(process)
        self.assertFalse(payload["configured"])

    def test_finance_endpoint_reads_only_configured_account_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "financial.sqlite3"
            ledger = FinancialLedger(ledger_path)
            ledger.record(game="io", profile_id="profile-a", account_id="account-a",
                          asset_name="Item", stage="sold", source="manual",
                          gross_gems=100, category="item")
            process = self._server(18768, "--ledger", str(ledger_path),
                                   "--finance-game", "io", "--finance-profile", "profile-a",
                                   "--finance-account", "account-a")
            try:
                payload = self._get_json(process, 18768)
            finally:
                self._stop(process)
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["summary"]["completed_sale_net_gems"], 85)
        self.assertEqual(payload["summary"]["confirmed_usdt_received"], 0)


if __name__ == "__main__":
    unittest.main()
