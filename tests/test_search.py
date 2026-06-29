import time
from pipeline.search import run_search, filter_district, _parallel_fetch
from pipeline.spec import SearchSpec


def test_parallel_fetch_runs_concurrently_and_preserves_order():
    def make(val):
        def f():
            time.sleep(0.2)
            return val
        return f
    t0 = time.monotonic()
    out = _parallel_fetch([make("olx"), make("oto")], workers=4)
    dt = time.monotonic() - t0
    assert out == ["olx", "oto"]
    assert dt < 0.35  # serial would be ~0.4s; concurrent overlaps


def test_parallel_fetch_isolates_failures_to_empty_list():
    def ok():
        return ["row"]

    def boom():
        raise RuntimeError("source down")
    out = _parallel_fetch([ok, boom], workers=2)
    assert out == [["row"], []]

def test_filter_district_keeps_matching_normalized():
    rows = [{"district": "Mokotów"}, {"district": "Wola"},
            {"district": ""}, {"district": "mokotow"}]
    out = filter_district(rows, "mokotów")
    assert out == [{"district": "Mokotów"}, {"district": "mokotow"}]

def test_filter_district_empty_returns_all():
    rows = [{"district": "Wola"}, {"district": ""}]
    assert filter_district(rows, "") == rows

def test_city_not_found():
    spec = SearchSpec(woj="mazowieckie", miasto="Nieistniejewo123", rooms=[3]).normalized()
    out = run_search(spec, max_pages=1)
    assert out["error"] == "city_not_found"

def test_run_search_krakow_smoke():
    spec = SearchSpec(woj="malopolskie", miasto="krakow", rooms=[3],
                      price_min=500000, price_max=1500000).normalized()
    out = run_search(spec, max_pages=1)
    assert out["error"] is None
    assert out["city"]["city_id"] > 0
    assert out["count_raw"] >= 0
    for r in out["results"]:
        assert "value" in r and r["value"] > 0
    vals = [r["value"] for r in out["results"]]
    assert vals == sorted(vals, reverse=True)
