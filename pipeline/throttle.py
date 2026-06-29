import time
import logging

import redis as _redis

logger = logging.getLogger(__name__)

# Atomic refill+take. Returns {allowed, wait_seconds}. Token consumed only on grant.
_TAKE_LUA = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])
local burst = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local t = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(t[1])
local ts = tonumber(t[2])
if tokens == nil then tokens = burst; ts = now end
local elapsed = now - ts
if elapsed < 0 then elapsed = 0 end
tokens = math.min(burst, tokens + elapsed * rate)
local allowed = 0
local wait = 0.0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
else
  wait = (1 - tokens) / rate
end
redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', key, math.ceil((burst / rate) * 1000) + 1000)
return {allowed, tostring(wait)}
"""


class TokenBucket:
    def __init__(self, conn, key, rate, burst):
        self.conn = conn
        self.key = f"wf:tb:{key}"
        self.rate = float(rate)
        self.burst = float(burst)
        self._script = conn.register_script(_TAKE_LUA)

    def try_acquire(self):
        """Return 0.0 if a token was granted, else seconds to wait.

        Raises redis.RedisError on backend failure — RedisThrottle handles
        fail-open + circuit breaking.
        """
        allowed, wait = self._script(
            keys=[self.key], args=[self.rate, self.burst, time.time()]
        )
        return 0.0 if int(allowed) == 1 else float(wait)

    def acquire(self, max_wait=30.0):
        deadline = time.monotonic() + max_wait
        while True:
            wait = self.try_acquire()
            if wait == 0.0:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(wait, remaining))


class RedisThrottle:
    def __init__(self, conn, default_rate, default_burst, rates=None, bursts=None,
                 breaker_cooldown=30.0):
        self.conn = conn
        self.default_rate = float(default_rate)
        self.default_burst = float(default_burst)
        self.rates = rates or {}
        self.bursts = bursts or {}
        self.breaker_cooldown = breaker_cooldown
        self._buckets = {}
        self._tripped_until = 0.0

    def _bucket(self, domain):
        b = self._buckets.get(domain)
        if b is None:
            b = TokenBucket(
                self.conn, domain,
                self.rates.get(domain, self.default_rate),
                self.bursts.get(domain, self.default_burst),
            )
            self._buckets[domain] = b
        return b

    def acquire(self, domain, max_wait=30.0):
        if time.monotonic() < self._tripped_until:
            return True
        try:
            return self._bucket(domain).acquire(max_wait=max_wait)
        except _redis.RedisError as e:
            logger.warning("throttle fail-open, breaker tripped (%s): %s", domain, e)
            self._tripped_until = time.monotonic() + self.breaker_cooldown
            return True


def build_from_config(conn):
    from config import (OLX_RATE, OTODOM_RATE, NOMINATIM_RATE,
                        DEWELOPERUCH_RATE, THROTTLE_BURST)
    rates = {
        "olx.pl": OLX_RATE,
        "otodom.pl": OTODOM_RATE,
        "nominatim.openstreetmap.org": NOMINATIM_RATE,
        "deweloperuch.pl": DEWELOPERUCH_RATE,
    }
    return RedisThrottle(conn, default_rate=min(rates.values()),
                         default_burst=THROTTLE_BURST, rates=rates)
