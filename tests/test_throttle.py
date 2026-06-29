import time
import threading


def test_bucket_grants_burst_then_requires_wait(redis_conn):
    from pipeline.throttle import TokenBucket
    b = TokenBucket(redis_conn, "olx.pl", rate=1.0, burst=3)
    assert b.try_acquire() == 0.0
    assert b.try_acquire() == 0.0
    assert b.try_acquire() == 0.0
    wait = b.try_acquire()
    assert wait > 0.0


def test_bucket_refills_after_wait(redis_conn):
    from pipeline.throttle import TokenBucket
    b = TokenBucket(redis_conn, "otodom.pl", rate=20.0, burst=1)
    assert b.try_acquire() == 0.0
    assert b.try_acquire() > 0.0
    time.sleep(0.12)
    assert b.try_acquire() == 0.0


def test_failed_try_does_not_consume_token(redis_conn):
    from pipeline.throttle import TokenBucket
    b = TokenBucket(redis_conn, "nominatim", rate=0.0001, burst=1)
    assert b.try_acquire() == 0.0
    w1 = b.try_acquire()
    w2 = b.try_acquire()
    assert w1 > 0.0 and w2 > 0.0


def test_acquire_blocks_until_token(redis_conn):
    from pipeline.throttle import TokenBucket
    b = TokenBucket(redis_conn, "dom", rate=50.0, burst=1)
    assert b.acquire(max_wait=1.0) is True
    t0 = time.monotonic()
    assert b.acquire(max_wait=1.0) is True
    assert time.monotonic() - t0 >= 0.01


def test_acquire_times_out_when_starved(redis_conn):
    from pipeline.throttle import TokenBucket
    b = TokenBucket(redis_conn, "slow", rate=0.001, burst=1)
    assert b.acquire(max_wait=1.0) is True
    assert b.acquire(max_wait=0.2) is False


def test_redis_throttle_caps_concurrent_acquire_rate(redis_conn):
    from pipeline.throttle import RedisThrottle
    rate = 25.0
    thr = RedisThrottle(redis_conn, default_rate=rate, default_burst=1,
                        rates={"example.com": rate})
    t0 = time.monotonic()
    granted = []

    def worker():
        if thr.acquire("example.com", max_wait=5.0):
            granted.append(time.monotonic() - t0)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(granted) == 20
    span = max(granted)
    # 20 tokens at 25/s from a burst of 1 must take ~0.76s; allow slack but
    # prove they did NOT all fire instantly (which a missing cap would allow).
    assert span >= 0.5


def test_build_from_config_maps_known_domains(redis_conn):
    from pipeline.throttle import build_from_config, RedisThrottle
    thr = build_from_config(redis_conn)
    assert isinstance(thr, RedisThrottle)
    for d in ("olx.pl", "otodom.pl", "nominatim.openstreetmap.org", "deweloperuch.pl"):
        assert d in thr.rates and thr.rates[d] > 0


def test_worker_setup_installs_throttle_into_http(redis_conn):
    import pipeline.http as H
    from pipeline.throttle import RedisThrottle
    from worker.run import setup_throttle
    H.clear_throttle()
    setup_throttle(redis_conn)
    try:
        assert isinstance(H._THROTTLE, RedisThrottle)
    finally:
        H.clear_throttle()


def test_failopen_when_redis_unavailable():
    import redis
    from pipeline.throttle import RedisThrottle
    dead = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2)
    thr = RedisThrottle(dead, default_rate=1.0, default_burst=1)
    assert thr.acquire("example.com", max_wait=2.0) is True  # never blocks scraping
    # breaker tripped → subsequent calls short-circuit, no per-request Redis penalty
    t0 = time.monotonic()
    for _ in range(5):
        assert thr.acquire("example.com", max_wait=2.0) is True
    assert time.monotonic() - t0 < 0.1
