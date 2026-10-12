"""Unitários do executor: nenhum teste acessa o Poke Idle IO autenticado."""
import unittest

from app.io_action_engine import (
    ActionRequest, ApprovalRegistry, Engine, FakeIOAdapter, ObservedIO,
    Policy, verify_transition, demo
)


def req(kind, request_id="id", target="", quantity=1, price=0,
        game="io", profile="demo", account="demo"):
    return ActionRequest(request_id, game, profile, account, kind,
                         target, quantity, price)


class IOActionValidationTests(unittest.TestCase):
    def test_world_is_never_automated(self):
        with self.assertRaises(PermissionError):
            req("select_hunt", game="world", target="hunt")

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            req("send_secret")

    def test_missing_target_rejected(self):
        for kind in ("select_hunt", "evolve_pokemon", "buy_item", "publish_listing"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                req(kind)

    def test_price_required_for_market_operations(self):
        for kind in ("buy_item","buy_pokemon","publish_listing"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                req(kind,target="thing",price=0)

    def test_price_rejected_on_non_market_action(self):
        with self.assertRaises(ValueError):
            req("select_hunt",target="forest",price=5)

    def test_bool_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            req("buy_item",target="potion",quantity=True,price=2)

    def test_default_policy_blocks_financial_operations(self):
        engine=Engine()
        self.assertEqual(engine.execute(req("buy_item",target="potion",price=1))["status"],"blocked")
        self.assertEqual(engine.execute(req("publish_listing",target="stone",price=25))["status"],"blocked")

    def test_policy_limits_quantity(self):
        engine=Engine(Policy(max_spend_gems=100,max_quantity=2))
        response=engine.execute(req("buy_item",target="potion",quantity=3,price=1))
        self.assertEqual(response["status"],"blocked")

    def test_total_price_must_fit_spend_cap(self):
        engine=Engine(Policy(max_spend_gems=10))
        response=engine.execute(req("buy_item",target="potion",quantity=2,price=6))
        self.assertEqual(response["status"],"blocked")

    def test_fingerprint_changes_with_account_price_and_quantity(self):
        a=req("buy_item",target="potion",price=1)
        self.assertNotEqual(a.fingerprint,req("buy_item",target="potion",price=2).fingerprint)
        self.assertNotEqual(a.fingerprint,req("buy_item",target="potion",price=1,account="other").fingerprint)


class EngineSimulationTests(unittest.TestCase):
    def setUp(self):
        self.engine=Engine(Policy(max_spend_gems=80,max_listing_gems=100))
        self.adapter=FakeIOAdapter()

    def execute(self,kind, request_id, target="",quantity=1,price=0):
        return self.engine.execute(req(kind,request_id,target,quantity,price),
                                   self.adapter,mode="simulation")

    def test_dry_run_does_not_change_state(self):
        before=self.adapter.observe()
        response=self.engine.execute(req("select_hunt",target="forest"),self.adapter)
        self.assertEqual(response["status"],"dry_run")
        self.assertEqual(self.adapter.observe(),before)

    def test_select_best_map_simulated(self):
        outcome=self.execute("select_hunt","choose-map","forest")
        self.assertEqual(outcome["status"],"simulated")
        self.assertEqual(self.adapter.observe().hunt_id,"forest")

    def test_start_and_stop_farm(self):
        self.assertEqual(self.execute("start_farm","start")["status"],"simulated")
        self.assertTrue(self.adapter.observe().farming)
        self.assertEqual(self.execute("stop_farm","stop")["status"],"simulated")
        self.assertFalse(self.adapter.observe().farming)

    def test_evolution_simulated_no_real_pokemon(self):
        before=self.adapter.observe()
        self.assertEqual(self.execute("evolve_pokemon","evolve","poke1")["status"],"simulated")
        self.assertNotEqual(before.pokemon_species["poke1"],
                            self.adapter.observe().pokemon_species["poke1"])

    def test_publish_listing_is_not_a_sale(self):
        outcome=self.execute("publish_listing","list","stone",1,50)
        after=self.adapter.observe()
        self.assertEqual(outcome["status"],"simulated")
        self.assertEqual(after.inventory["stone"],2)
        self.assertEqual(after.listings["stone"],1)
        self.assertEqual(after.gems_balance,200)

    def test_purchase_simulated(self):
        self.assertEqual(self.execute("buy_item","buy","potion",2,10)["status"],"simulated")
        after=self.adapter.observe()
        self.assertEqual(after.gems_balance,180)
        self.assertEqual(after.inventory["potion"],3)

    def test_sell_npc_changes_inventory_only(self):
        self.assertEqual(self.execute("sell_npc","sell","stone",1)["status"],"simulated")
        self.assertEqual(self.adapter.observe().inventory["stone"],2)

    def test_cancel_listing(self):
        self.execute("publish_listing","list","stone",1,50)
        self.assertEqual(self.execute("cancel_listing","cancel","stone")["status"],"simulated")
        after=self.adapter.observe()
        self.assertEqual(after.listings["stone"],0)
        self.assertEqual(after.inventory["stone"],3)

    def test_pause_resume(self):
        self.engine.pause()
        self.assertEqual(self.execute("start_farm","start")["status"],"blocked")
        self.engine.resume()
        self.assertEqual(self.execute("start_farm","start")["status"],"simulated")

    def test_emergency_cannot_resume(self):
        self.engine.emergency_stop()
        self.assertEqual(self.execute("start_farm","start")["status"],"blocked")
        with self.assertRaises(PermissionError):
            self.engine.resume()

    def test_idempotency(self):
        self.assertEqual(self.execute("start_farm","start")["status"],"simulated")
        self.assertEqual(self.execute("start_farm","start")["status"],"blocked")

    def test_max_actions(self):
        engine=Engine(Policy(max_actions=1))
        adapter=FakeIOAdapter()
        self.assertEqual(engine.execute(req("start_farm","one"),adapter,"simulation")["status"],"simulated")
        self.assertEqual(engine.execute(req("stop_farm","two"),adapter,"simulation")["status"],"blocked")

    def test_unexpected_account_blocked(self):
        other=FakeIOAdapter("another")
        outcome=self.engine.execute(req("start_farm","start"),other,"simulation")
        self.assertEqual(outcome["status"],"blocked")

    def test_simulation_requires_fake_adapter(self):
        class Real:
            is_simulation=False
            verified_actions=frozenset({"start_farm"})
            def observe(self): return FakeIOAdapter().observe()
            def perform(self,r): raise AssertionError("should not call")
        outcome=self.engine.execute(req("start_farm"),Real(),"simulation")
        self.assertEqual(outcome["status"],"blocked")

    def test_live_mode_rejects_simulation_adapter(self):
        outcome=self.engine.execute(req("start_farm"),self.adapter,"live")
        self.assertEqual(outcome["status"],"blocked")

    def test_missing_postcondition_fail_closed(self):
        class NoOp(FakeIOAdapter):
            def perform(self, request): pass
        broken=NoOp()
        outcome=self.engine.execute(req("start_farm"),broken,"simulation")
        self.assertEqual(outcome["status"],"uncertain")
        self.assertTrue(self.engine.emergency)

    def test_missing_stock_fail_closed(self):
        outcome=self.execute("publish_listing","list","absent",1,50)
        self.assertEqual(outcome["status"],"uncertain")
        self.assertTrue(self.engine.emergency)

    def test_demo_is_explicitly_simulated(self):
        records=demo()
        self.assertEqual(len(records),6)
        self.assertTrue(all(x["status"]=="simulated" for x in records))


class LiveGateTests(unittest.TestCase):
    class ValidatedAdapter:
        is_simulation=False
        verified_actions=frozenset({"start_farm"})
        def __init__(self):
            self.state=ObservedIO("io","demo","demo",farming=False)
        def observe(self): return self.state
        def perform(self,request):
            self.state=ObservedIO("io","demo","demo",farming=True)

    def test_no_action_without_specific_human_approval(self):
        adapter=self.ValidatedAdapter()
        engine=Engine()
        outcome=engine.execute(req("start_farm"),adapter,"live")
        self.assertEqual(outcome["status"],"blocked")
        self.assertFalse(adapter.observe().farming)

    def test_specific_approval_one_time(self):
        adapter=self.ValidatedAdapter()
        engine=Engine()
        a=req("start_farm","specific")
        token=engine.approvals.issue(a)  # Tests emulate direct human approval.
        self.assertEqual(engine.execute(a,adapter,"live",token)["status"],"verified")
        self.assertEqual(engine.execute(a,adapter,"live",token)["status"],"blocked")

    def test_approval_not_transferable(self):
        adapter=self.ValidatedAdapter()
        engine=Engine()
        token=engine.approvals.issue(req("start_farm","one"))
        response=engine.execute(req("start_farm","two"),adapter,"live",token)
        self.assertEqual(response["status"],"blocked")
        self.assertFalse(adapter.observe().farming)

    def test_unverified_action_rejected_before_approval(self):
        adapter=self.ValidatedAdapter()
        engine=Engine()
        a=req("select_hunt",target="forest")
        token=engine.approvals.issue(a)
        self.assertEqual(engine.execute(a,adapter,"live",token)["status"],"blocked")

    def test_approval_token_never_logged(self):
        adapter=self.ValidatedAdapter()
        engine=Engine()
        a=req("start_farm")
        token=engine.approvals.issue(a)
        engine.execute(a,adapter,"live",token)
        self.assertNotIn(token,str(engine.history))


class TransitionTests(unittest.TestCase):
    def test_no_postcondition_not_success(self):
        a=ObservedIO("io","demo","demo",farming=False)
        r=req("start_farm")
        self.assertFalse(verify_transition(r,a,a))

    def test_changed_account_invalidates_result(self):
        a=ObservedIO("io","demo","demo",farming=False)
        b=ObservedIO("io","demo","another",farming=True)
        self.assertFalse(verify_transition(req("start_farm"),a,b))


if __name__=="__main__":
    unittest.main()
