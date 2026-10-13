"""Testes da integracao IO sem abrir navegador ou usar conta real."""
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from app.tab_registry import Registry

PROFILE = "d57c56d9-6dcb-43e2-8ddf-f2014aa60fb2"


def payload(xp=100, game="io"):
    return {
        "profile_id": PROFILE, "profile_label": "Principal",
        "tabs": [{
            "game": game, "tab_id": 10, "window_id": 20,
            "title": "Pokeidle", "active": False,
            **({"route": "app"} if game == "io" else {}),
            "telemetry": {
                "source": "dom",
                "stats": {"level": 12, "xp_current": xp,
                          "hp_current": 25, "hp_max": 100}
            },
            "observation": {"status": "metrics", "canvas": 0,
                            "iframes": 0, "candidates": 5,
                            "xp_candidates": 1, "xp_ambiguous": False,
                            "xp_trainer_scoped": True, "xp_reason": "trainer_xp_scoped",
                            "telemetry_protocol": 2, "reader_version": "trainer-xp-scoped-v1",
                            "content_state": "responded"}
        }]
    }


class RegistryTelemetryTests(unittest.TestCase):
    def test_inactive_io_tab_receives_stats(self):
        reg = Registry("test-token")
        with patch("app.tab_registry.time.monotonic", return_value=100):
            reg.ingest(payload())
            row = reg.snapshot()["tabs"][0]
        self.assertFalse(row["active"])
        self.assertEqual(row["telemetry"]["stats"]["xp_current"], 100)
        self.assertEqual(row["advice"]["mode"], "dry_run")
        self.assertEqual(row["xp_per_hour"], None)

    def test_measured_xp_rate(self):
        reg = Registry("test-token")
        with patch("app.tab_registry.time.monotonic", return_value=100):
            reg.ingest(payload(xp=100))
        with patch("app.tab_registry.time.monotonic", return_value=160):
            reg.ingest(payload(xp=150))
            row = reg.snapshot()["tabs"][0]
        self.assertEqual(row["xp_per_hour"], 3000)
        self.assertEqual(row["advice"]["action"], "track_farm")

    def test_rolling_rates_require_sufficient_real_observation_time(self):
        registry = Registry("test-token")
        # 61 amostras em uma hora simulada: a janela de 60m não aparece
        # antes de cobrir 80% da duração solicitada.
        for minute in range(61):
            with patch("app.tab_registry.time.monotonic", return_value=100 + minute * 60):
                registry.ingest(payload(xp=100 + minute * 10))
                tab = registry.snapshot()["tabs"][0]
                rates = tab["xp_windows"]
                last_rate = tab["xp_per_hour"]
            if minute < 4:
                self.assertNotIn("5m", rates)
            if minute < 12:
                self.assertNotIn("15m", rates)
            if minute < 48:
                self.assertNotIn("60m", rates)
        self.assertEqual(rates, {"5m": 600, "15m": 600, "60m": 600})
        self.assertEqual(last_rate, 600)

    def test_rolling_rates_reset_on_xp_loss_and_level_change(self):
        registry = Registry("test-token")
        for minute in range(5):
            with patch("app.tab_registry.time.monotonic", return_value=100 + minute * 60):
                registry.ingest(payload(xp=100 + minute * 10))
        with patch("app.tab_registry.time.monotonic", return_value=401):
            registry.ingest(payload(xp=80))
            result = registry.snapshot()["tabs"][0]
        self.assertIsNone(result["xp_per_hour"])
        self.assertEqual(result["xp_windows"], {})
        progressed = payload(xp=150)
        progressed["tabs"][0]["telemetry"]["stats"]["level"] = 13
        with patch("app.tab_registry.time.monotonic", return_value=461):
            registry.ingest(progressed)
            result = registry.snapshot()["tabs"][0]
        self.assertIsNone(result["xp_per_hour"])
        self.assertEqual(result["xp_windows"], {})

    def test_rolling_rates_do_not_mix_different_chrome_windows(self):
        registry = Registry("test-token")
        with patch("app.tab_registry.time.monotonic", return_value=100):
            registry.ingest(payload(100))
        double = payload(150)
        another = payload(900)["tabs"][0]
        another["window_id"] = 21
        double["tabs"].append(another)
        with patch("app.tab_registry.time.monotonic", return_value=160):
            registry.ingest(double)
            rows = registry.snapshot()["tabs"]
        by_window = {tab["window_id"]: tab for tab in rows}
        self.assertEqual(by_window[20]["xp_per_hour"], 3000)
        self.assertIsNone(by_window[21]["xp_per_hour"])
        self.assertEqual(by_window[21]["xp_windows"], {})

    def test_disappearing_tab_clears_historical_window(self):
        registry = Registry("test-token")
        with patch("app.tab_registry.time.monotonic", return_value=100):
            registry.ingest(payload(100))
        missing = payload()
        missing["tabs"] = []
        with patch("app.tab_registry.time.monotonic", return_value=110):
            registry.ingest(missing)
        with patch("app.tab_registry.time.monotonic", return_value=160):
            registry.ingest(payload(200))
            result = registry.snapshot()["tabs"][0]
        self.assertIsNone(result["xp_per_hour"])
        self.assertEqual(result["xp_windows"], {})

    def test_hunt_hint_reaches_registry_without_creating_action(self):
        registry = Registry("test-token")
        item = payload()
        item["tabs"][0]["io_audit"] = {
            "route": "app", "farm_state": "active", "map_state": "closed",
            "hunt_hint": {"status": "matching_displays", "label": "Larvitar",
                          "level": 30, "source": "both"},
            "controls": {"surrender": {
                "selector": "#eco-desistir", "present": True,
                "enabled": True, "policy": "permanently_blocked"}}}
        registry.ingest(item)
        row = registry.snapshot()["tabs"][0]
        self.assertEqual(row["io_audit"]["hunt_hint"]["label"], "Larvitar")
        self.assertEqual(row["io_audit"]["controls"]["surrender"]["policy"],
                         "permanently_blocked")
        self.assertEqual(row["advice"]["mode"], "dry_run")
        self.assertTrue(all(not entry["action_authorized"]
                            for entry in row["advisory_queue"]))

    def test_legacy_extension_xp_cannot_be_used_as_trainer(self):
        reg = Registry("test-token")
        data = payload(xp=100)
        del data["tabs"][0]["observation"]
        with patch("app.tab_registry.time.monotonic", return_value=100):
            reg.ingest(data)
        data["tabs"][0]["telemetry"]["stats"]["xp_current"] = 200
        with patch("app.tab_registry.time.monotonic", return_value=160):
            reg.ingest(data)
            row = reg.snapshot()["tabs"][0]
        self.assertNotIn("xp_current", row["telemetry"]["stats"])
        self.assertIsNone(row["xp_per_hour"])
        self.assertEqual(row["observation"]["status"], "legacy_protocol")

    def test_partial_old_diagnostic_is_normalized_as_legacy(self):
        reg = Registry("test-token")
        data = payload()
        data["tabs"][0]["observation"] = {
            "status": "metrics", "canvas": 0, "iframes": 0, "candidates": 5,
        }
        reg.ingest(data)
        row = reg.snapshot()["tabs"][0]
        self.assertEqual(row["observation"]["status"], "legacy_protocol")
        self.assertNotIn("xp_current", row["telemetry"]["stats"])

    def test_scoped_xp_without_current_protocol_cannot_be_used(self):
        reg = Registry("test-token")
        data = payload(xp=100)
        for key in ("telemetry_protocol", "reader_version", "content_state"):
            del data["tabs"][0]["observation"][key]
        reg.ingest(data)
        row = reg.snapshot()["tabs"][0]
        self.assertNotIn("xp_current", row["telemetry"]["stats"])

    def test_unscoped_pokemon_xp_does_not_produce_trainer_rate(self):
        reg = Registry("test-token")
        data = payload(xp=100)
        data["tabs"][0]["observation"] = {
            "status":"metrics", "canvas":9, "iframes":0,
            "candidates":99, "xp_candidates":2,
            "xp_ambiguous":True, "xp_trainer_scoped":False}
        with patch("app.tab_registry.time.monotonic", return_value=100):
            reg.ingest(data)
        data["tabs"][0]["telemetry"]["stats"]["xp_current"] = 150
        with patch("app.tab_registry.time.monotonic", return_value=160):
            reg.ingest(data)
            row = reg.snapshot()["tabs"][0]
        self.assertNotIn("xp_current", row["telemetry"]["stats"])
        self.assertIsNone(row["xp_per_hour"])

    def test_game_world_cannot_ingest_account_telemetry(self):
        reg = Registry("test-token")
        with self.assertRaises(ValueError):
            reg.ingest(payload(game="world"))

    def test_sensitive_keys_rejected_by_server(self):
        reg = Registry("test-token")
        item = payload()
        item["tabs"][0]["telemetry"]["stats"]["token"] = "hidden"
        with self.assertRaises(ValueError):
            reg.ingest(item)

    def test_io_with_canvas_has_no_fabricated_statistics(self):
        reg = Registry("test-token")
        item = payload()
        item["tabs"][0]["telemetry"]["stats"] = {}
        reg.ingest(item)
        row = reg.snapshot()["tabs"][0]
        self.assertEqual(row["telemetry"]["available"], False)
        self.assertEqual(row["advice"]["action"], "observe")
        self.assertIsNone(row["xp_per_hour"])

    def test_landing_cannot_submit_hud_telemetry(self):
        reg = Registry("test-token")
        item = payload()
        item["tabs"][0]["route"] = "landing"
        with self.assertRaises(ValueError):
            reg.ingest(item)

    def test_invalid_io_route_rejected(self):
        reg = Registry("test-token")
        item = payload()
        item["tabs"][0]["route"] = "https://pokeidle.io/app?secret"
        with self.assertRaises(ValueError):
            reg.ingest(item)

    def test_normalized_io_observation_is_persisted(self):
        memory = Mock()
        reg = Registry("test-token", memory)
        reg.ingest(payload())
        stored = memory.record_observation.call_args.kwargs
        self.assertEqual(stored["game"], "io")
        self.assertEqual(stored["session_id"], "20:10")
        self.assertEqual(stored["state"]["stats"]["level"], 12)
        self.assertEqual(stored["decision"]["mode"], "dry_run")


if __name__ == "__main__":
    unittest.main()


class DiagnosticTests(unittest.TestCase):
    def test_reports_failed_reader(self):
        row = payload()
        row["tabs"][0].pop("telemetry")
        row["tabs"][0]["observation"] = {
            "status": "reader_unavailable", "canvas": 0,
            "iframes": 0, "candidates": 0, "xp_candidates": 0,
            "xp_ambiguous": False, "xp_trainer_scoped": False,
            "xp_reason": "reader_unavailable", "telemetry_protocol": 2,
            "reader_version": "unknown", "content_state": "unavailable"}
        registry = Registry("test")
        registry.ingest(row)
        tab = registry.snapshot()["tabs"][0]
        self.assertEqual(tab["observation"]["status"], "reader_unavailable")
        self.assertIsNone(tab["xp_per_hour"])

    def test_diagnostics_reject_privacy_leaks(self):
        row = payload()
        row["tabs"][0]["observation"] = {
            "status": "no_matches", "canvas": 2,
            "iframes": 1, "candidates": 100}
        registry = Registry("test")
        registry.ingest(row)
        self.assertEqual(registry.snapshot()["tabs"][0]["observation"]["status"], "legacy_protocol")
        row["tabs"][0]["observation"]["url"] = "/app?token=secret"
        with self.assertRaises(ValueError):
            registry.ingest(row)

    def test_world_rejects_observation(self):
        row = payload(game="world")
        row["tabs"][0].pop("telemetry")
        row["tabs"][0]["observation"] = {
            "status": "landing", "canvas": 0, "iframes": 0, "candidates": 0}
        with self.assertRaises(ValueError):
            Registry("test").ingest(row)

    def test_rate_invalidated_when_reader_stops(self):
        registry = Registry("test")
        with patch("app.tab_registry.time.monotonic", return_value=100):
            registry.ingest(payload(10))
        with patch("app.tab_registry.time.monotonic", return_value=160):
            registry.ingest(payload(20))
        row = payload()
        row["tabs"][0].pop("telemetry")
        row["tabs"][0]["observation"] = {
            "status": "reader_unavailable", "canvas": 0,
            "iframes": 0, "candidates": 0, "xp_candidates": 0,
            "xp_ambiguous": False, "xp_trainer_scoped": False,
            "xp_reason": "reader_unavailable", "telemetry_protocol": 2,
            "reader_version": "unknown", "content_state": "unavailable"}
        with patch("app.tab_registry.time.monotonic", return_value=180):
            registry.ingest(row)
            self.assertIsNone(registry.snapshot()["tabs"][0]["xp_per_hour"])
