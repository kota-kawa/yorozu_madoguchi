"""
主要APIエンドポイントのE2E挙動を検証するテスト。
E2E tests for the application's main API endpoints.
"""
import importlib
import os
import sys
import types
import unittest


class _DummyRedisBackend:
    """
    テスト用の最小Redisバックエンド（インメモリ）実装。
    Minimal in-memory Redis backend used for E2E stubbing.
    """
    def __init__(self):
        """
        キー値保存用ストアを初期化する
        Initialize key-value storage for the stub backend.
        """
        self.store = {}

    def setex(self, key, _ttl, value):
        """
        TTL引数付き保存を模倣して値を保存する
        Store a value while mimicking `setex` signature.
        """
        self.store[key] = value

    def set(self, key, value):
        """
        値を保存する
        Store a value.
        """
        self.store[key] = value

    def get(self, key):
        """
        値を取得する
        Retrieve a value.
        """
        return self.store.get(key)

    def delete(self, *keys):
        """
        指定キーを削除する
        Delete one or more keys.
        """
        for key in keys:
            self.store.pop(key, None)

    def eval(self, *_args, **_kwargs):
        """
        レート制限Lua呼び出しを成功扱いで返す
        Return a success-like value for Lua eval calls.
        """
        return 1


class _StubRedisModule:
    """
    APIテスト用に呼び出し履歴を保持するRedisモジュールスタブ。
    Redis module stub that records calls during API tests.
    """
    def __init__(self):
        """
        セッション操作の記録領域を初期化する
        Initialize storage for recorded session operations.
        """
        self.reset_sessions = []
        self.saved_user_types = {}
        self.saved_user_languages = {}

    def reset_session(self, session_id):
        """
        リセット対象セッションを記録する
        Record session IDs passed to reset_session.
        """
        self.reset_sessions.append(session_id)

    def save_user_type(self, session_id, user_type):
        """
        保存要求されたユーザー種別を記録する
        Record user types passed to save_user_type.
        """
        self.saved_user_types[session_id] = user_type

    def get_user_language(self, _session_id):
        return ""

    def save_user_language(self, session_id, language):
        self.saved_user_languages[session_id] = language


class ApiE2ETests(unittest.TestCase):
    """
    Flask APIのCSRF・セッション・正常系を網羅するE2Eテスト群。
    E2E test cases covering CSRF, session handling, and success paths.
    """
    @classmethod
    def setUpClass(cls):
        """
        EN: Prepare test fixtures.
        JP: テストの前提データを準備する。
        """
        os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
        cls._orig_modules = {
            name: sys.modules.get(name)
            for name in ("redis", "backend.llama_core", "backend.reservation")
        }

        redis_stub = types.SimpleNamespace(from_url=lambda *args, **kwargs: _DummyRedisBackend())
        llama_stub = types.SimpleNamespace(
            resolve_user_language=lambda _message, fallback=None, accept_language=None: fallback or "ja",
            chat_with_llama=lambda _session_id, _prompt, mode="travel", language=None: (
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
        sys.modules["backend.llama_core"] = llama_stub
        sys.modules["backend.reservation"] = reservation_stub

        import backend.database as database

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
        """
        EN: Prepare test fixtures.
        JP: テストの前提データを準備する。
        """
        self._env_backup = os.environ.copy()
        self.redis_stub = _StubRedisModule()

        import backend.app as backend_app
        import backend.routes.reply as reply_main
        import backend.routes.travel as travel_main
        import backend.routes.fitness as fitness_main
        import backend.routes.job as job_main
        import backend.routes.study as study_main
        from backend import limit_manager

        self._modules = {
            "app": backend_app,
            "reply_main": reply_main,
            "travel_main": travel_main,
            "fitness_main": fitness_main,
            "job_main": job_main,
            "study_main": study_main,
        }

        self._originals = {}
        for key, module in self._modules.items():
            if hasattr(module, "redis_client"):
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
        """
        EN: Clean up test fixtures.
        JP: テスト後の状態をクリーンアップする。
        """
        from backend import limit_manager
        limit_manager.check_and_increment_limit = self._orig_limit_check

        for (key, attr), value in self._originals.items():
            module = self._modules[key]
            if attr == "redis_client":
                module.redis_client = value

        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_api_reset_requires_csrf(self):
        """
        EN: Test api reset requires csrf behavior.
        JP: api reset requires csrf の挙動を検証するテスト。
        """
        response = self.client.post("/api/reset")
        self.assertEqual(response.status_code, 403)

    def test_api_reset_success_sets_cookie(self):
        """
        EN: Test api reset success sets cookie behavior.
        JP: api reset success sets cookie の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/reset", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "reset")
        self.assertIn("session_id=", response.headers.get("Set-Cookie", ""))
        self.assertEqual(len(self.redis_stub.reset_sessions), 1)

    def test_api_user_type_success(self):
        """
        EN: Test api user type success behavior.
        JP: api user type success の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/user_type", json={"user_type": "normal"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user_type"], "normal")
        self.assertEqual(list(self.redis_stub.saved_user_types.values()), ["normal"])

    def test_api_user_type_rejects_invalid(self):
        """
        EN: Test api user type rejects invalid behavior.
        JP: api user type rejects invalid の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/user_type", json={"user_type": "invalid"}, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_api_user_type_rejects_non_string(self):
        """
        EN: Test api user type rejects non string behavior.
        JP: api user type rejects non string の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post("/api/user_type", json={"user_type": 1}, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_reply_send_message_success(self):
        """
        EN: Test reply send message success behavior.
        JP: reply send message success の挙動を検証するテスト。
        """
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
        """
        EN: Test travel send message requires session behavior.
        JP: travel send message requires session の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.post(
            "/travel_send_message",
            json={"message": "hello", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_fitness_send_message_success(self):
        """
        EN: Test fitness send message success behavior.
        JP: fitness send message success の挙動を検証するテスト。
        """
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

    def test_job_send_message_success(self):
        """
        EN: Test job send message success behavior.
        JP: job send message success の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        self.client.set_cookie("localhost", "session_id", "session-777")
        response = self.client.post(
            "/job_send_message",
            json={"message": "hi", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["response"], "job-ok")

    def test_study_send_message_success(self):
        """
        EN: Test study send message success behavior.
        JP: study send message success の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        self.client.set_cookie("localhost", "session_id", "session-888")
        response = self.client.post(
            "/study_send_message",
            json={"message": "hi", "user_type": "normal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["response"], "study-ok")


if __name__ == "__main__":
    unittest.main()
