import os
import json
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Redisクライアントの初期化
# decode_responses=True により、bytes ではなく str が返される
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

def get_session_key(session_id, key_type):
    """セッションごとのRedisキーを生成する"""
    return f"session:{session_id}:{key_type}"

def get_chat_history(session_id):
    """指定されたセッションIDのチャット履歴を取得する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return []
    
    key = get_session_key(session_id, "chat_history")
    try:
        data = redis_client.get(key)
        if data:
            # JSONのリスト[role, text]をタプル(role, text)に変換
            return [tuple(item) for item in json.loads(data)]
    except Exception as e:
        logger.error(f"Error getting chat history for {session_id}: {e}")
    
    return []

def save_chat_history(session_id, chat_history):
    """指定されたセッションIDのチャット履歴を保存する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return
    
    key = get_session_key(session_id, "chat_history")
    try:
        redis_client.set(key, json.dumps(chat_history, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Error saving chat history for {session_id}: {e}")

def get_decision(session_id):
    """指定されたセッションIDの決定事項を取得する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return ""
    
    key = get_session_key(session_id, "decision")
    try:
        data = redis_client.get(key)
        return data if data else ""
    except Exception as e:
        logger.error(f"Error getting decision for {session_id}: {e}")
        return ""

def save_decision(session_id, decision_text):
    """指定されたセッションIDの決定事項を保存する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return
    
    key = get_session_key(session_id, "decision")
    try:
        redis_client.set(key, decision_text)
    except Exception as e:
        logger.error(f"Error saving decision for {session_id}: {e}")

def reset_session(session_id):
    """指定されたセッションIDのデータをリセットする"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return
    
    try:
        keys = [
            get_session_key(session_id, "chat_history"),
            get_session_key(session_id, "decision")
        ]
        redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Error resetting session for {session_id}: {e}")

def get_user_type(session_id):
    """指定されたセッションIDのユーザー種別を取得する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return ""

    key = get_session_key(session_id, "user_type")
    try:
        data = redis_client.get(key)
        return data if data else ""
    except Exception as e:
        logger.error(f"Error getting user_type for {session_id}: {e}")
        return ""

def save_user_type(session_id, user_type):
    """指定されたセッションIDのユーザー種別を保存する"""
    if not redis_client:
        logger.warning("Redis client is not available.")
        return

    key = get_session_key(session_id, "user_type")
    try:
        redis_client.set(key, user_type)
    except Exception as e:
        logger.error(f"Error saving user_type for {session_id}: {e}")
