import datetime
import logging
from redis_client import redis_client, get_user_type

logger = logging.getLogger(__name__)

EXPIRATION_SECONDS = 86400 * 2  # 48 hours

USER_TYPE_LIMITS = {
    "normal": 10,
    "premium": 100,
}

def normalize_user_type(user_type):
    if not user_type:
        return ""
    normalized = str(user_type).strip().lower()
    return normalized if normalized in USER_TYPE_LIMITS else ""

def resolve_user_type(session_id, user_type=None):
    normalized = normalize_user_type(user_type)
    if normalized:
        return normalized
    if not session_id:
        return ""
    stored = get_user_type(session_id)
    return normalize_user_type(stored)

def check_and_increment_limit(session_id, user_type=None):
    """
    Check total usage count in Redis using Lua script for atomicity.
    Returns (True, current_count, limit, user_type) if within limit,
    (False, current_count, limit, user_type) if limit exceeded or user_type missing.
    """
    if not redis_client:
        logger.error("Redis client is not available. Bypassing limit check.")
        # Fail open: allow access if Redis is down
        resolved_type = normalize_user_type(user_type) or "normal"
        return True, 0, USER_TYPE_LIMITS.get(resolved_type, 10), resolved_type

    resolved_type = resolve_user_type(session_id, user_type)
    if not resolved_type:
        return False, 0, 0, ""

    today_str = datetime.date.today().isoformat()
    limit = USER_TYPE_LIMITS[resolved_type]
    key = f"daily_usage:{today_str}:{session_id}:{resolved_type}"

    # Lua script to check and increment atomically
    # KEYS[1]: usage key
    # ARGV[1]: max limit
    # ARGV[2]: expiration in seconds
    lua_script = """
    local key = KEYS[1]
    local limit = tonumber(ARGV[1])
    local expire_time = tonumber(ARGV[2])

    local new_val = redis.call("incr", key)

    if new_val == 1 then
        redis.call("expire", key, expire_time)
    end

    if new_val > limit then
        redis.call("decr", key) -- Revert increment
        return -1
    end

    return new_val
    """

    try:
        result = redis_client.eval(lua_script, 1, key, limit, EXPIRATION_SECONDS)
        
        if result == -1:
            # Limit exceeded. 
            # Ideally get the current count (which is limit or limit+1 depending on timing),
            # but usually just returning limit is enough for display.
            # Or fetch actual value if strictly needed.
            return False, limit, limit, resolved_type
            
        return True, result, limit, resolved_type

    except Exception as e:
        logger.error(f"Error accessing Redis limit: {e}")
        # Fail open: allow access if Redis fails
        return True, 0, limit, resolved_type
