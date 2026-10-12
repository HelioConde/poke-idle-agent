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

    def _get_world_report(self, process: subprocess.Popen, port: int) -> dict:
        for _ in range(30):
            if process.poll() is not None:
                self.fail(process.stderr.read())
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/world-pokegrid",timeout=1) as response:
                    return json.loads(response.read())
            except OSError:
                time.sleep(.05)
        self.fail("Painel não iniciou")

    def test_world_pokegrid_disabled_without_report(self):
        process=self._server(18769)
        try:
            report=self._get_world_report(process,18769)
        finally:
            self._stop(process)
        self.assertFalse(report["configured"])

    def test_world_pokegrid_example_is_marked_demo(self):
        fixture=ROOT/"examples"/"pokegrid_snapshots_demo.json"
        process=self._server(18770,"--world-report",str(fixture))
        try:
            payload=self._get_world_report(process,18770)
        finally:
            self._stop(process)
        self.assertTrue(payload["configured"])
        self.assertTrue(payload["report"]["is_demo"])
        self.assertEqual(payload["report"]["groups"][0]["status"],"measured")
        self.assertIsNone(payload["report"]["revenue_usdt"])

    def _get_capture_report(self, process: subprocess.Popen, port: int) -> dict:
        for _ in range(30):
            if process.poll() is not None:
                self.fail(process.stderr.read())
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/world-capture",timeout=1) as response:
                    return json.loads(response.read())
            except OSError:
                time.sleep(.05)
        self.fail("Painel não iniciou")

    def test_nonvip_capture_endpoint_disabled_without_file(self):
        process=self._server(18771)
        try:
            response=self._get_capture_report(process,18771)
        finally:
            self._stop(process)
        self.assertFalse(response["configured"])

    def test_nonvip_capture_example_never_executes_gameplay(self):
        fixture=ROOT/"examples"/"world_capture_demo.json"
        process=self._server(18772,"--world-capture",str(fixture))
        try:
            response=self._get_capture_report(process,18772)
        finally:
            self._stop(process)
        self.assertTrue(response["configured"])
        self.assertTrue(response["report"]["is_demo"])
        self.assertFalse(response["report"]["external_auto_catch_enabled"])
        self.assertEqual(response["report"]["accounts"][0]["allowed_method"],"manual_throw")
        self.assertEqual(response["report"]["accounts"][0]["recommended_ball"],"Poke Ball")
        self.assertIsNone(response["report"]["usdt_revenue"])

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
