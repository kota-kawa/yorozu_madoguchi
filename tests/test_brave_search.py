"""
Brave Search クライアントの単体テスト。
Unit tests for the Brave Search client.
"""

import os
import unittest

from backend import brave_search


class BraveSearchTests(unittest.TestCase):
    """
    EN: Validate brave_search helper behavior.
    JP: brave_search ヘルパーの挙動を検証する。
    """

    def setUp(self):
        """
        EN: Prepare test fixtures.
        JP: テスト前の状態を準備する。
        """
        self._env_backup = os.environ.copy()

    def tearDown(self):
        """
        EN: Clean up test fixtures.
        JP: テスト後の状態を復元する。
        """
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_is_configured_false_when_token_missing(self):
        """
        EN: Test missing token returns false.
        JP: トークン未設定時に false を返すことを検証する。
        """
        os.environ.pop("BRAVE_SEARCH_API", None)
        self.assertFalse(brave_search.is_configured())

    def test_resolve_result_count_clamps_bounds(self):
        """
        EN: Test result count is clamped.
        JP: 検索件数が上限下限で丸められることを検証する。
        """
        self.assertEqual(brave_search._resolve_result_count(0), 1)
        self.assertEqual(brave_search._resolve_result_count(999), brave_search.MAX_RESULT_COUNT)

    def test_normalize_results_filters_invalid_items(self):
        """
        EN: Test invalid result entries are skipped.
        JP: 不正な結果エントリを除外することを検証する。
        """
        payload = {
            "web": {
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "description": "desc",
                    },
                    {"title": "No URL"},
                    "invalid",
                ]
            }
        }

        normalized = brave_search._normalize_results(payload)
        self.assertEqual(
            normalized,
            [
                {
                    "title": "Example",
                    "url": "https://example.com",
                    "description": "desc",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

