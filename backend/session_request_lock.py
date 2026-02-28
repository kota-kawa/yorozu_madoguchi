"""
セッション単位で同時リクエストを防ぐロックユーティリティ。
In-process lock utilities to prevent concurrent requests per session.
"""

from contextlib import contextmanager
import threading
from typing import Dict, Iterator


_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def acquire_session_lock(session_id: str) -> bool:
    """
    セッションID単位でノンブロッキングロック取得を試みる
    Try to acquire a non-blocking lock for the given session.

    ロック取得成功時は True、処理中リクエストがある場合は False を返します。
    Returns True when acquired, False if another request is already in progress.
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
    セッションロックを解放し、不要になったロック参照を掃除する
    Release the session lock and clean up unused lock entries.
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
    セッションロックを安全に取得・解放するコンテキストマネージャ
    Context manager that safely acquires and releases a session lock.
    """
    acquired = acquire_session_lock(session_id)
    try:
        yield acquired
    finally:
        if acquired:
            release_session_lock(session_id)
