"""Fluxo completo: escolher mapa -> farm -> gestão -> mercado sem tocar no jogo."""
import unittest

from app.adaptive_strategy import Account, Measurement
from app.io_action_engine import ActionRequest, Engine, FakeIOAdapter, Policy
from app.io_operation_planner import MarketAssessment, plan_farm, plan_market


class FullDryRunAndSimulationTests(unittest.TestCase):
    def setUp(self):
        self.account=Account.parse({
            "game":"io","profile_id":"demo","account_id":"demo",
            "trainer_level":12,
            "roster":[{"id":"poke1","species":"Pokémon arbitrário","level":12,
                       "hp":50,"max_hp":50}],
            "active_pokemon_id":"poke1",
            "hunts":[{"id":"forest","label":"Hunt A","unlocked":True},
                     {"id":"lake","label":"Hunt B","unlocked":True}]
        })
        self.measurements=[
            Measurement.parse({"game":"io","profile_id":"demo","account_id":"demo",
                 "pokemon_id":"poke1","hunt_id":"forest","minutes":60,
                 "xp_gained":100,"resources_gained":100,"resources_spent":0,
                 "defeats":0,"source":"manual"}),
            Measurement.parse({"game":"io","profile_id":"demo","account_id":"demo",
                 "pokemon_id":"poke1","hunt_id":"lake","minutes":60,
                 "xp_gained":500,"resources_gained":500,"resources_spent":0,
                 "defeats":0,"source":"manual"})
        ]
        self.adapter=FakeIOAdapter()
        self.engine=Engine(Policy(max_spend_gems=50,max_listing_gems=100))

    def test_farming_flow_replans_after_verified_simulated_action(self):
        plan1=plan_farm(self.account,self.adapter.observe(),self.measurements,"one")
        self.assertEqual(plan1.action.kind,"select_hunt")
        self.assertEqual(self.engine.execute(plan1.action,self.adapter,"dry_run")["status"],"dry_run")
        self.assertEqual(self.adapter.observe().hunt_id,"starter")
        self.assertEqual(self.engine.execute(plan1.action,self.adapter,"simulation")["status"],"simulated")
        plan2=plan_farm(self.account,self.adapter.observe(),self.measurements,"two")
        self.assertEqual(plan2.action.kind,"start_farm")
        self.assertEqual(self.engine.execute(plan2.action,self.adapter,"simulation")["status"],"simulated")
        plan3=plan_farm(self.account,self.adapter.observe(),self.measurements,"three")
        self.assertEqual(plan3.status,"monitor")
        self.assertTrue(self.adapter.observe().farming)

    def test_market_flow_listing_not_income_and_buy_only_with_cap(self):
        assessment=MarketAssessment("stone",3,50,True,True,True)
        proposal=plan_market(self.account,self.adapter.observe(),"list",assessment,"publish_listing")
        self.assertEqual(proposal.status,"needs_human_approval")
        before=self.adapter.observe()
        dry=self.engine.execute(proposal.action,self.adapter)
        self.assertEqual(dry["status"],"dry_run")
        self.assertEqual(self.adapter.observe(),before)
        sim=self.engine.execute(proposal.action,self.adapter,"simulation")
        self.assertEqual(sim["status"],"simulated")
        after=self.adapter.observe()
        self.assertEqual(after.listings["stone"],1)
        self.assertEqual(after.gems_balance,200)  # Anúncio NÃO é venda.
        buy=plan_market(self.account,self.adapter.observe(),"buy",assessment,"buy_item")
        self.assertEqual(buy.status,"needs_human_approval")
        self.assertEqual(self.engine.execute(buy.action,self.adapter,"simulation")["status"],"simulated")
        self.assertEqual(self.adapter.observe().gems_balance,150)
        self.assertNotIn("withdrawn_usdt",str(self.engine.history))

    def test_wrong_account_never_acts(self):
        other=Account.parse({
            "game":"io","profile_id":"other","account_id":"demo",
            "trainer_level":1,"roster":[],"active_pokemon_id":None,"hunts":[]})
        with self.assertRaises(PermissionError):
            plan_farm(other,self.adapter.observe(),self.measurements,"wrong")

    def test_world_action_rejected_even_with_synthetic_data(self):
        with self.assertRaises(PermissionError):
            ActionRequest("id","world","demo","demo","start_farm")


if __name__ == "__main__":
    unittest.main()
