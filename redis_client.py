import os
import json
import redis
import logging
import time
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    REDIS_SESSION_TTL_SECONDS = int(os.getenv("REDIS_SESSION_TTL_SECONDS", "172800"))
except ValueError:
    REDIS_SESSION_TTL_SECONDS = 172800

# Redisクライアントの初期化
# decode_responses=True により、bytes ではなく str が返されるため、
# Pythonコード内でエンコード/デコードを意識する必要が減ります。
try:
    redis_client: Optional[redis.Redis] = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Redisが使えない場合の簡易フォールバック（単一プロセス限定）
_memory_store: Dict[str, Tuple[str, Optional[float]]] = {}

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
    
    例: session:abc-123:chat_history
    """
    return f"session:{session_id}:{key_type}"

def _set_with_ttl(key: str, value: str) -> None:
    """
    TTL（有効期限）付きで値を設定するヘルパー関数
    """
    if not redis_client:
        _memory_set(key, value)
        return
    try:
        if REDIS_SESSION_TTL_SECONDS > 0:
            redis_client.setex(key, REDIS_SESSION_TTL_SECONDS, value)
        else:
            redis_client.set(key, value)
    except Exception as e:
        logger.error(f"Error saving key {key} to Redis: {e}")
        _memory_set(key, value)

def get_chat_history(session_id: str) -> List[Tuple[str, str]]:
    """
    指定されたセッションIDのチャット履歴を取得する
    
    履歴はJSONリスト形式で保存されており、取得時にタプルのリストへ変換します。
    戻り値: [(role, text), ...]
    """
    key = get_session_key(session_id, "chat_history")
    try:
        if redis_client:
            data = redis_client.get(key)
        else:
            logger.warning("Redis client is not available; using in-memory fallback.")
            data = _memory_get(key)
        if data:
            # JSONのリスト[role, text]をタプル(role, text)に変換
            return [tuple(item) for item in json.loads(data)]
    except Exception as e:
        logger.error(f"Error getting chat history for {session_id}: {e}")
    
    return []

def save_chat_history(session_id: str, chat_history: Sequence[Tuple[str, str]]) -> None:
    """
    指定されたセッションIDのチャット履歴を保存する
    
    リスト形式の履歴をJSON文字列にシリアライズしてRedisに保存します。
    """
    key = get_session_key(session_id, "chat_history")
    try:
        _set_with_ttl(key, json.dumps(chat_history, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Error saving chat history for {session_id}: {e}")

def get_decision(session_id: str) -> str:
    """
    指定されたセッションIDの決定事項（構造化前のテキスト）を取得する
    """
    key = get_session_key(session_id, "decision")
    try:
        if redis_client:
            data = redis_client.get(key)
        else:
            logger.warning("Redis client is not available; using in-memory fallback.")
            data = _memory_get(key)
        return data if data else ""
    except Exception as e:
        logger.error(f"Error getting decision for {session_id}: {e}")
        return ""

def save_decision(session_id: str, decision_text: str) -> None:
    """
    指定されたセッションIDの決定事項を保存する
    """
    key = get_session_key(session_id, "decision")
    try:
        _set_with_ttl(key, decision_text)
    except Exception as e:
        logger.error(f"Error saving decision for {session_id}: {e}")

def reset_session(session_id: str) -> None:
    """
    指定されたセッションIDに関連する全データを削除する
    
    チャット履歴や決定事項など、セッションに関連するキーをまとめて削除します。
    """
    try:
        keys = [
            get_session_key(session_id, "chat_history"),
            get_session_key(session_id, "decision")
        ]
        if redis_client:
            redis_client.delete(*keys)
        _memory_delete(*keys)
    except Exception as e:
        logger.error(f"Error resetting session for {session_id}: {e}")

def get_user_type(session_id: str) -> str:
    """指定されたセッションIDのユーザー種別を取得する"""
    key = get_session_key(session_id, "user_type")
    try:
        if redis_client:
            data = redis_client.get(key)
        else:
            logger.warning("Redis client is not available; using in-memory fallback.")
            data = _memory_get(key)
        return data if data else ""
    except Exception as e:
        logger.error(f"Error getting user_type for {session_id}: {e}")
        return ""

def save_user_type(session_id: str, user_type: str) -> None:
    """指定されたセッションIDのユーザー種別を保存する"""
    key = get_session_key(session_id, "user_type")
    try:
        _set_with_ttl(key, user_type)
    except Exception as e:
        logger.error(f"Error saving user_type for {session_id}: {e}")
