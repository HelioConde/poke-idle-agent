import tempfile
import unittest
from pathlib import Path

from app.memory import MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.directory.name) / "agent.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def test_persists_normalized_state_and_decision(self):
        self.store.record_observation(
            profile_id="profile-a", game="io", session_id="10:20",
            state={"level": 4, "xp_current": 50},
            decision={"mode": "dry_run", "action": "observe"},
            observed_at=1000,
        )
        restored = MemoryStore(self.store.path).history("profile-a", "10:20")
        self.assertEqual(restored[0]["state"]["xp_current"], 50)
        self.assertEqual(restored[0]["decision"]["action"], "observe")

    def test_history_never_mixes_profiles(self):
        for profile, value in (("profile-a", 10), ("profile-b", 20)):
            self.store.record_observation(
                profile_id=profile, game="io", session_id="10:20",
                state={"xp_current": value}, observed_at=1000,
            )
        history = self.store.history("profile-a", "10:20")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["state"]["xp_current"], 10)

    def test_rejects_invalid_identity_and_query_limit(self):
        with self.assertRaises(ValueError):
            self.store.record_observation(
                profile_id="", game="io", session_id="a", state={})
        with self.assertRaises(ValueError):
            self.store.history("profile-a", "10:20", limit=0)


if __name__ == "__main__":
    unittest.main()
