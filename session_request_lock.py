"""
Session-scoped in-process lock utilities.
"""

from contextlib import contextmanager
import threading
from typing import Dict, Iterator


_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def acquire_session_lock(session_id: str) -> bool:
    """
    Try to acquire a non-blocking lock for the given session.

    Returns True when lock is acquired, False when another request is in progress.
    """
    if not session_id:
        return False

    with _locks_guard:
        lock = _locks.get(session_id)
        if lock is None:
            lock = threading.Lock()
            _locks[session_id] = lock

    return lock.acquire(blocking=False)


def release_session_lock(session_id: str) -> None:
    """
    Release the lock for the given session if held and cleanup unused entries.
    """
    if not session_id:
        return

    with _locks_guard:
        lock = _locks.get(session_id)

    if lock is None:
        return

    if lock.locked():
        try:
            lock.release()
        except RuntimeError:
            return

    with _locks_guard:
        existing = _locks.get(session_id)
        if existing is lock and not existing.locked():
            _locks.pop(session_id, None)


@contextmanager
def session_request_lock(session_id: str) -> Iterator[bool]:
    """
    Context manager that acquires/releases a session lock safely.
    """
    acquired = acquire_session_lock(session_id)
    try:
        yield acquired
    finally:
        if acquired:
            release_session_lock(session_id)
