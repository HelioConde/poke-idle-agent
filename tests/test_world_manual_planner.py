import unittest
from app.world_manual_planner import Hunt, compare, advise

class WorldPlannerTests(unittest.TestCase):
    @staticmethod
    def sample(name,minutes,xp,gold,cost=0,source="manual"):
        return Hunt(name,minutes,xp,gold,cost,source)

    def test_demo_doesnt_rank(self):
        a=self.sample("A",60,100,50,source="demo")
        b=self.sample("B",60,200,30)
        self.assertEqual(compare([a,b],"gold")["status"],"measure_more")

    def test_short_samples_do_not_rank(self):
        a=self.sample("A",5,100,50)
        b=self.sample("B",60,200,30)
        self.assertEqual(compare([a,b],"gold")["status"],"measure_more")

    def test_gold_priority_beats_xp(self):
        a=self.sample("XP",60,1000,50)
        b=self.sample("Gold",60,100,500)
        self.assertEqual(compare([a,b],"gold")["ranked"][0]["hunt"],"Gold")

    def test_xp_priority(self):
        a=self.sample("XP",60,1000,50)
        b=self.sample("Gold",60,100,500)
        self.assertEqual(compare([a,b],"xp")["ranked"][0]["hunt"],"XP")

    def test_costs_subtract(self):
        a=self.sample("A",60,50,500,495)
        b=self.sample("B",60,50,50,0)
        self.assertEqual(compare([a,b],"gold")["ranked"][0]["hunt"],"B")

    def test_weighted_multiple_samples(self):
        a=self.sample("A",15,100,50)
        b=self.sample("A",15,100,50)
        c=self.sample("B",60,10,50)
        self.assertEqual(compare([a,b,c],"xp")["ranked"][0]["samples"],2)

    def test_no_cashouts(self):
        a=self.sample("A",60,100,50)
        b=self.sample("B",60,90,45)
        self.assertIn("NÃO são USDT",compare([a,b],"gold")["note"])

    def test_warn_level_reset(self):
        self.assertTrue(any("reinicia" in x for x in advise("Charmander",110,None)))

    def test_trainer_level_required(self):
        self.assertTrue(any("TREINADOR" in x for x in advise("Charmander",110,None)))

    def test_reject_zero_minutes(self):
        with self.assertRaises(ValueError):
            Hunt.parse({"hunt":"A","minutes":"0","xp_gained":"50","gold_gained":"20"})

    def test_reject_bad_source(self):
        with self.assertRaises(ValueError):
            Hunt.parse({"hunt":"A","minutes":"60","xp_gained":"50","gold_gained":"20","source":"bot"})
