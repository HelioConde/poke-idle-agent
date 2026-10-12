import unittest

from app.economy import (Opportunity, confirmed_withdrawal_usd, first_withdrawal_goal,
                         net_gems, pokemon_fee, recommend)


class EconomyTests(unittest.TestCase):
    def test_item_and_segmented_pokemon_fees(self):
        self.assertEqual(net_gems(100, "item", "completed"), 85)
        self.assertEqual(pokemon_fee(6000), 590)
        self.assertEqual(net_gems(6000, "pokemon", "completed"), 5410)

    def test_listing_is_not_a_sale_and_unconfirmed_is_not_usdt(self):
        self.assertIsNone(net_gems(500, "item", "listed"))
        self.assertIsNone(confirmed_withdrawal_usd(1000, False))
        self.assertEqual(confirmed_withdrawal_usd(1000, True), 7)

    def test_lower_xp_with_liquid_value_wins(self):
        high_xp = Opportunity("XP", 10000, 1, 0.2, 0.8, 3)
        liquid = Opportunity("Item procurado", 1000, 3, 0.9, 0.9, 3)
        result = recommend([high_xp, liquid])
        self.assertEqual(result["name"], "Item procurado")

    def test_missing_sales_requires_measurement(self):
        item = Opportunity("Raro", 1, 100, 1, 1, 0)
        self.assertEqual(recommend([item])["action"], "measure_more")

    def test_first_withdrawal_goal_never_confirms_without_manual_proof(self):
        in_progress = first_withdrawal_goal([100, 899])
        self.assertEqual(in_progress["remaining_net_gems"], 1)
        self.assertIsNone(in_progress["confirmed_usdt"])
        eligible = first_withdrawal_goal([1_000])
        self.assertEqual(eligible["status"], "eligible_for_manual_withdrawal")
        confirmed = first_withdrawal_goal([1_000], withdrawal_confirmed=True)
        self.assertEqual(confirmed["confirmed_usdt"], 7)


if __name__ == "__main__":
    unittest.main()
