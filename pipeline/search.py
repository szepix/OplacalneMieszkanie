from concurrent.futures import ThreadPoolExecutor
from config import FETCH_CONCURRENCY
from pipeline.spec import SearchSpec
from pipeline.geo import resolve_city, resolve_district, _norm, WARSZAWA_CITY_ID
from pipeline.features import enrich, qualifies
from pipeline.sources.olx import fetch_olx
from pipeline.sources.otodom import fetch_otodom
from pipeline.valuation import value_of

def filter_district(rows: list[dict], dzielnica: str) -> list[dict]:
    if not dzielnica:
        return rows
    dn = _norm(dzielnica)
    return [r for r in rows if _norm(r.get("district") or "") == dn]

def _parallel_fetch(tasks, workers):
    """Run fetch callables concurrently, order-preserving. A failing task
    yields [] (each source falls back independently, as the serial code did)."""
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(_safe, tasks))

def run_search(spec: SearchSpec, max_pages=2, use_address_geocode=False, workers=6):
    city = resolve_city(spec.woj, spec.miasto)
    if not city:
        return {"spec": spec, "city": None, "count_raw": 0, "count_qualified": 0,
                "results": [], "error": "city_not_found"}
    warszawa = city["city_id"] == WARSZAWA_CITY_ID
    region_norm, city_norm = _norm(spec.woj), _norm(spec.miasto)
    district_id = (resolve_district(city["city_id"], spec.dzielnica)
                   if spec.dzielnica and city.get("has_districts") else None)
    olx, oto = _parallel_fetch([
        lambda: fetch_olx(spec, city["city_id"], max_pages=max_pages, district_id=district_id),
        lambda: fetch_otodom(spec, region_norm, city_norm, max_pages=max_pages),
    ], workers=FETCH_CONCURRENCY)
    raw = filter_district([enrich(r) for r in olx + oto], spec.dzielnica)
    cand = [r for r in raw if qualifies(r, spec)]
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(lambda x: value_of(x, spec, use_address_geocode, warszawa), cand):
            if r:
                out.append(r)
    out.sort(key=lambda r: r["value"], reverse=True)
    return {"spec": spec, "city": city, "count_raw": len(raw),
            "count_qualified": len(cand), "results": out, "error": None}
