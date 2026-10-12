import json
import tempfile
import unittest
from pathlib import Path

from app.account_setup import PRIVATE_DATA, collect_account, save_account
from app.adaptive_strategy import Account


def answerer(items):
    iterator = iter(items)
    return lambda prompt: next(iterator)


class UniversalAccountSetupTests(unittest.TestCase):
    def test_new_account_with_caterpie(self):
        account=collect_account(answerer([
            "world","perfil-demo","conta-nova","1",
            "Caterpie","poke-caterpie","2",
            "", "poke-caterpie",
            "Rota A","rota-a","s","1",
            ""
        ]))
        self.assertEqual(account.game,"world")
        self.assertEqual(account.roster[0].species,"Caterpie")
        self.assertEqual(account.roster[0].level,2)
        self.assertEqual(account.active_pokemon_id,"poke-caterpie")

    def test_advanced_profile_with_two_pokemon(self):
        account=collect_account(answerer([
            "io","perfil-2","conta-2","100",
            "Charizard","p1","110",
            "Squirtle","p2","20",
            "","p2",
            ""
        ]))
        self.assertEqual(len(account.roster),2)
        self.assertEqual(account.active_pokemon_id,"p2")
        self.assertEqual(account.game,"io")

    def test_unknown_trainer_and_empty_roster_allowed(self):
        account=collect_account(answerer([
            "world","perfil","sem-time","","","",""
        ]))
        self.assertEqual(account.trainer_level,None)
        self.assertEqual(account.roster,())

    def test_alias_cannot_contain_email(self):
        with self.assertRaises(ValueError):
            collect_account(answerer(["world","email@example.org"]))

    def test_persist_multiple_local_accounts_without_overwrite(self):
        PRIVATE_DATA.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE_DATA) as temporary:
            output=Path(temporary)/"accounts.json"
            one=Account.parse({
                "game":"world","profile_id":"perfil1","account_id":"conta1",
                "trainer_level":1,"roster":[],"active_pokemon_id":None,"hunts":[]
            })
            two=Account.parse({
                "game":"io","profile_id":"perfil2","account_id":"conta2",
                "trainer_level":2,"roster":[],"active_pokemon_id":None,"hunts":[]
            })
            save_account(one,output)
            save_account(two,output)
            data=json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(data),2)
            self.assertEqual({x["account_id"] for x in data},{"conta1","conta2"})
            with self.assertRaises(ValueError):
                save_account(one,output)
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))),2)

    def test_refuse_writing_outside_private_data(self):
        account=Account.parse({
            "game":"world","profile_id":"perfil","account_id":"conta",
            "trainer_level":None,"roster":[],"active_pokemon_id":None,"hunts":[]
        })
        with self.assertRaises(ValueError):
            save_account(account,Path(__file__).resolve().parent/"unsafe.json")


if __name__=="__main__":
    unittest.main()
