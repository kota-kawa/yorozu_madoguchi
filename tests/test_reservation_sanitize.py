import unittest

import reservation


class ReservationSanitizeTests(unittest.TestCase):
    def test_sanitize_field_trims_and_removes_control_chars(self):
        raw = "  hello\x00\x08 world  "
        self.assertEqual(reservation.sanitize_field(raw), "hello world")

    def test_sanitize_field_returns_none_for_empty(self):
        self.assertIsNone(reservation.sanitize_field("   "))
        self.assertIsNone(reservation.sanitize_field(None))

    def test_sanitize_field_respects_max_length(self):
        value = "a" * (reservation.MAX_FIELD_LENGTH + 10)
        sanitized = reservation.sanitize_field(value)
        self.assertEqual(len(sanitized), reservation.MAX_FIELD_LENGTH)

    def test_normalize_date_supports_slash_format(self):
        self.assertEqual(reservation.normalize_date("2025/1/2"), "2025-01-02")

    def test_normalize_date_supports_japanese_format(self):
        self.assertEqual(reservation.normalize_date("2025年1月2日"), "2025-01-02")

    def test_normalize_date_falls_back_to_clean_text(self):
        self.assertEqual(reservation.normalize_date("  未定 "), "未定")


if __name__ == "__main__":
    unittest.main()
