"""Fila consultiva IO: nunca gera comandos reais nem dados inventados."""
import unittest

from app.io_advisory import build_io_advisory


class IOAdvisoryTests(unittest.TestCase):
    def test_low_hp_and_unknown_farm_get_supervised_alerts(self):
        items = build_io_advisory(
            {"hp_current": 10, "hp_max": 100},
            {}, {"farm_state": "unknown"})
        self.assertEqual(items[0]["kind"], "review_health")
        self.assertEqual(items[0]["priority"], "high")
        self.assertIn("Desistir", items[0]["message"])
        self.assertIn("confirm_farm", [item["kind"] for item in items])
        self.assertTrue(all(item["action_authorized"] is False for item in items))

    def test_short_term_decline_only_advises_manual_review(self):
        items = build_io_advisory(
            {"level": 33}, {"5m": 350, "15m": 1100},
            {"farm_state": "active"})
        self.assertEqual(items[0]["kind"], "investigate_xp_drop")
        self.assertEqual(items[0]["status"], "review_only")
        self.assertIn("não trocar hunt automaticamente", items[0]["message"])

    def test_without_mature_data_no_change_to_hunt(self):
        items = build_io_advisory(
            {"level": 33}, {"5m": 1000}, {"farm_state": "active"})
        self.assertEqual(items[0]["kind"], "collect_longer_window")
        self.assertIn("verify_hunt_manually", [item["kind"] for item in items])

    def test_invalid_or_missing_numbers_do_not_trigger_false_decline(self):
        for value in (float("nan"), float("inf"), None, "500", -1):
            with self.subTest(value=value):
                result = build_io_advisory(
                    {}, {"5m": value, "15m": 2000},
                    {"farm_state": "active"})
                self.assertNotIn("investigate_xp_drop",
                                 [item["kind"] for item in result])

    def test_does_not_grant_permissions_or_compose_live_commands(self):
        items = build_io_advisory(
            {}, {"5m": 100, "15m": 1000}, {"farm_state": "active"})
        self.assertLessEqual(len(items), 3)
        self.assertTrue(all(set(item) == {
            "kind", "priority", "status", "message", "action_authorized"
        } for item in items))
        self.assertFalse(any(item["action_authorized"] for item in items))


if __name__ == "__main__":
    unittest.main()
