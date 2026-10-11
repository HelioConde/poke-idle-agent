import unittest

from app.farm_telemetry import FarmSample, overkill_evidence, summarize


class FarmTelemetryTests(unittest.TestCase):
    def test_measures_rates_from_counter_deltas(self):
        samples = [
            FarmSample(100, xp_total=100, coins_total=10, kills_total=2,
                       damage_taken_total=4, healing_used_total=1),
            FarmSample(160, xp_total=160, coins_total=25, kills_total=5,
                       damage_taken_total=10, healing_used_total=3),
        ]
        result = summarize(samples)
        self.assertEqual(result["xp_per_hour"], 3600)
        self.assertEqual(result["coins_per_hour"], 900)
        self.assertEqual(result["kills_per_minute"], 3)
        self.assertEqual(result["damage_taken"], 6)

    def test_unknown_counters_stay_unknown(self):
        result = summarize([FarmSample(1), FarmSample(61)])
        self.assertIsNone(result["xp_per_hour"])
        self.assertIsNone(result["items_found"])

    def test_rejects_non_monotonic_samples(self):
        with self.assertRaises(ValueError):
            summarize([FarmSample(60), FarmSample(60)])
        with self.assertRaises(ValueError):
            summarize([FarmSample(1, xp_total=-1), FarmSample(2, xp_total=1)])

    def test_overkill_requires_events_and_uses_respawn_config(self):
        self.assertIsNone(overkill_evidence([1, 2], 3)["overkill"])
        evidence = overkill_evidence([1, 3, 5, 7], 2)
        self.assertEqual(evidence["status"], "measured")
        self.assertTrue(evidence["overkill"])


if __name__ == "__main__":
    unittest.main()
