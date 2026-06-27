from concurrent.futures import ThreadPoolExecutor
from pipeline.spec import SearchSpec
from pipeline.geo import resolve_city, _norm, WARSZAWA_CITY_ID
from pipeline.features import enrich, qualifies
from pipeline.sources.olx import fetch_olx
from pipeline.sources.otodom import fetch_otodom
from pipeline.valuation import value_of

def run_search(spec: SearchSpec, max_pages=2, use_address_geocode=False, workers=6):
    city = resolve_city(spec.woj, spec.miasto)
    if not city:
        return {"spec": spec, "city": None, "count_raw": 0, "count_qualified": 0,
                "results": [], "error": "city_not_found"}
    warszawa = city["city_id"] == WARSZAWA_CITY_ID
    region_norm, city_norm = _norm(spec.woj), _norm(spec.miasto)
    try:
        olx = fetch_olx(spec, city["city_id"], max_pages=max_pages)
    except Exception:
        olx = []
    try:
        oto = fetch_otodom(spec, region_norm, city_norm, max_pages=max_pages)
    except Exception:
        oto = []
    raw = [enrich(r) for r in olx + oto]
    cand = [r for r in raw if qualifies(r, spec)]
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(lambda x: value_of(x, spec, use_address_geocode, warszawa), cand):
            if r:
                out.append(r)
    out.sort(key=lambda r: r["value"], reverse=True)
    return {"spec": spec, "city": city, "count_raw": len(raw),
            "count_qualified": len(cand), "results": out, "error": None}
