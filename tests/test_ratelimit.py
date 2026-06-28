from datetime import datetime, timezone


def test_first_submit_allowed_then_active_block(redis_conn):
    from jobs.ratelimit import check_and_reserve
    ok, reason = check_and_reserve("9.9.9.9", conn=redis_conn)
    assert ok and reason is None
    ok2, reason2 = check_and_reserve("9.9.9.9", conn=redis_conn)
    assert not ok2 and reason2 == "active"  # within 5 min


def test_daily_limit_blocks_21st(redis_conn):
    from jobs.ratelimit import check_and_reserve
    ip = "8.8.8.8"
    now = datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)
    allowed = 0
    for _ in range(25):
        redis_conn.delete(f"wf:active:{ip}")  # clear the 5-min lock to isolate daily cap
        ok, reason = check_and_reserve(ip, now=now, conn=redis_conn)
        if ok:
            allowed += 1
        else:
            assert reason == "daily"
    assert allowed == 20


def test_active_block_does_not_consume_daily_quota(redis_conn):
    from jobs.ratelimit import check_and_reserve
    ip = "7.7.7.7"
    now = datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)
    check_and_reserve(ip, now=now, conn=redis_conn)              # 1 consumed, active set
    check_and_reserve(ip, now=now, conn=redis_conn)              # blocked active, no daily incr
    assert int(redis_conn.get(f"wf:daily:{ip}:20260627")) == 1
