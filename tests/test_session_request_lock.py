"""
`session_request_lock` の排他制御を検証するテスト。
Tests for session-scoped locking behavior in `session_request_lock`.
"""
import unittest

from backend.session_request_lock import (
    acquire_session_lock,
    release_session_lock,
    session_request_lock,
)


class SessionRequestLockTests(unittest.TestCase):
    """
    セッションロックの取得・解放・コンテキスト管理を確認する
    Verify acquire/release semantics and context-manager behavior.
    """
    def test_acquire_and_release(self):
        """
        EN: Test acquire and release behavior.
        JP: acquire and release の挙動を検証するテスト。
        """
        session_id = "test-session-lock-1"
        self.assertTrue(acquire_session_lock(session_id))
        self.assertFalse(acquire_session_lock(session_id))
        release_session_lock(session_id)
        self.assertTrue(acquire_session_lock(session_id))
        release_session_lock(session_id)

    def test_context_manager_releases_on_exit(self):
        """
        EN: Test context manager releases on exit behavior.
        JP: context manager releases on exit の挙動を検証するテスト。
        """
        session_id = "test-session-lock-2"
        with session_request_lock(session_id) as acquired:
            self.assertTrue(acquired)
            self.assertFalse(acquire_session_lock(session_id))
        self.assertTrue(acquire_session_lock(session_id))
        release_session_lock(session_id)

    def test_context_manager_does_not_release_foreign_lock(self):
        """
        EN: Test context manager does not release foreign lock behavior.
        JP: context manager does not release foreign lock の挙動を検証するテスト。
        """
        session_id = "test-session-lock-3"
        self.assertTrue(acquire_session_lock(session_id))
        with session_request_lock(session_id) as acquired:
            self.assertFalse(acquired)
        self.assertFalse(acquire_session_lock(session_id))
        release_session_lock(session_id)


if __name__ == "__main__":
    unittest.main()
