import http.server
import socketserver
import threading

import pytest


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def test_domain_strips_www_and_keeps_host():
    from pipeline import http as H
    assert H._domain("https://www.olx.pl/api/v1/offers/") == "olx.pl"
    assert H._domain("https://www.otodom.pl/pl/wyniki") == "otodom.pl"
    assert H._domain("https://nominatim.openstreetmap.org/search") == "nominatim.openstreetmap.org"
    assert H._domain("https://deweloperuch.pl/wycena") == "deweloperuch.pl"


def test_get_acquires_token_for_host(redis_conn, server):
    from pipeline import http as H
    from pipeline.throttle import RedisThrottle
    thr = RedisThrottle(redis_conn, default_rate=100.0, default_burst=5)
    H.set_throttle(thr)
    try:
        body = H._get(f"http://127.0.0.1:{server}/x")
        assert "ok" in body
        assert redis_conn.exists("wf:tb:127.0.0.1") == 1
    finally:
        H.clear_throttle()


def test_get_without_throttle_is_noop(redis_conn, server):
    from pipeline import http as H
    H.clear_throttle()
    body = H._get(f"http://127.0.0.1:{server}/x")
    assert "ok" in body
    assert redis_conn.exists("wf:tb:127.0.0.1") == 0
