from pipeline.search import run_search
from pipeline.spec import SearchSpec

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
