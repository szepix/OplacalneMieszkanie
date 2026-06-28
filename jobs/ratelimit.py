from datetime import datetime, timezone
import redis
from config import REDIS_URL, RATE_ACTIVE_TTL, RATE_DAILY_LIMIT


def _conn():
    return redis.Redis.from_url(REDIS_URL)


def check_and_reserve(ip: str, now=None, conn=None):
    conn = conn or _conn()
    now = now or datetime.now(timezone.utc)
    active_key = f"wf:active:{ip}"
    if not conn.set(active_key, "1", nx=True, ex=RATE_ACTIVE_TTL):
        return False, "active"
    daily_key = f"wf:daily:{ip}:{now.strftime('%Y%m%d')}"
    count = conn.incr(daily_key)
    if count == 1:
        conn.expire(daily_key, 86400)
    if count > RATE_DAILY_LIMIT:
        conn.delete(active_key)
        return False, "daily"
    return True, None
