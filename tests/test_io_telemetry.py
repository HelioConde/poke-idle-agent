import math
import unittest
from app.io_telemetry import (dry_run_decision, measured_xp_per_hour, sanitize,
                              sanitize_observation, sanitize_automation_audit)

class IoTelemetryTests(unittest.TestCase):
    def test_empty_dom_read_is_not_fabricated(self):
        self.assertEqual(sanitize({"source": "dom", "stats": {}})["available"], False)
        self.assertEqual(dry_run_decision({})["action"], "observe")

    def test_valid_numbers(self):
        stats = sanitize({"source": "dom", "stats": {"level": 40, "hp_current": 21, "hp_max": 100}})
        self.assertEqual(stats["stats"]["level"], 40)
        self.assertEqual(dry_run_decision(stats["stats"])["action"], "review_health")

    def test_unauthorized_data_rejected(self):
        for sample in (
            {"source": "dom", "stats": {"session_token": "secret"}},
            {"source": "dom", "stats": {"email": 32}},
            {"source": "dom", "stats": {"xp_current": math.nan}},
            {"source": "dom", "stats": {"gems": -1}},
            {"source": "dom", "stats": {"coins": True}},
            {"source": "websocket", "stats": {"coins": 10}},
        ):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                sanitize(sample)

    def test_xp_rate_only_same_level_with_valid_progress(self):
        past = {"level": 14, "xp_current": 100}
        self.assertEqual(measured_xp_per_hour(past, {"level": 14, "xp_current": 150}, 60), 3000)
        self.assertIsNone(measured_xp_per_hour(past, {"level": 15, "xp_current": 12}, 60))
        self.assertIsNone(measured_xp_per_hour(past, {"level": 14, "xp_current": 5}, 60))
        self.assertIsNone(measured_xp_per_hour(past, {"level": 14, "xp_current": 130}, 2))


    def test_diagnostic_xp_ambiguity_is_only_count_not_private_text(self):
        payload = {"status": "metrics", "canvas": 9, "iframes": 0,
                   "candidates": 99, "xp_candidates": 2, "xp_ambiguous": True}
        self.assertEqual(sanitize_observation(payload), payload)
        old = {k: payload[k] for k in ("status", "canvas", "iframes", "candidates")}
        self.assertEqual(sanitize_observation(old), old)
        resolved = dict(payload, xp_ambiguous=False, xp_trainer_scoped=True)
        self.assertEqual(sanitize_observation(resolved), resolved)
        for corrupted in (
            dict(payload, xp_ambiguous=False),
            dict(payload, xp_candidates="2"),
            dict(payload, xp_candidates=21),
            dict(payload, raw_xp="7.346 / 15.400 xp"),
            dict(payload, xp_ambiguous="true"),
            dict(resolved, xp_trainer_scoped="true"),
            dict(resolved, xp_trainer_scoped=False),
            dict(resolved, xp_candidates=0),
        ):
            with self.subTest(corrupted=corrupted), self.assertRaises(ValueError):
                sanitize_observation(corrupted)

    def test_no_action_is_executed(self):
        rec = dry_run_decision({"hp_current": 5, "hp_max": 100})
        self.assertEqual(rec["mode"], "dry_run")
        self.assertNotIn(rec["action"], {"click", "buy", "withdraw", "sell"})

    def test_current_protocol_requires_coherent_reader_state(self):
        payload = {"status": "metrics", "canvas": 0, "iframes": 0, "candidates": 4,
                   "xp_candidates": 1, "xp_ambiguous": False, "xp_trainer_scoped": True,
                   "xp_reason": "trainer_xp_scoped", "telemetry_protocol": 2,
                   "reader_version": "trainer-xp-scoped-v1", "content_state": "responded"}
        self.assertEqual(sanitize_observation(payload), payload)
        with self.assertRaises(ValueError):
            sanitize_observation(dict(payload, reader_version="unknown"))

    def test_decision_is_explainable_and_verifiable(self):
        rec = dry_run_decision({"level": 2, "xp_current": 5}, 300)
        for key in ("objective", "data_used", "confidence", "risk",
                    "preconditions", "expected_result", "verification_plan",
                    "permission_required"):
            self.assertIn(key, rec)
        self.assertEqual(rec["action"], "track_farm")

    def test_map_and_native_controls_have_fixed_selectors(self):
        audit = {"route": "app", "farm_state": "active", "map_state": "open", "controls": {
            "hunt_map": {"selector": 'button[data-modal="mapa"]',
                         "present": True, "enabled": True, "policy": "read_only"},
            "map_dialog": {"selector": '#modal .modal-caixa[data-modal="mapa"]',
                           "present": True, "enabled": True, "policy": "read_only"},
            "native_revive": {"selector": "#auto-revive", "present": True,
                              "enabled": True, "policy": "read_only", "toggle_state": "on"},
            "native_potion": {"selector": "#auto-potion", "present": True,
                              "enabled": True, "policy": "read_only", "toggle_state": "off"},
            "surrender": {"selector": "#eco-desistir", "present": True,
                          "enabled": True, "policy": "permanently_blocked"},
        }}
        self.assertEqual(sanitize_automation_audit(audit), audit)
        for corrupted in (
            {**audit, "map_state": "traveling"},
            {**audit, "controls": {**audit["controls"],
             "native_potion": {**audit["controls"]["native_potion"], "toggle_state": "click"}}},
            {**audit, "controls": {**audit["controls"],
             "native_revive": {**audit["controls"]["native_revive"], "selector": "#random"}}},
            {**audit, "controls": {**audit["controls"],
             "surrender": {**audit["controls"]["surrender"], "policy": "read_only"}}},
            {**audit, "controls": {**audit["controls"],
             "hunt_map": {**audit["controls"]["hunt_map"], "policy": "clickable"}}},
            {**audit, "controls": {**audit["controls"],
             "map_dialog": {**audit["controls"]["map_dialog"], "toggle_state": "on"}}},
            {**audit, "controls": {**audit["controls"],
             "native_revive": {**audit["controls"]["native_revive"], "checked": True}}},
        ):
            with self.subTest(corrupted=corrupted), self.assertRaises(ValueError):
                sanitize_automation_audit(corrupted)

    def test_hunt_hud_hint_is_bounded_and_never_executes(self):
        base = {"route": "app", "farm_state": "unknown",
                "map_state": "closed", "controls": {}}
        matching = {"status": "matching_displays", "label": "Larvitar",
                    "level": 30, "source": "both"}
        valid = dict(base, hunt_hint=matching)
        self.assertEqual(sanitize_automation_audit(valid)["hunt_hint"], matching)
        for hint in (
            {"status": "single_display", "label": "Oddish", "level": 15, "source": "eco"},
            {"status": "unavailable", "label": None, "level": None, "source": "none"},
            {"status": "ambiguous", "label": None, "level": None, "source": "both"},
        ):
            self.assertEqual(sanitize_automation_audit(dict(base, hunt_hint=hint))["hunt_hint"], hint)
        for broken in (
            {**matching, "status": ["matching_displays"]},
            {**matching, "source": {"value": "both"}},
            {**matching, "label": "<img src=x>"},
            {**matching, "label": "trainer@email.com"},
            {**matching, "label": "x" * 60},
            {**matching, "level": True},
            {**matching, "level": "30"},
            {**matching, "source": "hud"},
            {**matching, "url": "http://example.invalid"},
            {"status": "single_display", "label": "Oddish", "level": 15, "source": "both"},
            {"status": "unavailable", "label": "Larvitar", "level": None, "source": "none"},
        ):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                sanitize_automation_audit(dict(base, hunt_hint=broken))
        with self.assertRaises(ValueError):
            sanitize_automation_audit(dict(base, route="not_app", hunt_hint=matching))

    def test_readonly_map_structure_rejects_untrusted_fields_and_inconsistent_state(self):
        base = {"route": "app", "farm_state": "unknown",
                "map_state": "open", "controls": {}}
        observed = {"status": "observed", "buttons": 8, "links": 2,
                    "candidate_markers": 3}
        self.assertEqual(sanitize_automation_audit(dict(base, map_structure=observed))
                         ["map_structure"], observed)
        missing = {"status": "body_missing", "buttons": 0, "links": 0,
                   "candidate_markers": 0}
        self.assertEqual(sanitize_automation_audit(dict(base, map_structure=missing))
                         ["map_structure"], missing)
        closed = dict(base, map_state="closed", map_structure={
            "status": "not_open", "buttons": 0, "links": 0,
            "candidate_markers": 0})
        self.assertEqual(sanitize_automation_audit(closed)["map_structure"]["status"],
                         "not_open")
        invalid = (
            {**observed, "buttons": 201},
            {**observed, "links": -1},
            {**observed, "candidate_markers": True},
            {**observed, "buttons": "8"},
            {**observed, "url": "https://private.invalid"},
            {**observed, "html": "<button>"},
            {**observed, "status": ["observed"]},
            {**missing, "buttons": 1},
        )
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                sanitize_automation_audit(dict(base, map_structure=item))
        with self.assertRaises(ValueError):
            sanitize_automation_audit(dict(base, map_state="closed",
                                           map_structure=observed))
        with self.assertRaises(ValueError):
            sanitize_automation_audit(dict(base, map_state="open",
                map_structure={"status": "not_open", "buttons": 0,
                               "links": 0, "candidate_markers": 0}))
        with self.assertRaises(ValueError):
            sanitize_automation_audit(dict(base, route="not_app",
                                           map_structure=observed))

    def test_automation_audit_is_closed_and_never_approves_control(self):
        audit = {"route": "app", "farm_state": "active", "controls": {
            "surrender": {"selector": "#eco-desistir", "present": True,
                          "enabled": True, "policy": "permanently_blocked"},
            "hunt_map": {"selector": None, "present": False,
                         "enabled": False, "policy": "not_audited"},
        }}
        self.assertEqual(sanitize_automation_audit(audit), audit)
        with self.assertRaises(ValueError):
            sanitize_automation_audit({**audit, "html": "<button>"})
        with self.assertRaises(ValueError):
            sanitize_automation_audit({**audit, "controls": {
                "arbitrary": {"selector": "#anything", "present": True,
                              "enabled": True, "policy": "read_only"}}})
