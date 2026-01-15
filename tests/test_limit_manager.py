import sys
import types
import unittest

sys.modules.setdefault("redis", types.SimpleNamespace(from_url=lambda *args, **kwargs: None))

import limit_manager


class FakeRedis:
    def __init__(self):
        self.store = {}

    def eval(self, _script, _numkeys, *args):
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
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value


class LimitManagerTests(unittest.TestCase):
    def setUp(self):
        self.original_redis = limit_manager.redis_client
        self.original_user_limits = dict(limit_manager.USER_TYPE_LIMITS)
        self.original_total_limit = limit_manager.TOTAL_DAILY_LIMIT
        import redis_client as redis_module
        self.redis_module = redis_module
        self.original_redis_module_client = redis_module.redis_client

        fake_redis = FakeRedis()
        limit_manager.redis_client = fake_redis
        redis_module.redis_client = fake_redis
        limit_manager.USER_TYPE_LIMITS = {"normal": 2, "premium": 5}
        limit_manager.TOTAL_DAILY_LIMIT = 3

    def tearDown(self):
        limit_manager.redis_client = self.original_redis
        limit_manager.USER_TYPE_LIMITS = self.original_user_limits
        limit_manager.TOTAL_DAILY_LIMIT = self.original_total_limit
        self.redis_module.redis_client = self.original_redis_module_client

    def test_user_limit_enforced(self):
        allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertEqual(limit, 2)
        self.assertEqual(user_type, "normal")
        self.assertFalse(total_exceeded)

        allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 2)
        self.assertFalse(total_exceeded)

        allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
            "session-a",
            user_type="normal",
        )
        self.assertFalse(allowed)
        self.assertEqual(limit, 2)
        self.assertFalse(total_exceeded)

    def test_total_limit_enforced(self):
        for index in range(3):
            allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
                f"session-{index}",
                user_type="normal",
            )
            self.assertTrue(allowed)
            self.assertFalse(total_exceeded)

        allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
            "session-extra",
            user_type="normal",
        )
        self.assertFalse(allowed)
        self.assertTrue(total_exceeded)

    def test_user_type_required(self):
        allowed, count, limit, user_type, total_exceeded = limit_manager.check_and_increment_limit(
            "session-missing"
        )
        self.assertFalse(allowed)
        self.assertEqual(user_type, "")
        self.assertFalse(total_exceeded)


if __name__ == "__main__":
    unittest.main()
