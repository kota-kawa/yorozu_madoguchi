import datetime
import logging
from redis_client import redis_client, get_user_type

logger = logging.getLogger(__name__)

EXPIRATION_SECONDS = 86400 * 2  # 48 hours
TOTAL_DAILY_LIMIT = 500

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
    if not session_id:
        return normalized if normalized else ""

    stored = get_user_type(session_id)
    stored_normalized = normalize_user_type(stored)
    if stored_normalized:
        return stored_normalized

    return normalized if normalized else ""

def check_and_increment_limit(session_id, user_type=None):
    """
    Check total usage count in Redis using Lua script for atomicity.
    Returns (allowed, current_count, limit, user_type, total_exceeded, error_code).
    """
    if not redis_client:
        logger.error("Redis client is not available. Rejecting limit check.")
        # Fail closed: block when Redis is unavailable
        return False, 0, 0, "", False, "redis_unavailable"

    resolved_type = resolve_user_type(session_id, user_type)
    if not resolved_type:
        return False, 0, 0, "", False, None

    today_str = datetime.date.today().isoformat()
    limit = USER_TYPE_LIMITS[resolved_type]
    user_key = f"daily_usage:{today_str}:{session_id}:{resolved_type}"
    total_key = f"daily_usage_total:{today_str}"

    # Lua script to check and increment atomically
    # KEYS[1]: user usage key
    # KEYS[2]: total usage key
    # ARGV[1]: user max limit
    # ARGV[2]: total max limit
    # ARGV[3]: expiration in seconds
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
            return -2
        end
        return -1
    end

    return user_val
    """

    try:
        result = redis_client.eval(
            lua_script,
            2,
            user_key,
            total_key,
            limit,
            TOTAL_DAILY_LIMIT,
            EXPIRATION_SECONDS,
        )
        
        if result == -1:
            # Limit exceeded. 
            # Ideally get the current count (which is limit or limit+1 depending on timing),
            # but usually just returning limit is enough for display.
            # Or fetch actual value if strictly needed.
            return False, limit, limit, resolved_type, False, None
        if result == -2:
            return False, limit, limit, resolved_type, True, None
            
        return True, result, limit, resolved_type, False, None

    except Exception as e:
        logger.error(f"Error accessing Redis limit: {e}")
        # Fail closed: block when Redis fails
        return False, 0, limit, resolved_type, False, "redis_unavailable"
