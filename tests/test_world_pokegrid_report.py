import copy
import json
import tempfile
import unittest
from pathlib import Path
from app.world_pokegrid_report import analyze, parse_snapshot, analyze_file


def sample(*, ts="2026-10-12T10:00:00-03:00", xp=10000, gold=5000, kills=10,
           captures=1, shiny=0, potions=50, pokeballs=30,
           account="account-A", mon="mon-A", hunt="forest", profile="profile-A"):
    return dict(profile_id=profile, account_id=account, pokemon_id=mon, hunt_id=hunt,
                recorded_at=ts, xp_total=xp, gold_total=gold, kills_total=kills,
                captures_total=captures, shiny_total=shiny,
                potions=potions, pokeballs=pokeballs)


def payload(*readings, source="manual"):
    return {"game":"world","source":source,"snapshots":list(readings)}


class PokeGridManualAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.a=sample()
        self.b=sample(ts="2026-10-12T11:00:00-03:00",xp=12000,gold=5500,
                      kills=20,captures=3,potions=40,pokeballs=25)

    def test_real_manual_rate_and_consumption(self):
        report=analyze(payload(self.a,self.b))
        self.assertEqual(report["source"],"manual")
        self.assertIsNone(report["revenue_usdt"])
        group=report["groups"][0]
        self.assertEqual(group["status"],"measured")
        self.assertEqual(group["xp_per_hour"],2000)
        self.assertEqual(group["net_gold_per_hour"],500)
        self.assertEqual(group["kills_per_hour"],10)
        self.assertEqual(group["captures_per_hour"],2)
        self.assertEqual(group["stocks"]["potions"]["consumed_per_hour_observed"],10)
        self.assertEqual(group["stocks"]["pokeballs"]["estimated_hours_left"],5)

    def test_demo_remains_demo(self):
        report=analyze(payload(self.a,self.b,source="demo"))
        self.assertTrue(report["is_demo"])
        self.assertIsNone(report["revenue_usdt"])

    def test_same_account_different_hunts_not_mixed(self):
        b=sample(hunt="lake",ts="2026-10-12T11:00:00-03:00",xp=12000)
        result=analyze(payload(self.a,b))
        self.assertEqual(len(result["groups"]),2)
        self.assertTrue(all(group["status"]=="measure_more" for group in result["groups"]))

    def test_two_accounts_never_mix(self):
        b=sample(account="account-B",ts="2026-10-12T11:00:00-03:00",xp=100000)
        result=analyze(payload(self.a,b))
        self.assertEqual(len(result["groups"]),2)

    def test_two_pokemon_never_mix(self):
        b=sample(mon="mon-B",ts="2026-10-12T11:00:00-03:00")
        result=analyze(payload(self.a,b))
        self.assertEqual(len(result["groups"]),2)

    def test_rank_two_hunts_only_with_same_account_and_pokemon(self):
        a=sample(hunt="forest")
        b=sample(hunt="forest",ts="2026-10-12T11:00:00-03:00",
                 xp=12000,gold=5500,kills=20)
        c=sample(hunt="lake")
        d=sample(hunt="lake",ts="2026-10-12T11:00:00-03:00",
                 xp=11000,gold=8000,kills=15)
        r_xp=analyze(payload(a,b,c,d),priority="xp")
        r_gold=analyze(payload(a,b,c,d),priority="gold")
        self.assertEqual(r_xp["rankings"][0]["hunts"][0]["hunt_id"],"forest")
        self.assertEqual(r_gold["rankings"][0]["hunts"][0]["hunt_id"],"lake")
        self.assertEqual(r_xp["rankings"][0]["account_id"],"account-A")

    def test_no_rank_between_different_accounts(self):
        c=sample(account="account-B")
        d=sample(account="account-B",ts="2026-10-12T11:00:00-03:00",xp=18000)
        r=analyze(payload(self.a,self.b,c,d))
        self.assertEqual(r["rankings"],[])

    def test_invalid_priority_rejected(self):
        with self.assertRaises(ValueError):
            analyze(payload(self.a,self.b),priority="money")

    def test_level_down_or_counter_reset_no_positive_rate(self):
        b=copy.deepcopy(self.b)
        b["xp_total"]=9000
        result=analyze(payload(self.a,b))
        self.assertEqual(result["groups"][0]["status"],"inconsistent")
        self.assertNotIn("xp_per_hour",result["groups"][0])

    def test_negative_gold_not_real_money(self):
        b=copy.deepcopy(self.b)
        b["gold_total"]=4000
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertEqual(result["net_gold_per_hour"],-1000)
        self.assertTrue(any("Gold líquido" in x for x in result["warnings"]))

    def test_shiny_manual_confirmation(self):
        b=copy.deepcopy(self.b)
        b["shiny_total"]=1
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertEqual(result["new_shiny_marked_manually"],1)
        self.assertTrue(any("Shiny" in x for x in result["warnings"]))

    def test_stalled_hunt_warning(self):
        b=copy.deepcopy(self.b)
        b["kills_total"]=self.a["kills_total"]
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertTrue(any("Sem kills" in x for x in result["warnings"]))

    def test_supply_low_warning(self):
        b=copy.deepcopy(self.b)
        b["potions"]=5
        b["pokeballs"]=3
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertTrue(any("estoque baixo" in x for x in result["warnings"]))

    def test_time_window_too_short(self):
        b=copy.deepcopy(self.b)
        b["recorded_at"]="2026-10-12T10:05:00-03:00"
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertEqual(result["status"],"measure_more")

    def test_duplicate_timestamps_rejected_as_evidence(self):
        b=copy.deepcopy(self.b)
        b["recorded_at"]=self.a["recorded_at"]
        result=analyze(payload(self.a,b))["groups"][0]
        self.assertEqual(result["status"],"measure_more")

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            analyze(payload(self.a,self.b,source="observed"))

    def test_world_only(self):
        with self.assertRaises(ValueError):
            analyze({"game":"io","source":"manual","snapshots":[self.a,self.b]})

    def test_disallow_auth_fields(self):
        bad=dict(self.a,token="secret")
        with self.assertRaises(ValueError):
            parse_snapshot(bad)

    def test_disallow_email_and_credentials(self):
        bad=dict(self.a,account_id="email@example.com")
        with self.assertRaises(ValueError):
            parse_snapshot(bad)

    def test_disallow_negative_and_string_counters(self):
        for v in ("5",-1,True):
            with self.subTest(v=v),self.assertRaises(ValueError):
                parse_snapshot(dict(self.a,xp_total=v))

    def test_requires_timezone(self):
        with self.assertRaises(ValueError):
            parse_snapshot(dict(self.a,recorded_at="2026-10-12T12:00:00"))

    def test_example_fixture_is_fictional(self):
        path=Path(__file__).resolve().parents[1]/"examples"/"pokegrid_snapshots_demo.json"
        report=analyze_file(path)
        self.assertTrue(report["is_demo"])
        self.assertEqual(report["groups"][0]["status"],"measured")

    def test_no_actual_credentials_or_network_imports(self):
        import inspect
        import app.world_pokegrid_report as module
        src=inspect.getsource(module)
        for blocked in ("requests.get(", "webdriver", "playwright.", "chrome.tabs",
                        "websocket.", "requests.post("):
            self.assertNotIn(blocked,src)


if __name__=="__main__":
    unittest.main()
