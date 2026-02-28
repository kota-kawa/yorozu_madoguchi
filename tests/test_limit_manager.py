"""
`limit_manager` の日次制限ロジックを検証するテスト。
Tests for daily rate-limit behavior in `limit_manager`.
"""
import sys
import types
import unittest

sys.modules.setdefault("redis", types.SimpleNamespace(from_url=lambda *args, **kwargs: None))

from backend import limit_manager


class FakeRedis:
    """
    Redis `eval/get/set` の最小挙動を再現するテスト用スタブ。
    Minimal Redis stub that emulates `eval/get/set` behavior for tests.
    """
    def __init__(self):
        """
        内部カウンタ用のストアを初期化する
        Initialize in-memory state for counters.
        """
        self.store = {}

    def eval(self, _script, _numkeys, *args):
        """
        Lua相当のカウント更新を簡易再現する
        Simulate atomic counter updates equivalent to the Lua script.
        """
        user_key = args[0]
        total_key = args[1]
        user_limit = int(args[2])
        total_limit = int(args[3])

        user_val = self.store.get(user_key, 0) + 1
        total_val = self.store.get(total_key, 0) + 1
        self.store[user_key] = user_val
        self.store[total_key] = total_val

        if user_val > user_limit or total_val > total_limit:
            self.store[user_key] = self.store.get(user_key, 0) - 1
            self.store[total_key] = self.store.get(total_key, 0) - 1
            if total_val > total_limit:
                return -2
            return -1

        return user_val

    def get(self, key):
        """
        ストアから値を取得する
        Get a value from the stub store.
        """
        return self.store.get(key)

    def set(self, key, value):
        """
        ストアへ値を保存する
        Set a value in the stub store.
        """
        self.store[key] = value


class LimitManagerTests(unittest.TestCase):
    """
    `limit_manager.check_and_increment_limit` の振る舞いを検証する
    Validate behavior of `limit_manager.check_and_increment_limit`.
    """
    def setUp(self):
        """
        EN: Prepare test fixtures.
        JP: テストの前提データを準備する。
        """
        self.original_user_limits = dict(limit_manager.USER_TYPE_LIMITS)
        self.original_total_limit = limit_manager.TOTAL_DAILY_LIMIT
        from backend import redis_client as redis_module
        self.redis_module = redis_module
        self.original_redis_module_client = redis_module.redis_client

        fake_redis = FakeRedis()
        redis_module.redis_client = fake_redis
        limit_manager.USER_TYPE_LIMITS = {"normal": 2, "premium": 5}
        limit_manager.TOTAL_DAILY_LIMIT = 3

    def tearDown(self):
        """
        EN: Clean up test fixtures.
        JP: テスト後の状態をクリーンアップする。
        """
        limit_manager.USER_TYPE_LIMITS = self.original_user_limits
        limit_manager.TOTAL_DAILY_LIMIT = self.original_total_limit
        self.redis_module.redis_client = self.original_redis_module_client

    def test_user_limit_enforced(self):
        """
        EN: Test user limit enforced behavior.
        JP: user limit enforced の挙動を検証するテスト。
        """
        allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertEqual(limit, 2)
        self.assertEqual(user_type, "normal")
        self.assertFalse(total_exceeded)
        self.assertIsNone(error_code)

        allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 2)
        self.assertFalse(total_exceeded)
        self.assertIsNone(error_code)

        allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertFalse(allowed)
        self.assertEqual(limit, 2)
        self.assertFalse(total_exceeded)
        self.assertIsNone(error_code)

    def test_total_limit_enforced(self):
        """
        EN: Test total limit enforced behavior.
        JP: total limit enforced の挙動を検証するテスト。
        """
        for index in range(3):
            allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
                f"session-{index}",
                user_type="normal",
            )
            self.assertTrue(allowed)
            self.assertFalse(total_exceeded)
            self.assertIsNone(error_code)

        allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
            "session-extra",
            user_type="normal",
        )
        self.assertFalse(allowed)
        self.assertTrue(total_exceeded)
        self.assertIsNone(error_code)

    def test_user_type_required(self):
        """
        EN: Test user type required behavior.
        JP: user type required の挙動を検証するテスト。
        """
        allowed, count, limit, user_type, total_exceeded, error_code = limit_manager.check_and_increment_limit(
            "session-missing"
        )
        self.assertFalse(allowed)
        self.assertEqual(user_type, "")
        self.assertFalse(total_exceeded)
        self.assertIsNone(error_code)


if __name__ == "__main__":
    unittest.main()
