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
                            "xp_trainer_scoped": True}
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
            "iframes": 0, "candidates": 0}
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
        self.assertEqual(registry.snapshot()["tabs"][0]["observation"]["canvas"], 2)
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
            "iframes": 0, "candidates": 0}
        with patch("app.tab_registry.time.monotonic", return_value=180):
            registry.ingest(row)
            self.assertIsNone(registry.snapshot()["tabs"][0]["xp_per_hour"])
