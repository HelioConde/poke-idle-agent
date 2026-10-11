import unittest
from pathlib import Path
from app.agent import IdleSandbox, choose_action, run
from app.decision import rank_hunts
from app.lab import Session, aggregate, load_sessions

ROOT = Path(__file__).resolve().parents[1]

class MetricsTests(unittest.TestCase):
    def test_data_demo(self):
        data = aggregate(load_sessions(ROOT / "examples" / "sessoes_demo.csv"))
        self.assertEqual({x["game"] for x in data}, {"world", "io"})
        self.assertTrue(all(x["source"] == "DEMONSTRAÇÃO" for x in data))

    def test_cashout_demo_never_counts(self):
        row = dict(game="io", minutes="60", xp="1", coins="1", gems_received_net="1000",
                   listings="1", sales="1", withdrawn_usd="7", operating_cost_brl="0", source="demo")
        data = aggregate([Session.from_row(row)])[0]
        self.assertEqual(data["withdrawn_usd"], 0)
        self.assertEqual(data["indicative_io_gems_usd"], 7)

    def test_world_conversion_unknown(self):
        data = aggregate(load_sessions(ROOT / "examples" / "sessoes_demo.csv"))
        self.assertIsNone(data[0]["indicative_io_gems_usd"])

    def test_reject_negative_duration(self):
        row = dict(game="io", minutes="0", xp="1", coins="1", gems_received_net="0",
                   listings="0", sales="0", withdrawn_usd="0", operating_cost_brl="0")
        with self.assertRaises(ValueError):
            Session.from_row(row)

    def test_reject_more_sales_than_listings(self):
        row = dict(game="io", minutes="5", xp="1", coins="1", gems_received_net="0",
                   listings="0", sales="1", withdrawn_usd="0", operating_cost_brl="0")
        with self.assertRaises(ValueError):
            Session.from_row(row)

    def test_hunt_low_risk(self):
        rows = [dict(game="io", hunt="arriscada", xp_per_hour="10000", estimated_gems_per_hour="0", failure_probability=".9", confidence=".5"),
                dict(game="io", hunt="segura", xp_per_hour="9000", estimated_gems_per_hour="0", failure_probability="0", confidence=".9")]
        self.assertEqual(rank_hunts(rows)[0]["hunt"], "segura")

    def test_hunt_reject_risk(self):
        with self.assertRaises(ValueError):
            rank_hunts([dict(game="io", hunt="ruim", xp_per_hour="10", estimated_gems_per_hour="0", failure_probability="2", confidence=".2")])

class SandboxTests(unittest.TestCase):
    def test_cycle_generates_coins(self):
        result = run(20)
        self.assertEqual(result["environment"], "local_sandbox_only")
        self.assertGreater(result["summary"]["coins"], 0)
        self.assertEqual(len(result["events"]), 20)

    def test_invalid_actions(self):
        with self.assertRaises(ValueError):
            IdleSandbox().act("withdraw")

    def test_rest_when_tired(self):
        game = IdleSandbox()
        for _ in range(4): game.act("gather")
        game.act("sell")
        self.assertEqual(choose_action(game.observe()), "rest")

    def test_invalid_steps(self):
        with self.assertRaises(ValueError): run(0)

if __name__ == "__main__":
    unittest.main()
