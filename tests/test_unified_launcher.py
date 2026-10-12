"""Teste end-to-end do painel UNICO, sem navegador autenticado nem acesso a jogos."""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.financial_ledger import FinancialLedger
from app.unified_launcher import available_files, existing_unified_server, resolve_data_dir, ROOT
from unittest.mock import patch
import os

TOKEN = "test-only-registry-token-not-a-real-secret-123456"
ORIGIN = "chrome-extension://" + "a" * 32


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.accounts_file = self.dir / "accounts.json"
        self.ledger_file = self.dir / "financial.sqlite3"
        self.accounts_file.write_text(
            (ROOT / "examples" / "adaptive_accounts_demo.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        FinancialLedger(self.ledger_file).record(
            game="io", profile_id="demo-io", account_id="conta-io",
            asset_name="Item em teste", stage="sold", source="manual",
            gross_gems=100, category="item",
        )
        # Medições locais fictícias para TESTE: nunca carregadas pelo launcher
        # como dados reais do usuário.
        records = json.loads(self.accounts_file.read_text(encoding="utf-8"))
        io = next(item for item in records if item["game"] == "io")
        io["hunts"].append({"id": "area-2", "label": "Segunda área",
                             "unlocked": True, "required_trainer_level": None})
        self.accounts_file.write_text(json.dumps(records), encoding="utf-8")
        self.io_measurements = self.dir / "io_hunt_measurements.json"
        def measure(hunt, xp, source="manual", profile="demo-io"):
            return {"game": "io", "profile_id": profile,
                    "account_id": "conta-io", "pokemon_id": "primeiro",
                    "hunt_id": hunt, "minutes": 60, "xp_gained": xp,
                    "resources_gained": 10, "resources_spent": 1,
                    "defeats": 0, "source": source}
        self.io_measurements.write_text(json.dumps([
            measure("area-1", 100), measure("area-2", 250),
            measure("area-1", 999999, source="demo"),
            measure("area-1", 999999, profile="other")
        ]), encoding="utf-8")
        self.port = unused_port()
        args = [
            sys.executable, "-c",
            "import sys;from pathlib import Path;"
            "import dashboard;from app.tab_registry import Registry;"
            "dashboard.start(Path('examples/sessoes_demo.csv'),int(sys.argv[1]),"
            "Path(sys.argv[3]),None,"
            "Path('examples/pokegrid_snapshots_demo.json'),"
            "Path('examples/world_capture_demo.json'),"
            "registry=Registry(sys.argv[4]),accounts_path=Path(sys.argv[2]),"
            "ivs_path=Path('examples/pokegrid_iv_demo.json'),"
            "io_measurements_path=Path(sys.argv[5]),open_browser=False)",
            str(self.port), str(self.accounts_file), str(self.ledger_file), TOKEN, str(self.io_measurements)
        ]
        self.process = subprocess.Popen(
            args, cwd=ROOT, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(self.stop)
        for _ in range(70):
            if self.process.poll() is not None:
                self.fail("Servidor encerrou: " + self.process.stderr.read())
            try:
                with urlopen(self.url("/api/unified/status"), timeout=0.5) as res:
                    if res.status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(0.04)
        else:
            self.fail("Painel integrado não iniciou")

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process.stderr.close()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path, timeout=2):
        with urlopen(self.url(path), timeout=timeout) as res:
            return json.loads(res.read())

    def test_single_server_exposes_all_safe_modules(self):
        self.assertEqual(self.get("/api/unified/status")["mode"], "unified")
        self.assertTrue(existing_unified_server(self.port))
        self.assertEqual(self.get("/api/tabs")["tabs"], [])
        self.assertEqual(len(self.get("/api/accounts")["accounts"]), 3)
        self.assertTrue(self.get("/api/world-pokegrid")["report"]["is_demo"])
        capture = self.get("/api/world-capture")["report"]
        self.assertTrue(capture["is_demo"])
        self.assertFalse(capture["external_auto_catch_enabled"])
        self.assertEqual(capture["accounts"][0]["allowed_method"], "manual_throw")

    def test_io_hunts_uses_only_matching_manual_measurements(self):
        result = self.get("/api/io/hunts?objective=xp")
        self.assertTrue(result["configured"])
        self.assertFalse(result["identity_verified_live"])
        self.assertEqual(result["execution"], "none")
        self.assertEqual(len(result["comparisons"]), 1)
        ranking = result["comparisons"][0]["ranking"]
        self.assertEqual(ranking["status"], "ranked")
        self.assertEqual(ranking["ranked"][0]["hunt_id"], "area-2")
        first = next(row for row in ranking["ranked"] if row["hunt_id"] == "area-1")
        self.assertEqual(first["xp_per_hour"], 100)
        with self.assertRaises(HTTPError) as error:
            self.get("/api/io/hunts?objective=execute")
        self.assertEqual(error.exception.code, 422)

    def test_only_registered_account_can_get_financial_summary(self):
        summary = self.get("/api/finance?game=io&profile=demo-io&account=conta-io")
        self.assertEqual(summary["summary"]["completed_sale_net_gems"], 85)
        self.assertEqual(summary["summary"]["confirmed_usdt_received"], 0)
        outsider = self.get("/api/finance?game=io&profile=other&account=other")
        self.assertFalse(outsider["configured"])
        no_account = self.get("/api/finance")
        self.assertFalse(no_account["configured"])

    def test_browser_html_and_monitor_page_are_different(self):
        with urlopen(self.url("/"), timeout=2) as res:
            html = res.read().decode("utf-8")
        self.assertIn('id="tabs-grid"', html)
        self.assertIn('id="world-capture-results"', html)
        self.assertIn('id="world-ivs-results"', html)
        self.assertIn("Telemetria IO pela extensão, somente leitura", html)
        self.assertNotIn("Capturas passivas com Playwright", html)
        script = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
        self.assertIn("XP treinador:", script)
        self.assertIn("origem: treinador confirmada", script)
        with urlopen(self.url("/monitor"), timeout=2) as res:
            monitor = res.read().decode("utf-8")
        self.assertIn("/monitor/registry.js", monitor)
        self.assertIn("XP atual/máx.", monitor)
        self.assertIn("table-scroll", monitor)
        with urlopen(self.url("/monitor/registry.js"), timeout=2) as res:
            registry_js = res.read().decode("utf-8")
        self.assertIn("/api/tabs", registry_js)
        self.assertIn("Bloqueado: leitor desatualizado", registry_js)
        self.assertIn("Nenhuma sincronização recebida", registry_js)

    def test_iv_optional_node_runs_in_same_dashboard(self):
        # A primeira execução do Node no runner Linux pode exceder dois
        # segundos; a integração ainda precisa falhar em prazo finito.
        ivs = self.get("/api/world-ivs", timeout=6)
        if shutil.which("node"):
            self.assertTrue(ivs["configured"])
            self.assertEqual(ivs["report"]["source"], "demo")
            self.assertEqual(len(ivs["report"]["pokemon"]), 1)
        else:
            self.assertFalse(ivs["configured"])

    def test_extension_synchronizes_to_unified_port(self):
        body = json.dumps({
            "profile_id": "d57c56d9-6dcb-43e2-8ddf-f2014aa60fb2",
            "profile_label": "Chrome exemplo",
            "tabs": [{"game": "io", "tab_id": 42, "window_id": 9,
                      "title": "Poke Idle IO", "active": False,
                      "route": "app",
                      "telemetry": {"source": "dom", "stats": {
                          "level": 17, "xp_current": 5490,
                          "hp_current": 35, "hp_max": 100,
                      }}}]
        }).encode()
        req = Request(
            self.url("/api/sync"), data=body, method="POST",
            headers={
                "Origin": ORIGIN, "X-IGA-Token": TOKEN,
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=2) as res:
            self.assertEqual(json.loads(res.read())["tab_count"], 1)
        tabs = self.get("/api/tabs")["tabs"]
        self.assertEqual(len(tabs), 1)
        self.assertFalse(tabs[0]["active"])
        self.assertEqual(tabs[0]["telemetry"]["stats"]["level"], 17)
        self.assertEqual(tabs[0]["advice"]["mode"], "dry_run")
        req_bad = Request(
            self.url("/api/sync"), data=body, method="POST",
            headers={
                "Origin": ORIGIN, "X-IGA-Token": "invalid-key",
                "Content-Type": "application/json",
            },
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req_bad, timeout=2)
        self.assertEqual(ctx.exception.code, 401)

    def test_no_financial_or_gameplay_post_routes(self):
        req=Request(self.url("/api/finance"),data=b"{}",method="POST",
                    headers={"Origin": ORIGIN, "X-IGA-Token": TOKEN})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=2)
        self.assertEqual(ctx.exception.code, 403)

    def test_existing_server_not_confused_with_nonunified(self):
        self.assertTrue(existing_unified_server(self.port))

    def test_environment_can_reuse_original_private_data_folder(self):
        old=self.dir/"existing-project"/"data"
        old.mkdir(parents=True)
        (old/"accounts.json").write_text("[]",encoding="utf-8")
        with patch.dict(os.environ,{"IGA_DATA_DIR":str(old)}):
            self.assertEqual(resolve_data_dir(ROOT),old.resolve())
            self.assertEqual(available_files(ROOT)["accounts_path"],old/"accounts.json")
        with patch.dict(os.environ,{"IGA_DATA_DIR":"relative/data"}):
            with self.assertRaises(ValueError):
                resolve_data_dir(ROOT)

    def test_private_options_do_not_load_demo_files_as_real(self):
        empty=self.dir/"empty"
        empty.mkdir()
        # O launcher honra IGA_DATA_DIR no processo real. Isole este cenário
        # para provar o fallback root/data mesmo quando a máquina do usuário
        # já aponta IGA_DATA_DIR para o projeto original.
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(all(x is None for x in available_files(empty).values()))
            data=empty/"data"
            data.mkdir()
            (data/"world_capture.json").write_text("{}",encoding="utf-8")
            available=available_files(empty)
            self.assertEqual(available["world_capture_path"],data/"world_capture.json")
            self.assertIsNone(available["ivs_path"])


if __name__ == "__main__":
    unittest.main()
