import importlib
import os
import sys
import types
import unittest


class _DummyRedisBackend:
    def __init__(self):
        self.store = {}

    def setex(self, key, _ttl, value):
        self.store[key] = value

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    def eval(self, *_args, **_kwargs):
        return 1


class _StubRedisModule:
    def __init__(self):
        self.reset_sessions = []
        self.saved_user_types = {}

    def reset_session(self, session_id):
        self.reset_sessions.append(session_id)

    def save_user_type(self, session_id, user_type):
        self.saved_user_types[session_id] = user_type


class ApiE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_modules = {name: sys.modules.get(name) for name in ("redis", "llama_core", "reservation")}

        redis_stub = types.SimpleNamespace(from_url=lambda *args, **kwargs: _DummyRedisBackend())
        llama_stub = types.SimpleNamespace(
            chat_with_llama=lambda _session_id, _prompt, mode="travel": (
                f"{mode}-ok",
                "plan",
                None,
                None,
                False,
                "remaining",
            )
        )
        reservation_stub = types.SimpleNamespace(
            complete_plan=lambda _session_id: "Complete!",
        )

        sys.modules["redis"] = redis_stub
        sys.modules["llama_core"] = llama_stub
        sys.modules["reservation"] = reservation_stub

        import database

        cls._orig_init_db = database.init_db
        database.init_db = lambda: None

        cls.run_module = importlib.import_module("run")

        database.init_db = cls._orig_init_db

        for name, module in cls._orig_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def setUp(self):
        self._env_backup = os.environ.copy()
        self.redis_stub = _StubRedisModule()

        import reply.reply_main as reply_main
        import travel.travel_main as travel_main
        import fitness.fitness_main as fitness_main
        import limit_manager

        self._modules = {
            "run": self.run_module,
            "reply_main": reply_main,
            "travel_main": travel_main,
            "fitness_main": fitness_main,
        }

        self._originals = {}
        for key, module in self._modules.items():
            self._originals[(key, "redis_client")] = module.redis_client
            module.redis_client = self.redis_stub

        self._orig_limit_check = limit_manager.check_and_increment_limit
        limit_manager.check_and_increment_limit = lambda *_args, **_kwargs: (
            True,
            1,
            10,
            "normal",
            False,
            None,
        )

        self.app = self.run_module.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        import limit_manager
        limit_manager.check_and_increment_limit = self._orig_limit_check

        for (key, attr), value in self._originals.items():
            module = self._modules[key]
            if attr == "redis_client":
                module.redis_client = value

        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_api_reset_requires_csrf(self):
        response = self.client.post("/api/reset")
        self.assertEqual(response.status_code, 403)

    def test_api_reset_success_sets_cookie(self):
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/reset", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "reset")
        self.assertIn("session_id=", response.headers.get("Set-Cookie", ""))
        self.assertEqual(len(self.redis_stub.reset_sessions), 1)

    def test_api_user_type_success(self):
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/user_type", json={"user_type": "normal"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user_type"], "normal")
        self.assertEqual(list(self.redis_stub.saved_user_types.values()), ["normal"])

    def test_api_user_type_rejects_invalid(self):
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/user_type", json={"user_type": "invalid"}, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_reply_send_message_success(self):
        headers = {"Origin": "http://localhost:5173"}
        self.client.set_cookie("localhost", "session_id", "session-123")
        response = self.client.post(
            "/reply_send_message",
            json={"message": "hello", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["response"], "reply-ok")
        self.assertEqual(payload["remaining_text"], "remaining")

    def test_travel_send_message_requires_session(self):
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post(
            "/travel_send_message",
            json={"message": "hello", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_fitness_send_message_success(self):
        headers = {"Origin": "http://localhost:5173"}
        self.client.set_cookie("localhost", "session_id", "session-999")
        response = self.client.post(
            "/fitness_send_message",
            json={"message": "hi", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["response"], "fitness-ok")


if __name__ == "__main__":
    unittest.main()
