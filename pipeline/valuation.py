import re
import urllib.parse
from pipeline.http import _get
from pipeline.geo import geocode, nearest_metro

DEWELOPER = "https://deweloperuch.pl/wycena/warszawa/x"

_WYC_RX = {
    "value": re.compile(r'estimatedValue\\?":\s*(\d+)'),
    "ppsqm": re.compile(r'estimatedPricePerSqm\\?":\s*(\d+)'),
    "median": re.compile(r'medianPricePerSqm\\?":\s*(\d+)'),
    "avg": re.compile(r'averagePricePerSqm\\?":\s*(\d+)'),
    "count": re.compile(r'"count\\?":\s*(\d+)'),
    "radius": re.compile(r'radiusLevel\\?":\\?"([a-z]+)'),
    "reliable": re.compile(r'isReliable\\?":\s*(true|false)'),
    "r2": re.compile(r'"r2\\?":\s*([0-9.]+)'),
}

WYC = {}
_MISS = object()


def _default_get(key):
    return WYC.get(key, _MISS)


def _default_set(key, val):
    WYC[key] = val


cache_get = _default_get
cache_set = _default_set


def wycena(lat, lng, area):
    key = f"{round(lat,5)},{round(lng,5)},{int(area)}"
    hit = cache_get(key)
    if hit is not _MISS:
        return hit
    q = {"lat": f"{lat}", "lng": f"{lng}", "area": str(int(area))}
    t = _get(DEWELOPER + "?" + urllib.parse.urlencode(q),
             {"Accept": "*/*", "Referer": "https://deweloperuch.pl/wycena"})
    out = {}
    for k, rx in _WYC_RX.items():
        m = rx.search(t)
        if not m:
            continue
        out[k] = (m.group(1) if k == "radius" else
                  m.group(1) == "true" if k == "reliable" else
                  float(m.group(1)) if k == "r2" else int(m.group(1)))
    res = out if out.get("value") else None
    cache_set(key, res)
    return res

def value_of(r, spec, use_address_geocode=False, warszawa=False):
    lat = lng = None
    if use_address_geocode and r.get("street"):
        g = geocode(r.get("street"), r.get("number"))
        if g:
            lat, lng = g; r["geo_src"] = "adres"
    if lat is None and r.get("coords") and isinstance(r["coords"], (list, tuple)):
        lat, lng = r["coords"]; r["geo_src"] = "oferta"
    if lat is None and isinstance(r.get("map"), dict) and r["map"].get("lat"):
        lat, lng = r["map"]["lat"], r["map"]["lon"]; r["geo_src"] = "mapa-olx"
    if lat is None or lng is None:
        return None
    lat, lng = float(lat), float(lng)
    r["lat"], r["lng"] = round(lat, 6), round(lng, 6)
    if warszawa:
        r["metro_name"], r["metro_line"], r["metro_m"] = nearest_metro(lat, lng)
    w = wycena(lat, lng, r["area"])
    if not w:
        return None
    r["wycena"] = w["value"]; r["ppsqm"] = w.get("ppsqm")
    r["median_ppsqm"] = w.get("median"); r["radius"] = w.get("radius")
    r["wyc_count"] = w.get("count") or 0; r["reliable_src"] = bool(w.get("reliable")); r["r2"] = w.get("r2")
    wmed = (w.get("median") or w.get("ppsqm") or 0) * r["area"]
    r["wycena_med"] = int(wmed)
    r["value_est"] = round(w["value"] / r["eff_price"], 3)
    r["value_med"] = round(wmed / r["eff_price"], 3) if wmed else r["value_est"]
    r["value"] = round(min(w["value"], wmed or w["value"]) / r["eff_price"], 3)
    good_radius = r["radius"] in ("budynek", "poblize", "sasiedztwo")
    r["suspect"] = (r["value_est"] > 1.6 or abs(r["value_est"] - r["value_med"]) > 0.45
                    or r["wyc_count"] < 5 or r["radius"] in ("miasto", "miejscowosc"))
    r["reliable"] = r["wyc_count"] >= 8 and good_radius and not r["suspect"]
    return r
