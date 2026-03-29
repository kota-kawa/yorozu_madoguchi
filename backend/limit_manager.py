"""
利用制限（レートリミット）を管理するモジュール。
Module for enforcing rate limits per user and globally.
"""

import datetime
import logging
import os
from typing import Any, Optional, Tuple
from backend import redis_client

logger = logging.getLogger(__name__)

# 定数定義
# Constants
EXPIRATION_SECONDS = 86400 * 2  # 48時間（Redisキーの有効期限） / 48 hours TTL for Redis keys
TOTAL_DAILY_LIMIT = 500  # システム全体での1日の最大リクエスト数 / Total daily cap
try:
    WEB_SEARCH_MONTHLY_LIMIT = int(os.getenv("WEB_SEARCH_MONTHLY_LIMIT", "1000"))
except ValueError:
    WEB_SEARCH_MONTHLY_LIMIT = 1000

# ユーザー種別ごとの1日のリクエスト制限
# Per-user-type daily limits
USER_TYPE_LIMITS = {
    "normal": 50,
    "premium": 150,
}


def _seconds_until_next_month(now: Optional[datetime.datetime] = None) -> int:
    """
    現在時刻から翌月初日までの秒数を返す
    Return seconds from now until the first moment of next month.
    """
    current = now or datetime.datetime.now()
    if current.month == 12:
        next_month = datetime.datetime(current.year + 1, 1, 1)
    else:
        next_month = datetime.datetime(current.year, current.month + 1, 1)
    seconds = int((next_month - current).total_seconds())
    return max(60, seconds)

def normalize_user_type(user_type: Any) -> str:
    """
    ユーザー種別の文字列を正規化する
    Normalize user type text.
    
    空白除去、小文字化を行い、有効な種別（normal/premium）のみを返します。
    無効な場合は空文字を返します。
    Strips whitespace, lowercases, and only returns valid types (normal/premium).
    """
    if not user_type:
        return ""
    normalized = str(user_type).strip().lower()
    return normalized if normalized in USER_TYPE_LIMITS else ""

def resolve_user_type(session_id: str, user_type: Optional[str] = None) -> str:
    """
    ユーザー種別を解決する
    Resolve user type from input or Redis.
    
    引数で渡された user_type を優先し、なければ Redis から session_id に紐づく情報を取得します。
    Prefers explicit input; otherwise loads from Redis by session ID.
    """
    normalized = normalize_user_type(user_type)
    if not session_id:
        return normalized if normalized else ""

    stored = redis_client.get_user_type(session_id)
    stored_normalized = normalize_user_type(stored)
    if stored_normalized:
        return stored_normalized

    return normalized if normalized else ""

def check_and_increment_limit(session_id: str, user_type: Optional[str] = None) -> Tuple[bool, int, int, str, bool, Optional[str]]:
    """
    利用制限を確認し、カウントをインクリメントする
    Check rate limits and increment counters.
    
    Luaスクリプトを使用してアトミックに実行します。
    Uses a Lua script for atomic updates.
    
    戻り値:
    - allowed: 許可されるかどうか (True/False)
    - current_count: 現在のカウント
    - limit: 制限値
    - user_type: ユーザー種別
    - total_exceeded: システム全体の制限を超過したか (True/False)
    - error_code: エラーコード (Redis利用不可など)
    Returns:
    - allowed: whether allowed
    - current_count: current count
    - limit: per-user limit
    - user_type: resolved user type
    - total_exceeded: global limit exceeded
    - error_code: error code (e.g., redis_unavailable)
    """
    client = redis_client.get_redis_client()
    if not client:
        logger.error("Redis client is not available. Rejecting limit check.")
        # Fail closed: Redisが利用できない場合は安全のためブロック
        # Fail closed when Redis is unavailable
        return False, 0, 0, "", False, "redis_unavailable"

    resolved_type = resolve_user_type(session_id, user_type)
    if not resolved_type:
        return False, 0, 0, "", False, None

    today_str = datetime.date.today().isoformat()
    limit = USER_TYPE_LIMITS[resolved_type]
    user_key = f"daily_usage:{today_str}:{session_id}:{resolved_type}"
    total_key = f"daily_usage_total:{today_str}"

    # Luaスクリプト: ユーザーごとと全体のカウントをアトミックにチェック・更新
    # Lua script: atomically update user and global counters
    # KEYS[1]: ユーザー利用数のキー / user counter key
    # KEYS[2]: 全体利用数のキー / global counter key
    # ARGV[1]: ユーザー上限 / user limit
    # ARGV[2]: 全体上限 / global limit
    # ARGV[3]: 有効期限（秒） / TTL in seconds
    lua_script = """
    local user_key = KEYS[1]
    local total_key = KEYS[2]
    local user_limit = tonumber(ARGV[1])
    local total_limit = tonumber(ARGV[2])
    local expire_time = tonumber(ARGV[3])

    local user_val = redis.call("incr", user_key)
    local total_val = redis.call("incr", total_key)

    if user_val == 1 then
        redis.call("expire", user_key, expire_time)
    end
    if total_val == 1 then
        redis.call("expire", total_key, expire_time)
    end

    if user_val > user_limit or total_val > total_limit then
        redis.call("decr", user_key)
        redis.call("decr", total_key)
        if total_val > total_limit then
            return -2  -- 全体制限超過
        end
        return -1  -- ユーザー制限超過
    end

    return user_val
    """

    try:
        result = client.eval(
            lua_script,
            2,
            user_key,
            total_key,
            limit,
            TOTAL_DAILY_LIMIT,
            EXPIRATION_SECONDS,
        )
        
        if result == -1:
            # ユーザー制限超過
            # User limit exceeded
            return False, limit, limit, resolved_type, False, None
        if result == -2:
            # 全体制限超過
            # Global limit exceeded
            return False, limit, limit, resolved_type, True, None
            
        return True, result, limit, resolved_type, False, None

    except Exception as e:
        logger.error(f"Error accessing Redis limit: {e}")
        # Fail closed: Redisエラー時はブロック
        # Fail closed on Redis errors
        return False, 0, limit, resolved_type, False, "redis_unavailable"


def check_and_increment_web_search_limit() -> Tuple[bool, int, int, Optional[str]]:
    """
    Web検索の月次利用上限を確認し、カウントをインクリメントする
    Check and increment the monthly web-search usage counter.

    Returns:
    - allowed: whether search is allowed
    - current_count: current monthly count (or limit when blocked)
    - limit: monthly limit
    - error_code: optional error code
    """
    limit = max(1, WEB_SEARCH_MONTHLY_LIMIT)
    client = redis_client.get_redis_client()
    if not client:
        logger.error("Redis client is not available. Rejecting web-search limit check.")
        return False, 0, limit, "redis_unavailable"

    today = datetime.date.today()
    monthly_key = f"web_search_usage:{today.year:04d}-{today.month:02d}"
    ttl_seconds = _seconds_until_next_month()

    lua_script = """
    local monthly_key = KEYS[1]
    local monthly_limit = tonumber(ARGV[1])
    local expire_time = tonumber(ARGV[2])

    local monthly_val = redis.call("incr", monthly_key)
    if monthly_val == 1 then
        redis.call("expire", monthly_key, expire_time)
    end

    if monthly_val > monthly_limit then
        redis.call("decr", monthly_key)
        return -1
    end
    return monthly_val
    """

    try:
        result = client.eval(
            lua_script,
            1,
            monthly_key,
            limit,
            ttl_seconds,
        )
        if result == -1:
            return False, limit, limit, None
        return True, int(result), limit, None
    except Exception as e:
        logger.error("Error accessing Redis web-search limit: %s", e)
        return False, 0, limit, "redis_unavailable"
