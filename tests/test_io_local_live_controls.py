"""Comprova que o adaptador Chrome não pode autoaprovar modo live."""
import unittest
from dataclasses import FrozenInstanceError
from time import time

from app.io_action_engine import ActionRequest, Engine, ObservedIO
from app.io_local_live_controls import (
    LOCAL_IO_LIVE_CONTROLS, LocalControlEvidence, locally_verified_control
)


class LocalEvidenceTests(unittest.TestCase):
    def test_registry_starts_empty_and_read_only(self):
        self.assertEqual(len(LOCAL_IO_LIVE_CONTROLS), 0)
        with self.assertRaises(TypeError):
            LOCAL_IO_LIVE_CONTROLS["start_farm"] = object()
        self.assertIsNone(locally_verified_control("start_farm"))
        self.assertIsNone(locally_verified_control("buy_item"))
        self.assertIsNone(locally_verified_control("stop_farm"))
        self.assertIsNone(locally_verified_control(None))

    def test_incomplete_control_proof_never_accepted(self):
        bad = LocalControlEvidence(
            action="start_farm", route="/app", control_id="start-button",
            validation_commit="0"*40, evidence_report="test.md",
            review_ticket="review-1", verified_checks=("read_before",),
        )
        self.assertFalse(bad.is_complete_for("start_farm"))
        self.assertFalse(bad.is_complete_for("select_hunt"))
        self.assertIsNone(locally_verified_control("start_farm"))
        with self.assertRaises(FrozenInstanceError):
            bad.action = "select_hunt"

    def test_claimed_adapter_validation_cannot_enable_live(self):
        class UntrustedAdapter:
            is_simulation = False
            verified_actions = frozenset({
                "start_farm", "select_hunt", "evolve_pokemon",
                "publish_listing", "buy_item", "buy_pokemon",
            })
            performed = False
            def observe(self):
                return ObservedIO(
                    "io", "profile", "account", hunt_id="forest",
                    farming=False, scene="hunt", team_defeated=False,
                    session_farming=False, trainer_xp=1000, observed_at=time(),
                )
            def perform(self, request):
                self.performed = True

        adapter = UntrustedAdapter()
        for kind,target,price in (
            ("start_farm","",0), ("select_hunt","lake",0),
            ("evolve_pokemon","poke",0), ("publish_listing","stone",10),
            ("buy_item","stone",10), ("buy_pokemon","pokemon1",25)
        ):
            with self.subTest(kind=kind):
                request=ActionRequest("request-"+kind,"io","profile","account",
                                      kind,target,1,price)
                engine=Engine()
                token=engine.approvals.issue(request)
                result=engine.execute(request,adapter,mode="live",
                                      approval_token=token)
                self.assertEqual(result["status"],"blocked")
                self.assertIn("prova local auditada",result["message"])
                self.assertFalse(adapter.performed)

    def test_no_approval_does_not_allow_live_either(self):
        class Adapter:
            is_simulation = False
            verified_actions = frozenset({"start_farm"})
            def observe(self):
                raise AssertionError("Adapter should never be called")
            def perform(self,req):
                raise AssertionError("No actions can execute")
        request=ActionRequest("id","io","demo","demo","start_farm")
        result=Engine().execute(request,Adapter(),"live")
        self.assertEqual(result["status"],"blocked")

    def test_dry_run_still_returns_plan(self):
        request=ActionRequest("id","io","demo","demo","select_hunt","lake")
        self.assertEqual(Engine().execute(request)["status"],"dry_run")


if __name__ == "__main__":
    unittest.main()
