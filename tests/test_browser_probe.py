import unittest
from app.browser_probe import normalize_title, title_matches_game

class WindowTitleFilterTests(unittest.TestCase):
    def test_accent_title(self):
        self.assertTrue(title_matches_game("Pokéidle.io - Google Chrome", "io"))
    def test_plain_title(self):
        self.assertTrue(title_matches_game("PokeIdle — Microsoft Edge", "io"))
    def test_world_title(self):
        self.assertTrue(title_matches_game("Poke Idle World - Google Chrome", "world"))
    def test_google_login_not_captured(self):
        self.assertFalse(title_matches_game("Fazer login – Contas do Google - Chrome", "io"))
    def test_other_tabs_not_captured(self):
        self.assertFalse(title_matches_game("Gmail - Google Chrome", "io"))
        self.assertFalse(title_matches_game("Gmail - Google Chrome", "world"))
    def test_cross_game_not_captured(self):
        self.assertFalse(title_matches_game("Poke Idle World - Chrome", "io"))
        self.assertFalse(title_matches_game("PokeIdleWorld - Chrome", "io"))
        self.assertFalse(title_matches_game("Pokéidle.io - Chrome", "world"))
    def test_unicode_title(self):
        self.assertEqual(normalize_title("Pokéidle"), "pokeidle")

if __name__ == "__main__":
    unittest.main()
