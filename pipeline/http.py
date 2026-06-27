import json, re, time, html, gzip, shutil, subprocess, urllib.parse, urllib.request, urllib.error, sys

try:
    import certifi, ssl; SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    import ssl; SSL_CTX = ssl.create_default_context()

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
NOMINATIM_UA = "olx-mieszkania-finder/1.0 (daniel@szepi.dev)"

OLX_API = "https://www.olx.pl/api/v1/offers/"

_CURL = shutil.which("curl")
def _get_curl(url, headers=None):
    if not _CURL: return ""
    cmd = [_CURL, "-sL", "--compressed", "--max-time", "40", "-A", UA]
    for k, v in (headers or {}).items():
        if k.lower() not in ("user-agent", "accept-encoding"): cmd += ["-H", f"{k}: {v}"]
    try:
        return subprocess.run(cmd + [url], capture_output=True, timeout=50).stdout.decode("utf-8", "replace")
    except Exception:
        return ""

def _get(url, headers=None, tries=3):
    h = {"User-Agent": UA, "Accept-Encoding": "gzip",
         "Accept": "text/html,application/json,*/*", "Accept-Language": "pl,en;q=0.8"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 405, 429):           # bot-block → przez curl (inny fingerprint)
                t = _get_curl(url, headers)
                if t: return t
            if a == tries - 1:
                print(f"  ! GET {url[:90]}: {e}", file=sys.stderr); return ""
            time.sleep(0.6 * (a + 1))
        except Exception as e:
            if a == tries - 1:
                print(f"  ! GET {url[:90]}: {e}", file=sys.stderr); return ""
            time.sleep(0.6 * (a + 1))
    return ""

def _json(url, headers=None):
    t = _get(url, headers)
    try: return json.loads(t)
    except Exception: return {}

def next_data(htmltext):
    i = htmltext.find('id="__NEXT_DATA__"')
    if i < 0: return {}
    s = htmltext.find(">", i) + 1
    e = htmltext.find("</script>", s)
    try: return json.loads(htmltext[s:e])
    except Exception: return {}

def walk(o, typ):
    if isinstance(o, dict):
        if o.get("__typename") == typ: yield o
        for v in o.values(): yield from walk(v, typ)
    elif isinstance(o, list):
        for v in o: yield from walk(v, typ)

def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")

def _get_oto(url, tries=5):
    """Otodom przez curl (urllib bywa fingerprint-blokowany 405). Retry+backoff na burst-limit."""
    for a in range(tries):
        t = _get_curl(url, {"Accept": "text/html", "Accept-Language": "pl,en;q=0.8"})
        if "__NEXT_DATA__" in t: return t
        time.sleep(1.0 + 1.4 * a)
    return ""
