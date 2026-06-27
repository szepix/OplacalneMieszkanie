import argparse, json, re, sys
from pipeline.spec import SearchSpec
from pipeline.search import run_search

def _fmt(n): return f"{int(n):,}".replace(",", " ")

def build_spec(a) -> SearchSpec:
    return SearchSpec(
        woj=a.woj, miasto=a.miasto,
        rooms=[int(re.sub(r"\D", "", x)) for x in a.rooms.split(",") if re.sub(r"\D", "", x)] if a.rooms else [],
        price_min=a.price_min, price_max=a.price_max,
        area_min=a.area_min, area_max=a.area_max, year_min=a.year_min, floor=a.floor,
        required_features=a.features.split(",") if a.features else [],
        keywords=a.keywords.split(",") if a.keywords else [],
        rynek=a.rynek,
    ).normalized()

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--woj", required=True); p.add_argument("--miasto", required=True)
    p.add_argument("--rooms", default=""); p.add_argument("--price-min", dest="price_min", type=int, default=0)
    p.add_argument("--price-max", dest="price_max", type=int, default=10_000_000)
    p.add_argument("--area-min", dest="area_min", type=float, default=None)
    p.add_argument("--area-max", dest="area_max", type=float, default=None)
    p.add_argument("--year-min", dest="year_min", type=int, default=None)
    p.add_argument("--floor", type=int, default=None)
    p.add_argument("--features", default=""); p.add_argument("--keywords", default="")
    p.add_argument("--rynek", default="any"); p.add_argument("--max-pages", dest="max_pages", type=int, default=2)
    p.add_argument("--geocode", action="store_true", help="use Nominatim address geocode for precision")
    p.add_argument("--json", dest="json_out", default=None)
    a = p.parse_args(argv)
    spec = build_spec(a)
    out = run_search(spec, max_pages=a.max_pages, use_address_geocode=a.geocode)
    if a.json_out:
        ser = dict(out); ser["spec"] = vars(spec)
        with open(a.json_out, "w") as f:
            json.dump(ser, f, ensure_ascii=False, indent=1)
    if out["error"]:
        print(f"[!] {out['error']}", file=sys.stderr)
        return 0
    print(f"# {spec.miasto} ({spec.woj}) — {out['count_qualified']} kandydatów, "
          f"{len(out['results'])} z wyceną")
    for i, r in enumerate(out["results"][:30], 1):
        adr = " ".join(x for x in [r.get("street"), r.get("number")] if x) or r.get("district") or spec.miasto
        wyc = min(r["wycena"], r.get("wycena_med") or r["wycena"])
        print(f"{i:>2}. value {r['value']:<5} | {_fmt(r['eff_price'])} zł vs wycena {_fmt(wyc)} | "
              f"{r['area']:.0f} m² | {adr} | {r['src']} | {r['url']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
