import unittest

from app.adaptive_strategy import Account, Measurement
from app.io_action_engine import ObservedIO, Engine, Policy, FakeIOAdapter
from app.io_operation_planner import (
    EvolutionAssessment, MarketAssessment, plan_farm, plan_inventory,
    plan_market, plan_evolution, plan_next, plan_pokemon
)


def make_account(profile="demo", account_id="demo", game="io", pokemon="any-pokemon"):
    return Account.parse({
        "game":game,"profile_id":profile,"account_id":account_id,"trainer_level":12,
        "roster":[{"id":"poke1","species":pokemon,"level":20,"hp":100,"max_hp":100}],
        "active_pokemon_id":"poke1",
        "hunts":[{"id":"h1","label":"Hunt A","unlocked":True},
                 {"id":"h2","label":"Hunt B","unlocked":True},
                 {"id":"locked","label":"Hunt fechada","unlocked":False}]}
    )


def metric(area, xp, gain, profile="demo", account_id="demo",
           pokemon_id="poke1", source="manual"):
    return Measurement.parse({
        "game":"io","profile_id":profile,"account_id":account_id,
        "pokemon_id":pokemon_id,"hunt_id":area,"minutes":60,
        "xp_gained":xp,"resources_gained":gain,
        "resources_spent":0,"defeats":0,"source":source
    })


def state(hunt="h1", farming=False, profile="demo", account_id="demo",
          inventory=None):
    return ObservedIO("io",profile,account_id,hunt,farming,inventory or {},{}, {},100)


class FarmPlannerTests(unittest.TestCase):
    def setUp(self):
        self.account=make_account()
        self.rows=[metric("h1",1000,20),metric("h2",200,100)]

    def test_pick_best_for_resources(self):
        p=plan_farm(self.account,state(),self.rows,"request-1","resources")
        self.assertEqual(p.status,"proposed")
        self.assertEqual(p.action.kind,"select_hunt")
        self.assertEqual(p.action.target_id,"h2")

    def test_pick_best_for_xp(self):
        p=plan_farm(self.account,state("h2"),self.rows,"request-2","xp")
        self.assertEqual(p.action.target_id,"h1")

    def test_stop_farm_before_changing_hunt(self):
        p=plan_farm(self.account,state(farming=True),self.rows,"request-3","resources")
        self.assertEqual(p.action.kind,"stop_farm")
        self.assertEqual(p.evidence["recommended_hunt_id"],"h2")

    def test_start_on_best_hunt(self):
        p=plan_farm(self.account,state(hunt="h2"),self.rows,"request-4","resources")
        self.assertEqual(p.action.kind,"start_farm")

    def test_monitor_if_already_correct(self):
        p=plan_farm(self.account,state(hunt="h2",farming=True),self.rows,"request-5","resources")
        self.assertEqual(p.status,"monitor")
        self.assertIsNone(p.action)

    def test_never_pick_hunt_from_demo(self):
        p=plan_farm(self.account,state(),[metric("h1",100,50,source="demo"),
                                           metric("h2",200,100,source="demo")],
                    "request-6","resources")
        self.assertEqual(p.status,"need_data")
        self.assertIsNone(p.action)

    def test_monetization_needs_market_sales(self):
        p=plan_farm(self.account,state(),self.rows,"request-7","monetization")
        self.assertEqual(p.status,"need_data")
        self.assertIsNone(p.action)

    def test_cannot_mix_other_account_results(self):
        measurements=[metric("h1",100,50,profile="another"),
                      metric("h2",200,100,profile="another")]
        p=plan_farm(self.account,state(),measurements,"request-8")
        self.assertEqual(p.status,"need_data")

    def test_cannot_mix_another_pokemon_results(self):
        measurements=[metric("h1",100,50,pokemon_id="other"),
                      metric("h2",200,100,pokemon_id="other")]
        p=plan_farm(self.account,state(),measurements,"request-9")
        self.assertEqual(p.status,"need_data")

    def test_low_hp_priority(self):
        self.account=Account.parse({
            "game":"io","profile_id":"demo","account_id":"demo","trainer_level":12,
            "roster":[{"id":"poke1","species":"Caterpie","level":3,"hp":10,"max_hp":100}],
            "active_pokemon_id":"poke1","hunts":[{"id":"h1","label":"A","unlocked":True},
                                                  {"id":"h2","label":"B","unlocked":True}]
        })
        p=plan_farm(self.account,state(farming=True),self.rows,"req-low-hp")
        self.assertEqual(p.action.kind,"stop_farm")

    def test_unknown_farm_state_never_acts(self):
        p=plan_farm(self.account,state(hunt="h2",farming=None),self.rows,"req-none","resources")
        self.assertEqual(p.status,"need_data")

    def test_world_is_never_operated(self):
        a=make_account(game="world")
        with self.assertRaises(PermissionError):
            plan_farm(a,state(),self.rows,"request-world")

    def test_account_mismatch_rejected(self):
        with self.assertRaises(PermissionError):
            plan_farm(self.account,state(profile="another"),self.rows,"mismatch")

    def test_plan_next_is_generic_not_species_specific(self):
        c=make_account(pokemon="Squirtle")
        a=plan_next(c,state(),self.rows,"req-1")
        self.assertEqual(a.action.target_id,"h2")


class InventoryEvolutionTests(unittest.TestCase):
    def setUp(self):
        self.account=make_account(pokemon="Bulbasaur")
        self.state=state(inventory={"stone":2})

    def test_inspect_inventory_safe(self):
        p=plan_inventory(self.account,self.state,"inv")
        self.assertEqual(p.action.kind,"inspect_inventory")
        self.assertEqual(p.status,"proposed")

    def test_inspect_pokemon_safe(self):
        p=plan_pokemon(self.account,self.state,"poke")
        self.assertEqual(p.action.kind,"inspect_pokemon")

    def test_evolution_unknown_gives_no_action(self):
        p=plan_evolution(self.account,self.state,"ev",None)
        self.assertIsNone(p.action)

    def test_evolution_inspection_then_explicit_confirmation(self):
        proposal=EvolutionAssessment("poke1",True,"Ivysaur",True)
        step1=plan_evolution(self.account,self.state,"e1",proposal)
        step2=plan_evolution(self.account,self.state,"e2",proposal,propose_commit=True)
        self.assertEqual(step1.action.kind,"evaluate_evolution")
        self.assertEqual(step2.action.kind,"evolve_pokemon")
        self.assertEqual(step2.status,"needs_human_approval")

    def test_evolution_without_verified_costs_blocked(self):
        proposal=EvolutionAssessment("poke1",True,"Ivysaur",False)
        p=plan_evolution(self.account,self.state,"e1",proposal,propose_commit=True)
        self.assertIsNone(p.action)

    def test_evolution_for_other_account_blocked(self):
        proposal=EvolutionAssessment("pokemon-de-outra-conta",True,"Ivysaur",True)
        p=plan_evolution(self.account,self.state,"e1",proposal,propose_commit=True)
        self.assertIsNone(p.action)


class MarketPlannerTests(unittest.TestCase):
    def setUp(self):
        self.account=make_account()
        self.state=state(inventory={"stone":5})

    @staticmethod
    def evidence(sales=3, positive=True, allowed=True, verified=True):
        return MarketAssessment("stone", sales, 50, positive, allowed, verified)

    def test_less_than_three_completed_sales_no_trade(self):
        for sales in (0,1,2):
            with self.subTest(sales=sales):
                result=plan_market(self.account,self.state,"market",self.evidence(sales),"buy_item")
                self.assertEqual(result.status,"need_data")
                self.assertIsNone(result.action)

    def test_listings_are_not_completed_sales(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(sales=10,verified=False),"publish_listing")
        self.assertEqual(result.status,"need_data")

    def test_nonprofit_opportunity_blocked(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(positive=False),"buy_item")
        self.assertEqual(result.status,"blocked")

    def test_not_tradeable_blocked(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(allowed=False),"publish_listing")
        self.assertEqual(result.status,"blocked")

    def test_cannot_publish_without_stock(self):
        empty=state(inventory={})
        result=plan_market(self.account,empty,"market",self.evidence(),"publish_listing")
        self.assertEqual(result.status,"blocked")

    def test_prepare_listing_only_draft(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(),"prepare_listing")
        self.assertEqual(result.status,"proposed")
        self.assertEqual(result.action.kind,"prepare_listing")
        self.assertEqual(result.action.price_gems,0)

    def test_publish_listing_human_approval(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(),"publish_listing")
        self.assertEqual(result.status,"needs_human_approval")
        self.assertEqual(result.action.price_gems,50)

    def test_buy_item_human_approval(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(),"buy_item")
        self.assertEqual(result.status,"needs_human_approval")

    def test_default_engine_blocks_proposed_purchase(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(),"buy_item")
        blocked=Engine().execute(result.action, FakeIOAdapter(),mode="simulation")
        self.assertEqual(blocked["status"],"blocked")

    def test_dry_run_never_executes_listing(self):
        result=plan_market(self.account,self.state,"market",
                           self.evidence(),"publish_listing")
        adapter=FakeIOAdapter()
        before=adapter.observe()
        dry=Engine(Policy(max_listing_gems=100)).execute(result.action,adapter)
        self.assertEqual(dry["status"],"dry_run")
        self.assertEqual(before,adapter.observe())

    def test_invalid_market_operation(self):
        with self.assertRaises(ValueError):
            plan_market(self.account,self.state,"m",self.evidence(),"transfer_gems")

    def test_buy_pokemon_also_requires_approval(self):
        result=plan_market(self.account,self.state,"m",self.evidence(),"buy_pokemon")
        self.assertEqual(result.status,"needs_human_approval")


if __name__ == "__main__":
    unittest.main()
