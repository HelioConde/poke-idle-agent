"""Garantias universais, isolamento de contas e bloqueio de execução no World."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.adaptive_strategy import (
    Account, Hunt, MarketEvidence, Measurement, Pokemon, plan, plan_many, rank_hunts
)


def pokemon(id="mon-1", species="Bulbasaur", level=1, hp=100, max_hp=100):
    return {"id":id,"species":species,"level":level,"hp":hp,"max_hp":max_hp}


def hunt(id="h1", label="Hunt 1", unlocked=True, required_trainer_level=None):
    return {"id":id,"label":label,"unlocked":unlocked,
            "required_trainer_level":required_trainer_level}


def account(game="world", profile="profile-A", alias="account-A",
            roster=None, active="mon-1", trainer=1, hunts=None):
    return Account.parse({
        "game":game,"profile_id":profile,"account_id":alias,
        "trainer_level":trainer,
        "roster":[pokemon()] if roster is None else roster,
        "active_pokemon_id":active,
        "hunts":[hunt()] if hunts is None else hunts
    })


def sample(game="world", profile="profile-A", alias="account-A",
           mon="mon-1", area="h1", minutes=60, xp=100, gain=300,
           spent=0, defeats=0, source="manual"):
    return Measurement.parse({
        "game":game,"profile_id":profile,"account_id":alias,
        "pokemon_id":mon,"hunt_id":area,
        "minutes":minutes,"xp_gained":xp,"resources_gained":gain,
        "resources_spent":spent,"defeats":defeats,"source":source
    })


class NewAccountsTests(unittest.TestCase):
    def test_empty_account_onboards(self):
        state = account(roster=[], active=None, trainer=1, hunts=[])
        output = plan(state,[])
        self.assertEqual(output["stage"],"onboarding")
        self.assertEqual(output["action"],"inspect_starter")

    def test_new_pokemon_without_level_assumption(self):
        output = plan(account(roster=[pokemon(species="Caterpie",level=1)]),[])
        self.assertEqual(output["stage"],"measurement")
        self.assertEqual(output["active_pokemon"]["level"],1)

    def test_already_evolved_charizard_is_just_another_member(self):
        mon=pokemon(species="Charizard",level=110)
        output=plan(account(roster=[mon],trainer=110),[])
        self.assertEqual(output["stage"],"measurement")
        self.assertNotIn("evol",output["reason"].lower())

    def test_arbitrary_species_accepted(self):
        mon=pokemon(species="Pikachu",level=25)
        self.assertEqual(plan(account(roster=[mon]),[])["active_pokemon"]["species"],"Pikachu")

    def test_multiple_pokemon_requires_explicit_active(self):
        team=[pokemon("a","Pikachu",20),pokemon("b","Bulbasaur",100)]
        self.assertEqual(plan(account(roster=team,active=None),[])["action"],"choose_active")

    def test_low_hp_precedes_farming(self):
        state=account(roster=[pokemon(hp=10,max_hp=100)])
        self.assertEqual(plan(state,[])["action"],"review_recovery")

    def test_unknown_hp_not_assumed_low(self):
        state=account(roster=[{"id":"mon-1","species":"Oddish","level":12}])
        self.assertEqual(plan(state,[])["stage"],"measurement")

    def test_trainer_level_unknown_gives_discovery(self):
        state=account(trainer=None)
        self.assertEqual(plan(state,[])["action"],"record_trainer_level")

    def test_locked_hunt_milestone_comes_from_data(self):
        state=account(hunts=[
            hunt("one","Early route",False,7),
            hunt("two","Later route",False,20)])
        outcome=plan(state,[])
        self.assertEqual(outcome["action"],"inspect_hunt_access")
        self.assertEqual(outcome["next_declared_trainer_milestone"],7)

    def test_unknown_unlock_does_not_count_as_available(self):
        state=account(hunts=[hunt(unlocked=None)])
        self.assertEqual(plan(state,[])["stage"],"unlock")

    def test_no_evidence_requires_more_measurement(self):
        state=account(hunts=[hunt("h1","A"),hunt("h2","B")])
        outcome=plan(state,[sample(area="h1")])
        self.assertEqual(outcome["stage"],"measurement")


class MultipleAccountsTests(unittest.TestCase):
    def setUp(self):
        self.hunts=[hunt("h1","Farm A"),hunt("h2","Farm B")]
        self.one=account(hunts=self.hunts)
        self.two=account(profile="profile-B",alias="account-B",hunts=self.hunts)

    def test_account_isolation(self):
        metrics=[
            sample(area="h1",xp=10,gain=100),
            sample(area="h2",xp=10,gain=200),
            sample(profile="profile-B",alias="account-B",area="h1",xp=10,gain=999999),
            sample(profile="profile-B",alias="account-B",area="h2",xp=10,gain=0)
        ]
        results=plan_many([self.one,self.two],metrics,"resources")
        self.assertEqual(results[0]["recommended_hunt_id"],"h2")
        self.assertEqual(results[1]["recommended_hunt_id"],"h1")

    def test_same_profile_different_accounts_isolated(self):
        two=account(alias="account-B",hunts=self.hunts)
        metrics=[sample(area="h1"),sample(area="h2")]
        self.assertEqual(plan(two,metrics)["stage"],"measurement")

    def test_games_never_cross_mix(self):
        two=account(game="io",hunts=self.hunts)
        metrics=[sample(area="h1"),sample(area="h2")]
        self.assertEqual(plan(two,metrics)["stage"],"measurement")

    def test_pokemon_swap_requires_new_baseline(self):
        state=account(roster=[pokemon("mon-1"),pokemon("mon-2","Squirtle",10)],
                      active="mon-2",hunts=self.hunts)
        metrics=[sample(area="h1",mon="mon-1"),sample(area="h2",mon="mon-1")]
        self.assertEqual(plan(state,metrics)["stage"],"measurement")

    def test_no_duplicate_account(self):
        with self.assertRaises(ValueError):
            plan_many([self.one,self.one],[])

    def test_world_never_authorizes_external_actions(self):
        self.assertEqual(plan(self.one,[])["capabilities"]["gameplay_execution"],
                         "forbidden_without_explicit_authorization")

    def test_io_always_dry_run(self):
        state=account(game="io")
        self.assertEqual(plan(state,[])["capabilities"]["gameplay_execution"],
                         "dry_run_only")

    def test_io_financial_goal_requires_market_data(self):
        state=account(game="io")
        self.assertEqual(plan(state,[],"monetization")["stage"],"market_research")

    def test_io_financial_goal_uses_only_same_account_market_evidence(self):
        state=account(game="io")
        evidence=MarketEvidence.parse({"game":"io","profile_id":"profile-A","account_id":"account-A",
            "name":"Token de boss","expected_net_gems_per_hour":3,"sale_probability":.8,
            "confidence":.9,"comparable_completed_sales":3,"source":"observed"})
        other=MarketEvidence.parse({"game":"io","profile_id":"profile-B","account_id":"account-B",
            "name":"Outro","expected_net_gems_per_hour":999,"sale_probability":1,
            "confidence":1,"comparable_completed_sales":3,"source":"observed"})
        out=plan(state,[],"monetization",[evidence,other])
        self.assertEqual(out["stage"],"market_optimization")
        self.assertEqual(out["recommended_asset"],"Token de boss")

    def test_demo_market_evidence_never_produces_financial_recommendation(self):
        state=account(game="io")
        evidence=MarketEvidence.parse({"game":"io","profile_id":"profile-A","account_id":"account-A",
            "name":"Ativo demo","expected_net_gems_per_hour":99,"sale_probability":1,
            "confidence":1,"comparable_completed_sales":99,"source":"demo"})
        self.assertEqual(plan_many([state], [], "monetization", [evidence])[0]["stage"],
                         "market_research")

    def test_world_never_claims_verified_cashout(self):
        state=account()
        self.assertEqual(plan(state,[])["capabilities"]["cashout"],"unverified")

    def test_world_monetization_is_not_presented_as_earned_income(self):
        state=account()
        out=plan(state,[],"monetization")
        self.assertEqual(out["stage"],"unsupported")
        self.assertEqual(out["action"],"review_goal")

    def test_world_synthetic_observed_source_not_counted(self):
        metrics=[sample(area="h1",source="observed"),sample(area="h2",source="observed")]
        state=account(hunts=self.hunts)
        self.assertEqual(plan(state,metrics)["stage"],"measurement")


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.a=account(hunts=[hunt("h1","High XP"),hunt("h2","High yield")])

    def test_gold_yield_beats_high_xp_on_resources_goal(self):
        metrics=[sample(area="h1",xp=1000,gain=10),sample(area="h2",xp=100,gain=500)]
        self.assertEqual(plan(self.a,metrics,"resources")["recommended_hunt_id"],"h2")
        self.assertEqual(plan(self.a,metrics,"xp")["recommended_hunt_id"],"h1")

    def test_net_resource_subtracts_cost(self):
        metrics=[sample(area="h1",gain=500,spent=490),sample(area="h2",gain=50)]
        self.assertEqual(plan(self.a,metrics,"resources")["recommended_hunt_id"],"h2")

    def test_defeats_lower_score(self):
        metrics=[sample(area="h1",xp=100,gain=100,defeats=5),
                 sample(area="h2",xp=100,gain=100,defeats=0)]
        self.assertEqual(plan(self.a,metrics)["recommended_hunt_id"],"h2")

    def test_demo_cannot_rank(self):
        metrics=[sample(area="h1",source="demo"),sample(area="h2",source="demo")]
        self.assertEqual(rank_hunts(self.a,metrics)["status"],"measure_more")

    def test_short_sample_cannot_rank(self):
        metrics=[sample(area="h1",minutes=20),sample(area="h2")]
        self.assertEqual(rank_hunts(self.a,metrics)["status"],"measure_more")

    def test_two_short_samples_combined_are_valid(self):
        metrics=[sample(area="h1",minutes=15),sample(area="h1",minutes=15),
                 sample(area="h2",minutes=30)]
        out=rank_hunts(self.a,metrics)
        self.assertEqual(out["status"],"ranked")
        self.assertEqual(next(x for x in out["ranked"] if x["hunt_id"]=="h1")["samples"],2)

    def test_inaccessible_hunts_excluded(self):
        locked=account(hunts=[hunt("h1","Open"),hunt("h2","Locked",False,100)])
        metrics=[sample(area="h1"),sample(area="h2")]
        self.assertEqual(plan(locked,metrics)["stage"],"measurement")

    def test_world_gold_is_not_usdt(self):
        metrics=[sample(area="h1"),sample(area="h2")]
        self.assertIn("não são dinheiro",rank_hunts(self.a,metrics)["note"])


class DataContractTests(unittest.TestCase):
    def test_reject_sensitive_extra_fields(self):
        for extra in ({"token":"secret"},{"email":"alice@example.com"},{"cookie":"x"}):
            raw={"game":"world","profile_id":"p","account_id":"a",
                 "trainer_level":1,"roster":[],"active_pokemon_id":None,"hunts":[]}
            raw.update(extra)
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                Account.parse(raw)

    def test_pokemon_does_not_accept_level_zero_or_string(self):
        for level in (0,"1",-1,True):
            with self.subTest(level=level),self.assertRaises(ValueError):
                Pokemon.parse(pokemon(level=level))

    def test_duplicate_roster_rejected(self):
        with self.assertRaises(ValueError):
            account(roster=[pokemon(),pokemon()])

    def test_measurement_nonfinite_rejected(self):
        payload={"game":"world","profile_id":"p","account_id":"a","pokemon_id":"m",
                 "hunt_id":"h","minutes":float("inf"),"xp_gained":1,
                 "resources_gained":0,"resources_spent":0,"defeats":0,"source":"manual"}
        with self.assertRaises(ValueError):
            Measurement.parse(payload)

    def test_hunt_access_must_be_explicit(self):
        with self.assertRaises(ValueError):
            Hunt.parse(hunt(unlocked="true"))

    def test_cross_profile_measurement_do_not_infer(self):
        a=account()
        other=[sample(profile="other"),sample(profile="other",area="h2")]
        self.assertEqual(plan(a,other)["stage"],"measurement")

    def test_cli_with_demo_files(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,"-m","app.adaptive_strategy",
                               "--accounts",str(root/"examples"/"adaptive_accounts_demo.json"),
                               "--measurements",str(root/"examples"/"adaptive_measurements_demo.json")],
                              cwd=root,capture_output=True,text=True,check=True)
        data=json.loads(result.stdout)
        self.assertEqual(len(data),3)
        self.assertTrue(all(row["capabilities"]["mode"] in ("manual_advice","dry_run") for row in data))

    def test_cli_market_file_is_account_scoped(self):
        payload={"game":"io","profile_id":"profile-A","account_id":"account-A",
                 "trainer_level":1,"roster":[pokemon()],"active_pokemon_id":"mon-1",
                 "hunts":[hunt()]}
        market={"game":"io","profile_id":"profile-A","account_id":"account-A",
                "name":"Item medido","expected_net_gems_per_hour":2,
                "sale_probability":.75,"confidence":.8,
                "comparable_completed_sales":3,"source":"manual"}
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            accounts=directory/"accounts.json"
            evidence=directory/"market.json"
            accounts.write_text(json.dumps([payload]),encoding="utf-8")
            evidence.write_text(json.dumps([market]),encoding="utf-8")
            root=Path(__file__).resolve().parents[1]
            result=subprocess.run([sys.executable,"-m","app.adaptive_strategy",
                                   "--accounts",str(accounts),"--market",str(evidence),
                                   "--objective","monetization"],
                                  cwd=root,capture_output=True,text=True,check=True)
        data=json.loads(result.stdout)
        self.assertEqual(data[0]["recommended_asset"],"Item medido")


if __name__ == "__main__":
    unittest.main()
