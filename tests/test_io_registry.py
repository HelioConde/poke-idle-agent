"""Testes da integracao IO sem abrir navegador ou usar conta real."""
import unittest
from unittest.mock import patch

from app.tab_registry import Registry

PROFILE = "d57c56d9-6dcb-43e2-8ddf-f2014aa60fb2"


def payload(xp=100, game="io"):
    return {
        "profile_id": PROFILE, "profile_label": "Principal",
        "tabs": [{
            "game": game, "tab_id": 10, "window_id": 20,
            "title": "Pokeidle", "active": False,
            "telemetry": {
                "source": "dom",
                "stats": {"level": 12, "xp_current": xp,
                          "hp_current": 25, "hp_max": 100}
            }
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


if __name__ == "__main__":
    unittest.main()
