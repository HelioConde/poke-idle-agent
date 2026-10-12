import copy
import json
import unittest
from pathlib import Path

from app.world_capture_assistant import analyze, analyze_account, analyze_file

ROOT=Path(__file__).resolve().parents[1]


def mk(account_id="c1", vip=False, shiny=False, confirmed=True):
    return {"profile_id":"p1","account_id":account_id,"vip":vip,
            "inventory":{"Poke Ball":10,"Great Ball":3,"Ultra Ball":2,"Idle Ball":1},
            "shiny_reserves":{"Ultra Ball":2,"Great Ball":1,"Idle Ball":1},
            "encounter":{"species":"Pikachu","shiny":shiny,"confirmed":confirmed}}


def pay(*accounts, source="manual"):
    return {"game":"world","source":source,"accounts":list(accounts)}


class WorldNonVipCatchTests(unittest.TestCase):
    def test_default_free_manual_method(self):
        result=analyze(pay(mk()))["accounts"][0]
        self.assertEqual(result["status"],"manual_throw_recommended")
        self.assertEqual(result["allowed_method"],"manual_throw")
        self.assertEqual(result["recommended_ball"],"Poke Ball")
        self.assertEqual(result["capture_execution"],"disabled")

    def test_shiny_can_use_reserved_idle_ball(self):
        row=analyze_account(mk(shiny=True))
        self.assertEqual(row["recommended_ball"],"Idle Ball")
        self.assertIn("shiny",row["reason"])

    def test_normal_protects_shiny_ball_reserves(self):
        a=mk()
        a["normal_priority"]=["Idle Ball","Ultra Ball","Great Ball","Poke Ball"]
        row=analyze_account(a)
        self.assertEqual(row["recommended_ball"],"Great Ball")
        self.assertNotIn("Idle Ball",[row["recommended_ball"]]+row["alternatives"])
        self.assertNotIn("Ultra Ball",[row["recommended_ball"]]+row["alternatives"])

    def test_no_ball_reports_blocked_without_click(self):
        a=mk()
        a["inventory"]={}
        row=analyze_account(a)
        self.assertEqual(row["status"],"no_ball")
        self.assertIsNone(row["recommended_ball"])

    def test_unconfirmed_encounter_cannot_recommend_throw(self):
        a=mk(confirmed=False)
        row=analyze_account(a)
        self.assertEqual(row["status"],"await_manual_encounter")
        self.assertIsNone(row["recommended_ball"])

    def test_unknown_encounter_cannot_recommend_throw(self):
        a=mk()
        a.pop("encounter")
        self.assertEqual(analyze_account(a)["status"],"await_manual_encounter")

    def test_vip_points_to_official_in_game_feature(self):
        row=analyze_account(mk(vip=True))
        self.assertEqual(row["status"],"use_official_feature")
        self.assertEqual(row["allowed_method"],"official_auto_catch")
        self.assertIsNone(row["recommended_ball"])

    def test_user_configurable_normal_priority(self):
        a=mk()
        a["normal_priority"]=["Ultra Ball","Poke Ball"]
        a["shiny_reserves"]={}
        self.assertEqual(analyze_account(a)["recommended_ball"],"Ultra Ball")

    def test_user_configurable_shiny_priority(self):
        a=mk(shiny=True)
        a["shiny_priority"]=["Great Ball","Idle Ball"]
        self.assertEqual(analyze_account(a)["recommended_ball"],"Great Ball")

    def test_histories_separated_for_two_accounts(self):
        a=mk("one")
        b=mk("two")
        a["attempts"]=[{"species":"Pikachu","shiny":False,"ball":"Poke Ball",
                        "captured":True,"source":"manual"}]
        result=analyze(pay(a,b))
        self.assertEqual(result["accounts"][0]["history"]["captures"],1)
        self.assertEqual(result["accounts"][1]["history"]["attempts"],0)

    def test_rate_is_from_manual_data_only(self):
        a=mk()
        a["attempts"]=[
            {"species":"Pikachu","shiny":False,"ball":"Poke Ball","captured":True,"source":"manual"},
            {"species":"Pikachu","shiny":True,"ball":"Idle Ball","captured":False,"source":"manual"},
            {"species":"Pikachu","shiny":True,"ball":"Idle Ball","captured":True,"source":"manual"}]
        h=analyze(pay(a))["accounts"][0]["history"]
        self.assertEqual(h["attempts"],3)
        self.assertEqual(h["captures"],2)
        self.assertEqual(h["shiny_captures"],1)
        self.assertAlmostEqual(h["success_rate"],0.6667,places=4)

    def test_demo_does_not_claim_real_financial_results(self):
        path=ROOT/"examples"/"world_capture_demo.json"
        result=analyze_file(path)
        self.assertTrue(result["is_demo"])
        self.assertIsNone(result["usdt_revenue"])
        self.assertFalse(result["external_auto_catch_enabled"])
        self.assertEqual(len(result["accounts"]),3)
        self.assertEqual(result["accounts"][0]["history"]["source"],"demo")

    def test_no_cross_game_account_allowed(self):
        with self.assertRaises(ValueError):
            analyze({"game":"io","source":"manual","accounts":[mk()]})

    def test_duplicate_account_rejected(self):
        with self.assertRaises(ValueError):
            analyze(pay(mk(),mk()))

    def test_four_accounts_supported_but_fifth_requires_staff_review(self):
        four=[mk(str(i)) for i in range(4)]
        self.assertEqual(len(analyze(pay(*four))["accounts"]),4)
        with self.assertRaises(ValueError):
            analyze(pay(*four,mk("fifth")))

    def test_reject_password_tokens_cookies_local_storage(self):
        for name in ("password","token","cookie","localStorage","email"):
            a=mk()
            a[name]="do not save"
            with self.subTest(name=name),self.assertRaises(ValueError):
                analyze_account(a)

    def test_reject_email_in_alias(self):
        a=mk()
        a["account_id"]="abc@example.com"
        with self.assertRaises(ValueError):
            analyze_account(a)

    def test_reject_invalid_inventory(self):
        for invalid in (-1,True,"50",1.5):
            a=mk()
            a["inventory"]["Poke Ball"]=invalid
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                analyze_account(a)

    def test_reject_duplicate_ball_priority(self):
        a=mk()
        a["shiny_priority"]=["Ultra Ball","Ultra Ball"]
        with self.assertRaises(ValueError):
            analyze_account(a)

    def test_reject_missing_shiny_detection(self):
        a=mk()
        a["encounter"]["shiny"]="false"
        with self.assertRaises(ValueError):
            analyze_account(a)

    def test_attempts_must_be_manual_or_demo_and_consistent(self):
        a=mk()
        a["attempts"]=[{"species":"Pikachu","shiny":False,"ball":"Poke Ball",
                       "captured":True,"source":"observed"}]
        with self.assertRaises(ValueError):
            analyze(pay(a))
        a["attempts"][0]["source"]="demo"
        with self.assertRaises(ValueError):
            analyze(pay(a,source="manual"))

    def test_world_no_automation_implementation_present(self):
        import inspect
        import app.world_capture_assistant as module
        src=inspect.getsource(module)
        for blocked in ("document.querySelector(","dispatchEvent(","WebSocket(","requests.get(",
                        "playwright.",".click(","pyautogui."):
            with self.subTest(blocked=blocked):
                self.assertNotIn(blocked,src)


if __name__=="__main__":
    unittest.main()
