import math
import unittest
from app.io_telemetry import dry_run_decision, measured_xp_per_hour, sanitize, sanitize_observation

class IoTelemetryTests(unittest.TestCase):
    def test_empty_dom_read_is_not_fabricated(self):
        self.assertEqual(sanitize({"source": "dom", "stats": {}})["available"], False)
        self.assertEqual(dry_run_decision({})["action"], "observe")

    def test_valid_numbers(self):
        stats = sanitize({"source": "dom", "stats": {"level": 40, "hp_current": 21, "hp_max": 100}})
        self.assertEqual(stats["stats"]["level"], 40)
        self.assertEqual(dry_run_decision(stats["stats"])["action"], "review_health")

    def test_unauthorized_data_rejected(self):
        for sample in (
            {"source": "dom", "stats": {"session_token": "secret"}},
            {"source": "dom", "stats": {"email": 32}},
            {"source": "dom", "stats": {"xp_current": math.nan}},
            {"source": "dom", "stats": {"gems": -1}},
            {"source": "dom", "stats": {"coins": True}},
            {"source": "websocket", "stats": {"coins": 10}},
        ):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                sanitize(sample)

    def test_xp_rate_only_same_level_with_valid_progress(self):
        past = {"level": 14, "xp_current": 100}
        self.assertEqual(measured_xp_per_hour(past, {"level": 14, "xp_current": 150}, 60), 3000)
        self.assertIsNone(measured_xp_per_hour(past, {"level": 15, "xp_current": 12}, 60))
        self.assertIsNone(measured_xp_per_hour(past, {"level": 14, "xp_current": 5}, 60))
        self.assertIsNone(measured_xp_per_hour(past, {"level": 14, "xp_current": 130}, 2))


    def test_diagnostic_xp_ambiguity_is_only_count_not_private_text(self):
        payload = {"status": "metrics", "canvas": 9, "iframes": 0,
                   "candidates": 99, "xp_candidates": 2, "xp_ambiguous": True}
        self.assertEqual(sanitize_observation(payload), payload)
        old = {k: payload[k] for k in ("status", "canvas", "iframes", "candidates")}
        self.assertEqual(sanitize_observation(old), old)
        for corrupted in (
            dict(payload, xp_ambiguous=False),
            dict(payload, xp_candidates="2"),
            dict(payload, xp_candidates=21),
            dict(payload, raw_xp="7.346 / 15.400 xp"),
            dict(payload, xp_ambiguous="true"),
        ):
            with self.subTest(corrupted=corrupted), self.assertRaises(ValueError):
                sanitize_observation(corrupted)

    def test_no_action_is_executed(self):
        rec = dry_run_decision({"hp_current": 5, "hp_max": 100})
        self.assertEqual(rec["mode"], "dry_run")
        self.assertNotIn(rec["action"], {"click", "buy", "withdraw", "sell"})

    def test_decision_is_explainable_and_verifiable(self):
        rec = dry_run_decision({"level": 2, "xp_current": 5}, 300)
        for key in ("objective", "data_used", "confidence", "risk",
                    "preconditions", "expected_result", "verification_plan",
                    "permission_required"):
            self.assertIn(key, rec)
        self.assertEqual(rec["action"], "track_farm")
