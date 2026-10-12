import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.tab_registry import Registry, create_handler

PROFILE = "d57c56d9-6dcb-43e2-8ddf-f2014aa60fb2"
ORIGIN = "chrome-extension://" + "a" * 32


def payload(active=False):
    return {
        "profile_id": PROFILE, "profile_label": "Conta de teste",
        "tabs": [{"game": "io", "tab_id": 12, "window_id": 3,
                  "title": "Pokéidle.io", "active": active}]
    }


class RegistryUnitTests(unittest.TestCase):
    def test_inactive_tab_is_kept(self):
        registry = Registry("some-token")
        registry.ingest(payload(active=False))
        tabs = registry.snapshot()["tabs"]
        self.assertEqual(len(tabs), 1)
        self.assertFalse(tabs[0]["active"])

    def test_update_same_tab_without_duplication(self):
        registry = Registry("some-token")
        registry.ingest(payload(False))
        registry.ingest(payload(True))
        self.assertEqual(len(registry.snapshot()["tabs"]), 1)
        self.assertTrue(registry.snapshot()["tabs"][0]["active"])

    def test_multiple_profiles_are_independent(self):
        registry = Registry("some-token")
        first = payload()
        second = payload()
        second["profile_id"] = "e57c56d9-6dcb-43e2-8ddf-f2014aa60fb2"
        second["profile_label"] = "Segundo perfil"
        registry.ingest(first)
        registry.ingest(second)
        self.assertEqual(registry.snapshot()["profiles"], 2)
        self.assertEqual(len(registry.snapshot()["tabs"]), 2)

    def test_empty_profile_removes_tabs(self):
        registry = Registry("some-token")
        registry.ingest(payload())
        blank = payload()
        blank["tabs"] = []
        registry.ingest(blank)
        self.assertEqual(registry.snapshot()["tabs"], [])

    def test_reject_duplicate_tabs(self):
        registry = Registry("some-token")
        data = payload()
        data["tabs"].append(data["tabs"][0].copy())
        with self.assertRaises(ValueError):
            registry.ingest(data)

    def test_reject_unexpected_game_and_malformed_id(self):
        registry = Registry("some-token")
        data = payload()
        data["tabs"][0]["game"] = "banking"
        with self.assertRaises(ValueError):
            registry.ingest(data)
        data = payload()
        data["profile_id"] = "test"
        with self.assertRaises(ValueError):
            registry.ingest(data)


class RegistryApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry("private-test-token-long-enough-123")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0),
                                         create_handler(cls.registry))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def post(self, origin, key):
        request = Request(self.endpoint + "/api/sync",
                          data=json.dumps(payload()).encode(),
                          headers={"Content-Type": "application/json",
                                   "Origin": origin, "X-IGA-Token": key},
                          method="POST")
        try:
            with urlopen(request, timeout=5) as response:
                return response.status
        except HTTPError as exc:
            return exc.code

    def test_chrome_extension_can_sync(self):
        self.assertEqual(self.post(ORIGIN, self.registry.token), 200)
        with urlopen(self.endpoint + "/api/tabs") as response:
            data = json.load(response)
        self.assertGreaterEqual(len(data["tabs"]), 1)

    def test_untrusted_websites_cannot_submit(self):
        self.assertEqual(self.post("https://evil.example", self.registry.token), 403)

    def test_incorrect_token_rejected(self):
        self.assertEqual(self.post(ORIGIN, "incorrect"), 401)

    def test_preflight_allowed_only_for_extensions(self):
        request = Request(self.endpoint + "/api/sync", method="OPTIONS",
                          headers={"Origin": ORIGIN,
                                   "Access-Control-Request-Method": "POST"})
        with urlopen(request) as response:
            self.assertEqual(response.status, 204)
        wrong = Request(self.endpoint + "/api/sync", method="OPTIONS",
                        headers={"Origin": "https://evil.example"})
        with self.assertRaises(HTTPError):
            urlopen(wrong)

    def test_history_query_rejects_invalid_parameters(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.endpoint + "/api/history?profile_id=wrong&window_id=x&tab_id=1")
        self.assertEqual(caught.exception.code, 400)

    def test_history_query_accepts_known_tab_identity(self):
        urlopen(Request(self.endpoint + "/api/sync", data=json.dumps(payload()).encode(),
                        headers={"Content-Type": "application/json", "Origin": ORIGIN,
                                 "X-IGA-Token": self.registry.token}, method="POST"))
        with urlopen(self.endpoint + "/api/history?profile_id=" + PROFILE +
                     "&window_id=3&tab_id=12") as response:
            self.assertEqual(json.load(response), [])


if __name__ == "__main__":
    unittest.main()
