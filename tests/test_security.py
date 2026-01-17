import os
import unittest

from flask import Flask, request

import security


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self._env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_allowed_origins_includes_defaults(self):
        os.environ["ALLOWED_ORIGINS"] = "https://example.com"
        allowed = security.get_allowed_origins()
        self.assertIn("https://example.com", allowed)
        self.assertIn("https://chat.project-kk.com", allowed)
        self.assertIn("http://localhost:5173", allowed)

    def test_csrf_valid_allows_get(self):
        with self.app.test_request_context("/api/test", method="GET"):
            self.assertTrue(security.is_csrf_valid(request))

    def test_csrf_valid_with_origin(self):
        headers = {"Origin": "http://localhost:5173"}
        with self.app.test_request_context("/api/test", method="POST", headers=headers):
            self.assertTrue(security.is_csrf_valid(request))

    def test_csrf_invalid_missing_origin(self):
        os.environ["ALLOW_MISSING_ORIGIN"] = "false"
        with self.app.test_request_context("/api/test", method="POST"):
            self.assertFalse(security.is_csrf_valid(request))

    def test_csrf_allows_missing_origin_when_enabled(self):
        os.environ["ALLOW_MISSING_ORIGIN"] = "true"
        with self.app.test_request_context("/api/test", method="POST"):
            self.assertTrue(security.is_csrf_valid(request))

    def test_cookie_settings_on_localhost(self):
        headers = {"Host": "localhost:5173"}
        with self.app.test_request_context("/", headers=headers):
            settings = security.cookie_settings(request)
            self.assertFalse(settings["secure"])
            self.assertTrue(settings["httponly"])
            self.assertEqual(settings["path"], "/")

    def test_security_headers_applied(self):
        response = self.app.response_class("ok")
        response = security.apply_security_headers(response)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", response.headers)


if __name__ == "__main__":
    unittest.main()
