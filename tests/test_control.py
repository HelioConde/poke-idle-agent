import unittest

from app.control import ActionRequest, DryRunExecutor, RiskManager


class ControlTests(unittest.TestCase):
    def test_simulation_action_is_planned_not_executed(self):
        result = DryRunExecutor().execute(ActionRequest("simulated", "gather", {}))
        self.assertTrue(result.accepted)
        self.assertFalse(result.executed)

    def test_real_games_have_no_actions_enabled(self):
        executor = DryRunExecutor()
        for game in ("io", "world"):
            result = executor.execute(ActionRequest(game, "navigate_menu", {}))
            self.assertFalse(result.accepted)
            self.assertFalse(result.executed)

    def test_real_mode_is_always_disabled(self):
        result = DryRunExecutor().execute(
            ActionRequest("simulated", "gather", {}, mode="real"))
        self.assertFalse(result.accepted)
        self.assertIn("desabilitado", result.reason)

    def test_emergency_stop_and_rate_limit_block_plans(self):
        risk = RiskManager(max_actions_per_minute=1)
        executor = DryRunExecutor(risk)
        self.assertTrue(executor.execute(ActionRequest("simulated", "rest", {})).accepted)
        self.assertFalse(executor.execute(ActionRequest("simulated", "rest", {})).accepted)
        risk.emergency_stop()
        result = executor.execute(ActionRequest("simulated", "rest", {}))
        self.assertFalse(result.accepted)
        self.assertIn("emergência", result.reason)


if __name__ == "__main__":
    unittest.main()
