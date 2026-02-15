import unittest

from session_request_lock import acquire_session_lock, release_session_lock, session_request_lock


class SessionRequestLockTests(unittest.TestCase):
    def test_acquire_and_release(self):
        session_id = "test-session-lock-1"
        self.assertTrue(acquire_session_lock(session_id))
        self.assertFalse(acquire_session_lock(session_id))
        release_session_lock(session_id)
        self.assertTrue(acquire_session_lock(session_id))
        release_session_lock(session_id)

    def test_context_manager_releases_on_exit(self):
        session_id = "test-session-lock-2"
        with session_request_lock(session_id) as acquired:
            self.assertTrue(acquired)
            self.assertFalse(acquire_session_lock(session_id))
        self.assertTrue(acquire_session_lock(session_id))
        release_session_lock(session_id)

    def test_context_manager_does_not_release_foreign_lock(self):
        session_id = "test-session-lock-3"
        self.assertTrue(acquire_session_lock(session_id))
        with session_request_lock(session_id) as acquired:
            self.assertFalse(acquired)
        self.assertFalse(acquire_session_lock(session_id))
        release_session_lock(session_id)


if __name__ == "__main__":
    unittest.main()
