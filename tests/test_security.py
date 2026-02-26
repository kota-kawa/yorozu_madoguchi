"""
EN: Provide the test security module implementation.
JP: test_security モジュールの実装を定義する。
"""
import os
import unittest

from flask import Flask, request

import security


class SecurityTests(unittest.TestCase):
    """
    EN: Define SecurityTests test cases.
    JP: SecurityTests のテストケースを定義する。
    """
    def setUp(self):
        """
        EN: Prepare test fixtures.
        JP: テストの前提データを準備する。
        """
        self.app = Flask(__name__)
        self._env_backup = os.environ.copy()

    def tearDown(self):
        """
        EN: Clean up test fixtures.
        JP: テスト後の状態をクリーンアップする。
        """
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_allowed_origins_includes_defaults(self):
        """
        EN: Test allowed origins includes defaults behavior.
        JP: allowed origins includes defaults の挙動を検証するテスト。
        """
        os.environ["ALLOWED_ORIGINS"] = "https://example.com"
        allowed = security.get_allowed_origins()
        self.assertIn("https://example.com", allowed)
        self.assertIn("https://chat.project-kk.com", allowed)
        self.assertIn("http://localhost:5173", allowed)

    def test_csrf_valid_allows_get(self):
        """
        EN: Test csrf valid allows get behavior.
        JP: csrf valid allows get の挙動を検証するテスト。
        """
        with self.app.test_request_context("/api/test", method="GET"):
            self.assertTrue(security.is_csrf_valid(request))

    def test_csrf_valid_with_origin(self):
        """
        EN: Test csrf valid with origin behavior.
        JP: csrf valid with origin の挙動を検証するテスト。
        """
        headers = {"Origin": "http://localhost:5173"}
        with self.app.test_request_context("/api/test", method="POST", headers=headers):
            self.assertTrue(security.is_csrf_valid(request))

    def test_csrf_invalid_missing_origin(self):
        """
        EN: Test csrf invalid missing origin behavior.
        JP: csrf invalid missing origin の挙動を検証するテスト。
        """
        os.environ["ALLOW_MISSING_ORIGIN"] = "false"
        with self.app.test_request_context("/api/test", method="POST"):
            self.assertFalse(security.is_csrf_valid(request))

    def test_csrf_allows_missing_origin_when_enabled(self):
        """
        EN: Test csrf allows missing origin when enabled behavior.
        JP: csrf allows missing origin when enabled の挙動を検証するテスト。
        """
        os.environ["ALLOW_MISSING_ORIGIN"] = "true"
        with self.app.test_request_context("/api/test", method="POST"):
            self.assertTrue(security.is_csrf_valid(request))

    def test_cookie_settings_on_localhost(self):
        """
        EN: Test cookie settings on localhost behavior.
        JP: cookie settings on localhost の挙動を検証するテスト。
        """
        headers = {"Host": "localhost:5173"}
        with self.app.test_request_context("/", headers=headers):
            settings = security.cookie_settings(request)
            self.assertFalse(settings["secure"])
            self.assertTrue(settings["httponly"])
            self.assertEqual(settings["path"], "/")

    def test_security_headers_applied(self):
        """
        EN: Test security headers applied behavior.
        JP: security headers applied の挙動を検証するテスト。
        """
        response = self.app.response_class("ok")
        response = security.apply_security_headers(response)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", response.headers)


if __name__ == "__main__":
    unittest.main()
