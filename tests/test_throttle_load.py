import http.server
import threading
import time

import pytest


@pytest.fixture
def counting_server():
    hits = []
    lock = threading.Lock()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            with lock:
                hits.append(time.monotonic())
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_address[1], hits
    finally:
        srv.shutdown()
        srv.server_close()


def test_concurrent_http_calls_are_rate_capped(redis_conn, counting_server):
    from pipeline import http as H
    from pipeline.throttle import RedisThrottle
    port, hits = counting_server
    rate, burst, n = 10.0, 2.0, 12
    H.set_throttle(RedisThrottle(redis_conn, default_rate=rate, default_burst=burst),
                   max_wait=30.0)
    try:
        t0 = time.monotonic()
        threads = [threading.Thread(target=H._get, args=(f"http://127.0.0.1:{port}/x",))
                   for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.monotonic() - t0
    finally:
        H.clear_throttle()

    assert len(hits) == n  # every request still went out (cap delays, never drops)
    # burst lets `burst` through instantly; the rest are paced at `rate`/s.
    # Floor: (n - burst)/rate seconds. Without the throttle this is ~instant.
    assert elapsed >= (n - burst) / rate * 0.8
