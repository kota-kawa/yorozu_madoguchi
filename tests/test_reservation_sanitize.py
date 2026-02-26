"""
EN: Provide the test reservation sanitize module implementation.
JP: test_reservation_sanitize モジュールの実装を定義する。
"""
import unittest

import reservation


class ReservationSanitizeTests(unittest.TestCase):
    """
    EN: Define ReservationSanitizeTests test cases.
    JP: ReservationSanitizeTests のテストケースを定義する。
    """
    def test_sanitize_field_trims_and_removes_control_chars(self):
        """
        EN: Test sanitize field trims and removes control chars behavior.
        JP: sanitize field trims and removes control chars の挙動を検証するテスト。
        """
        raw = "  hello\x00\x08 world  "
        self.assertEqual(reservation.sanitize_field(raw), "hello world")

    def test_sanitize_field_returns_none_for_empty(self):
        """
        EN: Test sanitize field returns none for empty behavior.
        JP: sanitize field returns none for empty の挙動を検証するテスト。
        """
        self.assertIsNone(reservation.sanitize_field("   "))
        self.assertIsNone(reservation.sanitize_field(None))

    def test_sanitize_field_respects_max_length(self):
        """
        EN: Test sanitize field respects max length behavior.
        JP: sanitize field respects max length の挙動を検証するテスト。
        """
        value = "a" * (reservation.MAX_FIELD_LENGTH + 10)
        sanitized = reservation.sanitize_field(value)
        self.assertEqual(len(sanitized), reservation.MAX_FIELD_LENGTH)

    def test_normalize_date_supports_slash_format(self):
        """
        EN: Test normalize date supports slash format behavior.
        JP: normalize date supports slash format の挙動を検証するテスト。
        """
        self.assertEqual(reservation.normalize_date("2025/1/2"), "2025-01-02")

    def test_normalize_date_supports_japanese_format(self):
        """
        EN: Test normalize date supports japanese format behavior.
        JP: normalize date supports japanese format の挙動を検証するテスト。
        """
        self.assertEqual(reservation.normalize_date("2025年1月2日"), "2025-01-02")

    def test_normalize_date_falls_back_to_clean_text(self):
        """
        EN: Test normalize date falls back to clean text behavior.
        JP: normalize date falls back to clean text の挙動を検証するテスト。
        """
        self.assertEqual(reservation.normalize_date("  未定 "), "未定")


if __name__ == "__main__":
    unittest.main()
