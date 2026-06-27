import re, time, urllib.parse, threading
from concurrent.futures import ThreadPoolExecutor
from pipeline.http import _get_oto, next_data, walk, strip_html
from pipeline.features import num

OTO_BASE = "https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie"
OTO_OFFER = "https://www.otodom.pl/pl/oferta/"
OTO_ROOM_ENUM = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE"}

OTO = {}
OTO_TTL = 86400
_oto_lock = threading.Lock()


def oto_search_url(spec, region_norm, city_norm):
    return f"{OTO_BASE}/{region_norm}/{city_norm}/{city_norm}/{city_norm}"


def _oto_query(spec, page):
    q = {"limit": 36, "page": page,
         "priceMin": spec.price_min, "priceMax": spec.price_max}
    if spec.rooms:
        rooms = [OTO_ROOM_ENUM.get(n) for n in spec.rooms if OTO_ROOM_ENUM.get(n)]
        q["roomsNumber"] = "[" + ",".join(rooms) + "]"
    if "ogrod" in spec.required_features:
        q["extras"] = "[GARDEN]"
    return q


def _oto_floor(floor_no):
    if not floor_no: return None
    s = (floor_no[0] if isinstance(floor_no, list) else str(floor_no)).lower()
    if s in ("ground_floor", "floor_0"): return 0
    if s in ("cellar", "basement"): return -1
    if s == "garret": return 99
    m = re.search(r"floor_(\d+)", s)
    return int(m.group(1)) if m else None


def _oto_district(loc):
    for b in (loc.get("reverseGeocoding", {}) or {}).get("locations", []):
        if b.get("locationLevel") == "district": return b.get("name", "")
    return ""


def _oto_rooms(ad, chars, tgt):
    v = chars.get("rooms_num") or tgt.get("Rooms_num") or ad.get("roomsNumber")
    return v if v else ""


def otodom_detail(oid, slug, use_cache=True):
    c = OTO.get(oid)
    if use_cache and c and time.time() - c.get("ts", 0) < OTO_TTL:
        return c["data"]
    t = _get_oto(OTO_OFFER + slug)
    d = next_data(t)
    ad = (d.get("props", {}).get("pageProps", {}) or {}).get("ad")
    if not ad: return None
    tgt = ad.get("target", {}) or {}
    loc = ad.get("location", {}) or {}
    st = ((loc.get("address") or {}).get("street") or {})
    coords = loc.get("coordinates") or {}
    price = ad.get("price")
    if isinstance(price, dict): price = price.get("value")
    price = price or num(tgt.get("Price"))
    chars = {c.get("key"): c.get("value") for c in ad.get("characteristics", [])}
    area = float(str(chars.get("m", tgt.get("Area", 0))).replace(",", ".") or 0)
    extras = [x.lower() for x in (tgt.get("Extras_types") or [])]
    terrain = num(tgt.get("Terrain_area") or chars.get("terrain_area"))
    rec = {
        "src": "Otodom", "id": ad["id"], "url": ad.get("url", ""), "title": ad.get("title", ""),
        "text": strip_html(ad.get("title", "") + " . " + (ad.get("description") or "")),
        "price": int(price or 0), "area": area, "rooms": str(_oto_rooms(ad, chars, tgt)),
        "district": _oto_district(loc),
        "market": (tgt.get("MarketType") or chars.get("market") or "").lower(),
        "year": num(tgt.get("Build_year") or chars.get("build_year")) or None,
        "floor": _oto_floor(tgt.get("Floor_no") or chars.get("floor_no")),
        "street": st.get("name"), "number": st.get("number"),
        "coords": (coords.get("latitude"), coords.get("longitude")) if coords.get("latitude") else None,
        "extras": extras, "terrain": terrain,
    }
    with _oto_lock: OTO[oid] = {"ts": time.time(), "data": rec}
    return rec


def fetch_otodom(spec, region_norm, city_norm, max_pages=40):
    base = oto_search_url(spec, region_norm, city_norm)
    cands = {}
    for page in range(1, max_pages + 1):
        url = base + "?" + urllib.parse.urlencode(_oto_query(spec, page))
        t = _get_oto(url)
        d = next_data(t)
        if not d:
            break
        ads = list(walk(d, "AdvertListItem"))
        if not ads:
            break
        for a in ads:
            cands[str(a["id"])] = a["slug"]
        if len(ads) < 30:
            break
        time.sleep(0.3)
    rows = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        for r in ex.map(lambda it: otodom_detail(*it), cands.items()):
            if r:
                rows.append(r)
    return rows
