import datetime
import logging
from redis_client import redis_client

logger = logging.getLogger(__name__)

MAX_DAILY_LIMIT = 10
EXPIRATION_SECONDS = 86400 * 2  # 48 hours

def check_and_increment_limit():
    """
    Check total usage count in Redis using Lua script for atomicity.
    Returns (True, current_count) if within limit,
    (False, current_count) if limit exceeded.
    """
    if not redis_client:
        logger.error("Redis client is not available.")
        # Fail safe: deny access or allow? Assuming deny for safety/rate limiting.
        return False, -1

    today_str = datetime.date.today().isoformat()
    key = f"daily_usage:{today_str}"

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
        result = redis_client.eval(lua_script, 1, key, MAX_DAILY_LIMIT, EXPIRATION_SECONDS)
        
        if result == -1:
            # Limit exceeded. 
            # Ideally get the current count (which is limit or limit+1 depending on timing),
            # but usually just returning limit is enough for display.
            # Or fetch actual value if strictly needed.
            return False, MAX_DAILY_LIMIT
            
        return True, result

    except Exception as e:
        logger.error(f"Error accessing Redis limit: {e}")
        return False, -1
