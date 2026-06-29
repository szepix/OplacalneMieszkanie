import re, time, urllib.parse
from pipeline.http import _json, OLX_API, strip_html
from pipeline.features import num

OLX_CAT = 14
ROOM_ENUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "four"}


def _olx_floor(label):
    if not label: return None
    s = str(label).strip().lower()
    if s in ("parter", "0"): return 0
    if s in ("suterena", "piwnica"): return -1
    if s in ("poddasze",): return 99
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def olx_row(o):
    pr = {p["key"]: (p.get("value", {}).get("label") if isinstance(p.get("value"), dict) else p.get("value"))
          for p in o.get("params", [])}
    prv = {p["key"]: p.get("value", {}) for p in o.get("params", []) if isinstance(p.get("value"), dict)}
    price = prv.get("price", {}).get("value") or num(pr.get("price"))
    area = float(re.sub(r"[^\d.]", "", (pr.get("m") or "0").replace(",", ".")) or 0)
    loc = o.get("location", {})
    return {
        "src": "OLX", "id": o["id"], "url": o.get("url", ""), "title": o.get("title", ""),
        "text": strip_html(o.get("title", "") + " . " + (o.get("description") or "")),
        "price": int(price or 0), "area": area, "rooms": pr.get("rooms"),
        "district": (loc.get("district") or {}).get("name", ""),
        "market": (pr.get("market") or "").lower(), "floor": _olx_floor(pr.get("floor_select")),
        "year": None, "coords": (o.get("map") or {}).get("lat"), "map": o.get("map") or {},
    }


def fetch_olx(spec, city_id, max_pages=40, district_id=None):
    rows, offset = [], 0
    enums = sorted({ROOM_ENUM.get(n, "four") for n in spec.rooms})
    while offset <= 1000 and offset // 40 < max_pages:
        q = {"offset": offset, "limit": 40, "category_id": OLX_CAT, "city_id": city_id,
             "filter_float_price:from": spec.price_min, "filter_float_price:to": spec.price_max}
        if district_id:
            q["district_id"] = district_id
        for i, e in enumerate(enums):
            q[f"filter_enum_rooms[{i}]"] = e
        d = _json(OLX_API + "?" + urllib.parse.urlencode(q))
        data = d.get("data", [])
        if not data:
            break
        for o in data:
            rows.append(olx_row(o))
        offset += 40
        time.sleep(0.05)
    return rows
