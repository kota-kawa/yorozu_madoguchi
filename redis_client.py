"""
Redisアクセスと簡易フォールバック（インメモリ）の管理。
Redis access and a lightweight in-memory fallback.
"""

import os
import json
import redis
import logging
import time
import threading
from typing import Dict, List, Optional, Sequence, Tuple, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


try:
    REDIS_SESSION_TTL_SECONDS = int(os.getenv("REDIS_SESSION_TTL_SECONDS", "172800"))
except ValueError:
    REDIS_SESSION_TTL_SECONDS = 172800

REDIS_SOCKET_TIMEOUT_SECONDS = _env_float("REDIS_SOCKET_TIMEOUT_SECONDS", 2.0)
REDIS_CONNECT_TIMEOUT_SECONDS = _env_float("REDIS_CONNECT_TIMEOUT_SECONDS", 2.0)
REDIS_HEALTH_CHECK_INTERVAL = _env_int("REDIS_HEALTH_CHECK_INTERVAL", 30)
REDIS_RECONNECT_RETRIES = _env_int("REDIS_RECONNECT_RETRIES", 5)
REDIS_RECONNECT_INITIAL_DELAY_SECONDS = _env_float("REDIS_RECONNECT_INITIAL_DELAY_SECONDS", 0.5)
REDIS_RECONNECT_MAX_DELAY_SECONDS = _env_float("REDIS_RECONNECT_MAX_DELAY_SECONDS", 5.0)
REDIS_RECONNECT_MIN_INTERVAL_SECONDS = _env_float("REDIS_RECONNECT_MIN_INTERVAL_SECONDS", 2.0)
REDIS_FAIL_FAST = _env_bool("REDIS_FAIL_FAST", False)
REDIS_ALLOW_FALLBACK = _env_bool("REDIS_ALLOW_FALLBACK", True)

# Redisクライアントの状態管理
# Redis client state tracking
redis_client: Optional[Any] = None
_redis_lock = threading.Lock()
_last_health_check = 0.0
_last_reconnect_attempt = 0.0

# Redisが使えない場合の簡易フォールバック（単一プロセス限定）
# In-memory fallback when Redis is unavailable (single-process only)
_memory_store: Dict[str, Tuple[str, Optional[float]]] = {}


def _should_use_fallback() -> bool:
    if REDIS_FAIL_FAST:
        return False
    return REDIS_ALLOW_FALLBACK


def _supports_ping(client: Any) -> bool:
    return hasattr(client, "ping") and callable(getattr(client, "ping"))


def _ping_if_available(client: Any) -> None:
    if _supports_ping(client):
        client.ping()


def _fail_fast(reason: str, err: Optional[Exception] = None) -> None:
    if not REDIS_FAIL_FAST:
        return
    if err is not None:
        logger.critical("Redis unavailable (%s): %s", reason, err, exc_info=True)
    else:
        logger.critical("Redis unavailable (%s)", reason)
    os._exit(1)


def _create_redis_client() -> Optional[Any]:
    try:
        client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
            retry_on_timeout=True,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL,
        )
        _ping_if_available(client)
        return client
    except Exception as e:
        logger.error("Failed to connect to Redis: %s", e)
        return None


def _connect_with_retries() -> Optional[Any]:
    retries = max(1, REDIS_RECONNECT_RETRIES)
    delay = max(0.0, REDIS_RECONNECT_INITIAL_DELAY_SECONDS)

    for attempt in range(1, retries + 1):
        client = _create_redis_client()
        if client is not None:
            return client
        if attempt < retries:
            sleep_for = min(delay, REDIS_RECONNECT_MAX_DELAY_SECONDS)
            if sleep_for > 0:
                time.sleep(sleep_for)
            delay = min(max(delay * 2, 0.1), REDIS_RECONNECT_MAX_DELAY_SECONDS)
    return None


def _health_check_due(now: float) -> bool:
    if REDIS_HEALTH_CHECK_INTERVAL <= 0:
        return False
    return now - _last_health_check >= REDIS_HEALTH_CHECK_INTERVAL


def _mark_unhealthy(reason: str, err: Optional[Exception] = None) -> None:
    global redis_client, _last_health_check
    if err is not None:
        logger.error("Redis %s failed: %s", reason, err, exc_info=True)
    else:
        logger.error("Redis %s failed", reason)
    with _redis_lock:
        redis_client = None
        _last_health_check = 0.0
    _fail_fast(reason, err)


def get_redis_client() -> Optional[Any]:
    global redis_client, _last_health_check, _last_reconnect_attempt
    now = time.time()

    with _redis_lock:
        client = redis_client
        if client is not None:
            if _health_check_due(now):
                _last_health_check = now
                try:
                    _ping_if_available(client)
                except Exception as e:
                    redis_client = None
                    client = None
                    logger.warning("Redis health check failed: %s", e)

        if client is not None:
            return client

        if not REDIS_FAIL_FAST and now - _last_reconnect_attempt < REDIS_RECONNECT_MIN_INTERVAL_SECONDS:
            return None
        _last_reconnect_attempt = now

        client = _connect_with_retries()
        if client is not None:
            redis_client = client
            _last_health_check = now
            return client

    _fail_fast("reconnect")
    return None


def _memory_set(key: str, value: str) -> None:
    ttl = REDIS_SESSION_TTL_SECONDS if REDIS_SESSION_TTL_SECONDS > 0 else None
    expires_at = time.time() + ttl if ttl else None
    _memory_store[key] = (value, expires_at)


def _memory_get(key: str) -> Optional[str]:
    item = _memory_store.get(key)
    if not item:
        return None
    value, expires_at = item
    if expires_at and time.time() > expires_at:
        _memory_store.pop(key, None)
        return None
    return value


def _memory_delete(*keys: str) -> None:
    for key in keys:
        _memory_store.pop(key, None)


def get_session_key(session_id: str, key_type: str) -> str:
    """
    セッションIDに基づいたRedisキーを生成する
    Build a Redis key from session ID and key type.

    例: session:abc-123:chat_history
    Example: session:abc-123:chat_history
    """
    return f"session:{session_id}:{key_type}"


def _set_with_ttl(key: str, value: str) -> None:
    """
    TTL（有効期限）付きで値を設定するヘルパー関数
    Helper to set a value with TTL.
    """
    client = get_redis_client()
    if not client:
        if _should_use_fallback():
            _memory_set(key, value)
        return
    try:
        if REDIS_SESSION_TTL_SECONDS > 0:
            client.setex(key, REDIS_SESSION_TTL_SECONDS, value)
        else:
            client.set(key, value)
    except Exception as e:
        _mark_unhealthy("set", e)
        if _should_use_fallback():
            _memory_set(key, value)


def get_chat_history(session_id: str) -> List[Tuple[str, str]]:
    """
    指定されたセッションIDのチャット履歴を取得する
    Fetch chat history for a session.

    履歴はJSONリスト形式で保存されており、取得時にタプルのリストへ変換します。
    戻り値: [(role, text), ...]
    Stored as a JSON list and returned as [(role, text), ...].
    """
    key = get_session_key(session_id, "chat_history")
    try:
        client = get_redis_client()
        if client:
            data = client.get(key)
        else:
            if _should_use_fallback():
                logger.warning("Redis client is not available; using in-memory fallback.")
                data = _memory_get(key)
            else:
                data = None
        if data:
            # JSONのリスト[role, text]をタプル(role, text)に変換
            # Convert JSON list [role, text] to tuples
            return [tuple(item) for item in json.loads(data)]
    except Exception as e:
        _mark_unhealthy("get", e)
        if _should_use_fallback():
            data = _memory_get(key)
            if data:
                return [tuple(item) for item in json.loads(data)]

    return []


def save_chat_history(session_id: str, chat_history: Sequence[Tuple[str, str]]) -> None:
    """
    指定されたセッションIDのチャット履歴を保存する
    Save chat history for a session.

    リスト形式の履歴をJSON文字列にシリアライズしてRedisに保存します。
    Serializes the list to JSON and stores it in Redis.
    """
    key = get_session_key(session_id, "chat_history")
    try:
        _set_with_ttl(key, json.dumps(chat_history, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Error saving chat history for {session_id}: {e}")


def get_decision(session_id: str) -> str:
    """
    指定されたセッションIDの決定事項（構造化前のテキスト）を取得する
    Fetch decision text (unstructured) for a session.
    """
    key = get_session_key(session_id, "decision")
    try:
        client = get_redis_client()
        if client:
            data = client.get(key)
        else:
            if _should_use_fallback():
                logger.warning("Redis client is not available; using in-memory fallback.")
                data = _memory_get(key)
            else:
                data = None
        return data if data else ""
    except Exception as e:
        _mark_unhealthy("get", e)
        if _should_use_fallback():
            return _memory_get(key) or ""
        return ""


def save_decision(session_id: str, decision_text: str) -> None:
    """
    指定されたセッションIDの決定事項を保存する
    Save decision text for a session.
    """
    key = get_session_key(session_id, "decision")
    try:
        _set_with_ttl(key, decision_text)
    except Exception as e:
        logger.error(f"Error saving decision for {session_id}: {e}")


def reset_session(session_id: str) -> None:
    """
    指定されたセッションIDに関連する全データを削除する
    Delete all data associated with a session ID.

    チャット履歴や決定事項など、セッションに関連するキーをまとめて削除します。
    Removes chat history, decisions, and other session keys.
    """
    keys = [
        get_session_key(session_id, "chat_history"),
        get_session_key(session_id, "decision"),
        get_session_key(session_id, "user_language"),
        get_session_key(session_id, "user_type"),
    ]
    try:
        client = get_redis_client()
        if client:
            client.delete(*keys)
        elif _should_use_fallback():
            _memory_delete(*keys)
    except Exception as e:
        _mark_unhealthy("delete", e)
        if _should_use_fallback():
            _memory_delete(*keys)


def get_user_type(session_id: str) -> str:
    """指定されたセッションIDのユーザー種別を取得する / Get user type for a session."""
    key = get_session_key(session_id, "user_type")
    try:
        client = get_redis_client()
        if client:
            data = client.get(key)
        else:
            if _should_use_fallback():
                logger.warning("Redis client is not available; using in-memory fallback.")
                data = _memory_get(key)
            else:
                data = None
        return data if data else ""
    except Exception as e:
        _mark_unhealthy("get", e)
        if _should_use_fallback():
            return _memory_get(key) or ""
        return ""


def save_user_type(session_id: str, user_type: str) -> None:
    """指定されたセッションIDのユーザー種別を保存する / Save user type for a session."""
    key = get_session_key(session_id, "user_type")
    try:
        _set_with_ttl(key, user_type)
    except Exception as e:
        logger.error(f"Error saving user_type for {session_id}: {e}")


def get_user_language(session_id: str) -> str:
    """指定されたセッションIDのユーザー言語を取得する / Get user language for a session."""
    key = get_session_key(session_id, "user_language")
    try:
        client = get_redis_client()
        if client:
            data = client.get(key)
        else:
            if _should_use_fallback():
                logger.warning("Redis client is not available; using in-memory fallback.")
                data = _memory_get(key)
            else:
                data = None
        return data if data else ""
    except Exception as e:
        _mark_unhealthy("get", e)
        if _should_use_fallback():
            return _memory_get(key) or ""
        return ""


def save_user_language(session_id: str, language: str) -> None:
    """指定されたセッションIDのユーザー言語を保存する / Save user language for a session."""
    key = get_session_key(session_id, "user_language")
    try:
        _set_with_ttl(key, language)
    except Exception as e:
        logger.error(f"Error saving user_language for {session_id}: {e}")


# 初期接続（失敗時はフォールバック／fail-fast）
# Initial connection (fallback or fail-fast on failure)
if redis_client is None:
    if REDIS_FAIL_FAST:
        redis_client = _connect_with_retries()
        if redis_client is None:
            _fail_fast("startup")
    else:
        redis_client = _create_redis_client()
