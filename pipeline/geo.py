import json, re, math, threading, time, urllib.parse
from pipeline.http import _json, _get, NOMINATIM_UA

OLX_REGIONS = "https://www.olx.pl/api/v1/geo-encoder/regions/"
_GEO_LOOKUP_CACHE = {}
WARSZAWA_CITY_ID = 17871

NOMINATIM = "https://nominatim.openstreetmap.org/search"
_geo_lock = threading.Lock()
_geo_last = [0.0]
GEO = {}

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    repl = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ż":"z","ź":"z"}
    return "".join(repl.get(ch, ch) for ch in s)

def _regions() -> list[dict]:
    if "regions" not in _GEO_LOOKUP_CACHE:
        _GEO_LOOKUP_CACHE["regions"] = (_json(OLX_REGIONS) or {}).get("data", [])
    return _GEO_LOOKUP_CACHE["regions"]

def _cities(region_id: int) -> list[dict]:
    key = f"cities:{region_id}"
    if key not in _GEO_LOOKUP_CACHE:
        url = f"{OLX_REGIONS}{region_id}/cities/"
        _GEO_LOOKUP_CACHE[key] = (_json(url) or {}).get("data", [])
    return _GEO_LOOKUP_CACHE[key]

def resolve_city(woj: str, miasto: str) -> dict | None:
    wn, mn = _norm(woj), _norm(miasto)
    region = next((r for r in _regions() if _norm(r["name"]) == wn or r.get("normalized_name") == wn), None)
    if not region:
        return None
    city = next((c for c in _cities(region["id"])
                 if c.get("normalized_name") == mn or _norm(c["name"]) == mn), None)
    if not city:
        return None
    return {"city_id": city["id"], "region_id": region["id"],
            "lat": city.get("latitude"), "lng": city.get("longitude"),
            "has_districts": city.get("has_districts", False), "name": city["name"]}

def geocode(street, number, city="Warszawa"):
    """ulica+numer -> (lat,lng) z Nominatim (structured). Rate-limit 1.1s, cache."""
    if not street: return None
    street = re.sub(r"\b(ul|ulica|al|aleja|os|osiedle|pl|plac)\.?\s+", "", street.strip(), flags=re.I).strip()
    key = f"{street}|{number or ''}|{city}".lower()
    if key in GEO: return tuple(GEO[key]) if GEO[key] else None
    q = {"city": city, "country": "Poland", "format": "json", "limit": "1",
         "street": (f"{number} {street}" if number else street)}
    url = NOMINATIM + "?" + urllib.parse.urlencode(q)
    with _geo_lock:
        dt = time.time() - _geo_last[0]
        if dt < 1.2: time.sleep(1.2 - dt)
        t = _get(url, {"User-Agent": NOMINATIM_UA})
        _geo_last[0] = time.time()
    try:
        d = json.loads(t)
        res = (float(d[0]["lat"]), float(d[0]["lon"])) if d else None
    except Exception:
        res = None
    GEO[key] = list(res) if res else None
    return res

METRO = [   # operacyjne stacje M1+M2 (OSM/Overpass); planowane M3/M4 pominięte
    ("Kabaty", 52.13208, 21.06507, "M1"), ("Natolin", 52.1411, 21.05644, "M1"),
    ("Imielin", 52.1493, 21.04611, "M1"), ("Stokłosy", 52.15608, 21.03472, "M1"),
    ("Ursynów", 52.16205, 21.02763, "M1"), ("Służew", 52.17276, 21.02629, "M1"),
    ("Wilanowska", 52.18094, 21.01992, "M1"), ("Wierzbno", 52.18987, 21.0168, "M1"),
    ("Racławicka", 52.19886, 21.01223, "M1"), ("Pole Mokotowskie", 52.20878, 21.00793, "M1"),
    ("Politechnika", 52.21866, 21.0153, "M1"), ("Centrum", 52.23101, 21.01019, "M1"),
    ("Ratusz-Arsenał", 52.24522, 21.00088, "M1"), ("Dworzec Gdański", 52.25806, 20.99419, "M1"),
    ("Plac Wilsona", 52.26926, 20.9845, "M1"), ("Marymont", 52.27158, 20.97194, "M1"),
    ("Słodowiec", 52.27683, 20.96013, "M1"), ("Stare Bielany", 52.28183, 20.94935, "M1"),
    ("Wawrzyszew", 52.28635, 20.93952, "M1"), ("Młociny", 52.29077, 20.92987, "M1"),
    ("Świętokrzyska", 52.2351, 21.0079, "M1/M2"), ("Rondo Daszyńskiego", 52.23056, 20.9833, "M2"),
    ("Płocka", 52.23245, 20.96638, "M2"), ("Rondo ONZ", 52.23307, 20.9981, "M2"),
    ("Nowy Świat-Uniwersytet", 52.23682, 21.01682, "M2"), ("Młynów", 52.23766, 20.9601, "M2"),
    ("Księcia Janusza", 52.23918, 20.94438, "M2"), ("Bemowo", 52.23921, 20.9155, "M2"),
    ("Centrum Nauki Kopernik", 52.23991, 21.03179, "M2"), ("Ulrychów", 52.24033, 20.92987, "M2"),
    ("Stadion Narodowy", 52.24683, 21.04285, "M2"), ("Dworzec Wileński", 52.25378, 21.0358, "M2"),
    ("Szwedzka", 52.26347, 21.04552, "M2"), ("Targówek Mieszkaniowy", 52.26925, 21.05137, "M2"),
    ("Trocka", 52.2751, 21.05506, "M2"), ("Zacisze", 52.28375, 21.06215, "M2"),
    ("Kondratowicza", 52.29208, 21.04869, "M2"), ("Bródno", 52.29359, 21.02894, "M2"),
]

def haversine(la1, lo1, la2, lo2):
    r = 6371000.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp = math.radians(la2 - la1); dl = math.radians(lo2 - lo1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * r * math.asin(math.sqrt(a))

def nearest_metro(lat, lng):
    """(nazwa, linia, metry_w_linii_prostej) najbliższej operacyjnej stacji."""
    best = min(METRO, key=lambda s: haversine(lat, lng, s[1], s[2]))
    return best[0], best[3], int(round(haversine(lat, lng, best[1], best[2])))
