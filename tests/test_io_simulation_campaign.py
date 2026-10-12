"""Integração de longa duração: planejador + simulador + executor + memória."""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.io_action_engine import ActionRequest, Engine, FakeIOAdapter, Policy
from app.io_simulation import run_campaign


class SimulationCampaignTests(unittest.TestCase):
    def test_one_hundred_virtual_cycles_learn_without_replaying_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run_campaign(100, Path(directory) / "completed.json")
        self.assertEqual(report["environment"], "local_simulation_only")
        self.assertEqual(report["cycles"], 100)
        self.assertEqual(report["history_records"], 100)
        self.assertGreaterEqual(report["proposed"], 12)
        self.assertGreaterEqual(report["simulated"], 12)
        self.assertGreaterEqual(report["blocked"], 3)
        self.assertGreater(report["monitored"], 70)
        self.assertTrue(report["final_farming"])
        self.assertFalse(report["engine_emergency"])

    def test_unknown_postcondition_stops_simulation_instead_of_claiming_success(self):
        class NoChange(FakeIOAdapter):
            def perform(self, request):
                return None

        adapter = NoChange("p", "a")
        request = ActionRequest("once", "io", "p", "a", "start_farm")
        result = Engine().execute(request, adapter, mode="simulation")
        self.assertEqual(result["status"], "uncertain")

    def test_faults_do_not_cross_account_boundary_or_enable_live_actions(self):
        class ClaimedRealAdapter(FakeIOAdapter):
            is_simulation = False

        adapter = ClaimedRealAdapter("p", "a")
        request = ActionRequest("live-claim", "io", "p", "a", "start_farm")
        result = Engine(Policy(max_actions=10)).execute(request, adapter, mode="live")
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(adapter.observe().farming)

        wrong = ActionRequest("wrong-account", "io", "p", "other", "start_farm")
        result = Engine().execute(wrong, FakeIOAdapter("p", "a"), mode="simulation")
        self.assertEqual(result["status"], "blocked")

    def test_duplicate_request_is_never_simulated_twice(self):
        adapter = FakeIOAdapter("p", "a")
        engine = Engine()
        request = ActionRequest("duplicate", "io", "p", "a", "start_farm")
        self.assertEqual(engine.execute(request, adapter, mode="simulation")["status"], "simulated")
        self.assertEqual(engine.execute(request, adapter, mode="simulation")["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
