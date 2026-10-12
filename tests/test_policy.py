import unittest

from app.policy import action_policy


class PolicyTests(unittest.TestCase):
    def test_io_actions_are_dry_run_only_until_validated(self):
        policy = action_policy("io", "select_hunt")
        self.assertTrue(policy.dry_run_allowed)
        self.assertFalse(policy.real_enabled)

    def test_financial_actions_require_confirmation_or_are_refused(self):
        self.assertTrue(action_policy("io", "market_list").requires_confirmation)
        withdraw = action_policy("io", "withdraw")
        self.assertFalse(withdraw.dry_run_allowed)
        self.assertFalse(withdraw.real_enabled)

    def test_world_has_no_external_action_policy(self):
        self.assertIsNone(action_policy("world", "select_hunt"))


if __name__ == "__main__":
    unittest.main()
