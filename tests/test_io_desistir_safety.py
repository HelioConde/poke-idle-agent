"""Regressão após perda real de 549 XP por 'Desistir'. Somente estados fictícios."""
import unittest
from time import time

from app.io_action_engine import (
    Engine, ActionRequest, ObservedIO,
    reconcile_farm_state, verify_transition
)
from app.adaptive_strategy import Account, Measurement
from app.io_operation_planner import plan_farm


def observation(*, farming=False, session_farming=False,
                scene="hunt", defeated=False, xp=5490, hunt="h1", when=None):
    return ObservedIO("io", "perfil", "conta", hunt_id=hunt,
                      farming=farming, scene=scene, team_defeated=defeated,
                      trainer_xp=xp, session_farming=session_farming, observed_at=when)


def command(kind="select_hunt", target="h2"):
    return ActionRequest("op-1", "io", "perfil", "conta", kind, target)


class LossyStopRegressionTests(unittest.TestCase):
    def test_one_snapshot_not_enough(self):
        self.assertEqual(reconcile_farm_state([observation()])["status"],"unknown")

    def test_identical_hud_and_session_stopped_stable(self):
        now=time()
        frames=[observation(when=now-3),observation(when=now)]
        self.assertEqual(reconcile_farm_state(frames)["status"],"stopped_stable")

    def test_identical_timestamp_is_not_two_real_observations(self):
        now=time()
        frames=[observation(when=now),observation(when=now)]
        self.assertEqual(reconcile_farm_state(frames)["status"],"unknown")

    def test_stable_active_not_permission_to_switch(self):
        now=time()
        frames=[observation(farming=True,session_farming=True,when=now-3),
                observation(farming=True,session_farming=True,when=now)]
        self.assertEqual(reconcile_farm_state(frames)["status"],"active_stable")

    def test_centre_with_stale_session_requires_recovery(self):
        readings=[
            observation(farming=True,session_farming=True,xp=5490),
            observation(farming=True,session_farming=True,
                        scene="pokemon_center",defeated=True,xp=4949)
        ]
        self.assertEqual(reconcile_farm_state(readings)["status"],"recovery_required")

    def test_session_disagreement_blocks_hunt(self):
        readings=[observation(farming=False,session_farming=True),
                  observation(farming=False,session_farming=True)]
        self.assertEqual(reconcile_farm_state(readings)["status"],"inconsistent")

    def test_explicit_xp_loss_never_counts_as_safe_stop(self):
        frames=[observation(xp=5490),observation(xp=4949)]
        self.assertEqual(reconcile_farm_state(frames)["status"],"xp_loss")

    def test_transition_between_snapshots_not_stable(self):
        frames=[observation(farming=True,session_farming=True),
                observation(farming=False,session_farming=False)]
        self.assertEqual(reconcile_farm_state(frames)["status"],"transition")

    def test_changed_hunt_not_stable(self):
        frames=[observation(hunt="h1"),observation(hunt="h2")]
        self.assertEqual(reconcile_farm_state(frames)["status"],"transition")

    def test_no_scene_or_missing_xp_blocks(self):
        one=ObservedIO("io","perfil","conta",hunt_id="h1",farming=False)
        self.assertEqual(reconcile_farm_state([one,one])["status"],"unknown")

    def test_stop_not_success_after_team_defeat(self):
        before=observation(farming=True,session_farming=True,xp=5490)
        after=observation(farming=False,session_farming=False,
                          scene="pokemon_center",defeated=True,xp=4949)
        self.assertFalse(verify_transition(command("stop_farm",""),before,after))

    def test_stop_not_success_if_trainer_xp_drops(self):
        before=observation(farming=True,session_farming=True,xp=5490)
        after=observation(farming=False,session_farming=False,xp=4949)
        self.assertFalse(verify_transition(command("stop_farm",""),before,after))

    def test_live_stop_farm_denied_even_with_verified_adapter(self):
        class LossyAdapter:
            is_simulation=False
            verified_actions=frozenset({"stop_farm"})
            performed=False
            def observe(self):
                return observation(farming=True,session_farming=True)
            def perform(self,request):
                self.performed=True
        adapter=LossyAdapter()
        engine=Engine()
        result=engine.execute(command("stop_farm",""),adapter,"live")
        self.assertEqual(result["status"],"blocked")
        self.assertFalse(adapter.performed)
        self.assertIn("Desistir",result["message"])

    def test_live_select_hunt_denied_without_complete_evidence(self):
        class UnknownStateAdapter:
            is_simulation=False
            verified_actions=frozenset({"select_hunt"})
            performed=False
            def observe(self):
                return ObservedIO("io","perfil","conta",hunt_id="h1",farming=False)
            def perform(self,request):
                self.performed=True
        adapter=UnknownStateAdapter()
        engine=Engine()
        result=engine.execute(command(),adapter,"live")
        self.assertEqual(result["status"],"blocked")
        self.assertFalse(adapter.performed)

    def test_live_select_hunt_denied_in_center_even_with_authorization(self):
        class CentreAdapter:
            is_simulation=False
            verified_actions=frozenset({"select_hunt"})
            performed=False
            def observe(self):
                return observation(farming=True,session_farming=True,
                                   scene="pokemon_center",defeated=True,xp=4949)
            def perform(self,request):
                self.performed=True
        adapter=CentreAdapter()
        engine=Engine()
        request=command()
        token=engine.approvals.issue(request)
        result=engine.execute(request,adapter,"live",token)
        self.assertEqual(result["status"],"blocked")
        self.assertFalse(adapter.performed)

    def test_xp_loss_after_action_forces_emergency(self):
        class MisbehavingSimulator:
            is_simulation=True
            verified_actions=frozenset({"start_farm"})
            executed=False
            def observe(self):
                return observation(farming=self.executed,session_farming=self.executed,
                                   xp=4949 if self.executed else 5490)
            def perform(self,request):
                self.executed=True
        adapter=MisbehavingSimulator()
        engine=Engine()
        request=command("start_farm","")
        result=engine.execute(request,adapter,"simulation")
        self.assertEqual(result["status"],"uncertain")
        self.assertTrue(engine.emergency)

    def test_live_not_allowed_after_defeat(self):
        class Defeated:
            is_simulation=False
            verified_actions=frozenset({"start_farm"})
            performed=False
            def observe(self):
                return observation(farming=False,session_farming=True,
                                   scene="pokemon_center",defeated=True,xp=4949)
            def perform(self, request):
                self.performed=True
        adapter=Defeated()
        engine=Engine()
        result=engine.execute(command("start_farm",""),adapter,"live")
        self.assertEqual(result["status"],"blocked")
        self.assertFalse(adapter.performed)


if __name__ == "__main__":
    unittest.main()
